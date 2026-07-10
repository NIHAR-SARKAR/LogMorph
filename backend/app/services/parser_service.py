import re
import json
import csv
import io
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.schemas.parser import ParserTestRequest, ParserTestResult
from app.core.logging import logger

class ParserEngine:
    """Advanced log parsing engine supporting multiple formats."""

    BUILTIN_PATTERNS = {
        "generic_log": {
            "format_type": "regex",
            "pattern": r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(?P<severity>\w+)\s+(?P<message>.*)$",
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
            "severity_mapping": {},
            "field_mapping": {"timestamp": "timestamp", "severity": "severity", "message": "message"}
        },
        "json_log": {
            "format_type": "json",
            "pattern": "",
            "timestamp_format": "",
            "severity_mapping": {},
            "field_mapping": {}
        },
        "syslog": {
            "format_type": "regex",
            "pattern": r"^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+(?P<logger>\S+):\s+(?P<message>.*)$",
            "timestamp_format": "%b %d %H:%M:%S",
            "severity_mapping": {},
            "field_mapping": {"timestamp": "timestamp", "host": "machine_name", "logger": "logger", "message": "message"}
        },
        "nginx_access": {
            "format_type": "regex",
            "pattern": r'^(?P<remote_addr>\S+)\s+-\s+(?P<remote_user>\S+)\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<url>\S+)\s+HTTP/(?P<http_version>\d\.\d)"\s+(?P<status>\d{3})\s+(?P<body_bytes>\d+)\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"',
            "timestamp_format": "%d/%b/%Y:%H:%M:%S %z",
            "severity_mapping": {"5xx": "error", "4xx": "warning", "2xx": "info", "3xx": "info"},
            "field_mapping": {"timestamp": "timestamp", "status": "severity", "message": "url"}
        },
        "django": {
            "format_type": "regex",
            "pattern": r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+(?P<severity>\w+)\s+(?P<logger>\S+)\s+(?P<message>.*)$",
            "timestamp_format": "%Y-%m-%d %H:%M:%S,%f",
            "severity_mapping": {},
            "field_mapping": {"timestamp": "timestamp", "severity": "severity", "logger": "logger", "message": "message"}
        },
        "spring_boot": {
            "format_type": "regex",
            "pattern": r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2})\s+(?P<severity>\w+)\s+(?P<pid>\d+)\s+---\s+\[(?P<thread>[^\]]+)\]\s+(?P<logger>[^\s:]+)\s+:\s+(?P<message>.*)$",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "severity_mapping": {},
            "field_mapping": {"timestamp": "timestamp", "severity": "severity", "thread": "thread_name", "logger": "logger", "message": "message"}
        }
    }

    def __init__(self):
        self.compiled_patterns = {}

    def get_builtin_templates(self) -> List[Dict[str, Any]]:
        """Get all built-in parser templates."""
        templates = []
        for name, config in self.BUILTIN_PATTERNS.items():
            templates.append({
                "name": name,
                "description": f"Built-in {name} parser",
                "format_type": config["format_type"],
                "pattern": config["pattern"],
                "timestamp_format": config["timestamp_format"],
                "severity_mapping": config["severity_mapping"],
                "field_mapping": config["field_mapping"],
                "is_builtin": True
            })
        return templates

    def parse_line(self, line: str, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single log line using template."""
        format_type = template.get("format_type", "regex")

        if format_type == "regex":
            return self._parse_regex(line, template)
        elif format_type == "json":
            return self._parse_json(line, template)
        elif format_type == "csv":
            return self._parse_csv(line, template)
        elif format_type == "delimiter":
            return self._parse_delimiter(line, template)
        else:
            return self._parse_custom(line, template)

    def _parse_regex(self, line: str, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pattern = template.get("pattern", "")
        if not pattern:
            return None

        # Cache compiled patterns
        pattern_key = hash(pattern)
        if pattern_key not in self.compiled_patterns:
            try:
                self.compiled_patterns[pattern_key] = re.compile(pattern)
            except re.error as e:
                logger.error(f"Invalid regex pattern: {e}")
                return None

        compiled = self.compiled_patterns[pattern_key]
        match = compiled.match(line)
        if not match:
            return None

        result = match.groupdict()

        # Map fields
        field_mapping = template.get("field_mapping", {})
        mapped = {}
        for src, dst in field_mapping.items():
            if src in result:
                mapped[dst] = result[src]

        # Parse timestamp
        timestamp = None
        if "timestamp" in mapped and mapped["timestamp"]:
            ts_format = template.get("timestamp_format", "%Y-%m-%d %H:%M:%S")
            try:
                timestamp = datetime.strptime(mapped["timestamp"][:len(ts_format)], ts_format)
            except:
                pass

        # Map severity
        severity = mapped.get("severity", "unknown").lower()
        severity_mapping = template.get("severity_mapping", {})
        if severity in severity_mapping:
            severity = severity_mapping[severity]

        return {
            "timestamp": timestamp,
            "severity": severity,
            "message": mapped.get("message", line),
            "logger": mapped.get("logger"),
            "module": mapped.get("module"),
            "thread_name": mapped.get("thread_name"),
            "request_id": mapped.get("request_id"),
            "correlation_id": mapped.get("correlation_id"),
            "machine_name": mapped.get("machine_name"),
            "custom_fields": {k: v for k, v in result.items() if k not in field_mapping}
        }

    def _parse_json(self, line: str, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(line)
            field_mapping = template.get("field_mapping", {})

            timestamp = None
            if "timestamp" in field_mapping:
                ts_val = data.get(field_mapping["timestamp"])
                if ts_val:
                    try:
                        timestamp = datetime.fromisoformat(str(ts_val).replace('Z', '+00:00'))
                    except:
                        pass

            severity = str(data.get(field_mapping.get("severity", "level"), "unknown")).lower()

            return {
                "timestamp": timestamp,
                "severity": severity,
                "message": str(data.get(field_mapping.get("message", "message"), line)),
                "logger": str(data.get(field_mapping.get("logger", "logger"), "")),
                "custom_fields": {k: v for k, v in data.items() if k not in field_mapping.values()}
            }
        except json.JSONDecodeError:
            return None

    def _parse_csv(self, line: str, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            reader = csv.reader(io.StringIO(line))
            row = next(reader)
            headers = template.get("headers", [])
            if len(row) != len(headers):
                return None

            data = dict(zip(headers, row))
            return {
                "timestamp": datetime.strptime(data.get("timestamp", ""), template.get("timestamp_format", "%Y-%m-%d %H:%M:%S")) if "timestamp" in data else None,
                "severity": data.get("severity", "unknown").lower(),
                "message": data.get("message", line),
                "custom_fields": data
            }
        except:
            return None

    def _parse_delimiter(self, line: str, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        delimiter = template.get("delimiter", "\t")
        parts = line.split(delimiter)
        field_mapping = template.get("field_mapping", {})

        data = {}
        for i, (key, val) in enumerate(field_mapping.items()):
            if i < len(parts):
                data[val] = parts[i]

        return {
            "timestamp": None,
            "severity": data.get("severity", "unknown"),
            "message": data.get("message", line),
            "custom_fields": data
        }

    def _parse_custom(self, line: str, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Fallback to basic parsing
        return {
            "timestamp": None,
            "severity": "unknown",
            "message": line,
            "custom_fields": {}
        }

    def test_parser(self, request: ParserTestRequest) -> ParserTestResult:
        """Test parser against sample log."""
        template = {
            "format_type": request.format_type,
            "pattern": request.pattern,
            "timestamp_format": request.timestamp_format,
            "severity_mapping": request.severity_mapping,
            "field_mapping": request.field_mapping
        }

        result = self.parse_line(request.sample_log, template)
        if result:
            return ParserTestResult(
                success=True,
                extracted_fields=result.get("custom_fields", {}),
                timestamp=result.get("timestamp"),
                severity=result.get("severity"),
                message=result.get("message")
            )
        else:
            return ParserTestResult(
                success=False,
                error="Pattern did not match sample log"
            )

parser_engine = ParserEngine()
