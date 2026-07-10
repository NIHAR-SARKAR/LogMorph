import os
import re
import hashlib
import fnmatch
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.database import get_db
from app.models.log import LogFile, LogEntry, Severity
from app.models.project import LogSource
from app.models.user import User
from app.schemas.log import (
    LogFile as LogFileSchema, LogFileCreate,
    LogEntry as LogEntrySchema, LogEntryCreate, LogEntryFilter, LogStats
)
from app.core.security import get_current_active_user, require_developer, require_admin
from app.core.logging import logger

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("/files", response_model=List[LogFileSchema])
def list_log_files(
    log_source_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List log files."""
    query = db.query(LogFile)
    if log_source_id:
        query = query.filter(LogFile.log_source_id == log_source_id)
    return query.offset(skip).limit(limit).all()

@router.post("/files/scan/{log_source_id}")
def scan_log_source(
    log_source_id: int,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db)
):
    """Scan a log source directory for log files."""
    source = db.query(LogSource).filter(LogSource.id == log_source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Log source not found")

    path = source.path
    logger.info(f"Scanning source {log_source_id} path={path!r} pattern={source.file_pattern!r} exists={os.path.exists(path)} isdir={os.path.isdir(path)} isfile={os.path.isfile(path)}")
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")

    files_found = []

    pattern = source.file_pattern or '*'
    if os.path.isfile(path):
        # Single file
        files = [path]
    else:
        # Directory
        if source.recursive_scan:
            files = []
            for root, _, filenames in os.walk(path):
                for fname in filenames:
                    if fnmatch.fnmatch(fname, pattern):
                        files.append(os.path.join(root, fname))
        else:
            files = [os.path.join(path, f) for f in os.listdir(path)
                     if os.path.isfile(os.path.join(path, f)) and fnmatch.fnmatch(f, pattern)]

    logger.info(f"Source {log_source_id}: matched {len(files)} files with pattern {pattern!r}")

    for filepath in files:
        try:
            stat = os.stat(filepath)
            file_hash = hashlib.sha256(filepath.encode()).hexdigest()[:16]

            existing = db.query(LogFile).filter(
                LogFile.path == filepath,
                LogFile.log_source_id == log_source_id
            ).first()

            if existing:
                # Update if modified
                if existing.last_modified != datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc):
                    existing.size_bytes = stat.st_size
                    existing.last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    existing.parse_status = "pending"
                    files_found.append(existing)
            else:
                log_file = LogFile(
                    filename=os.path.basename(filepath),
                    path=filepath,
                    size_bytes=stat.st_size,
                    log_source_id=log_source_id,
                    hash=file_hash,
                    last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    encoding=source.encoding
                )
                db.add(log_file)
                files_found.append(log_file)
        except Exception as e:
            logger.error(f"Error scanning file {filepath}: {e}")
            continue

    db.commit()
    source.last_scan = datetime.now(timezone.utc)
    source.total_files = db.query(LogFile).filter(LogFile.log_source_id == log_source_id).count()
    db.commit()

    return {
        "message": f"Scanned {len(files_found)} files",
        "files": [{"id": f.id, "filename": f.filename, "size": f.size_bytes} for f in files_found]
    }

@router.post("/files/{log_file_id}/parse")
def parse_log_file(
    log_file_id: int,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db)
):
    """Parse a log file and extract entries."""
    log_file = db.query(LogFile).filter(LogFile.id == log_file_id).first()
    if not log_file:
        raise HTTPException(status_code=404, detail="Log file not found")

    log_file.parse_status = "parsing"
    db.commit()

    try:
        # Clear existing entries
        db.query(LogEntry).filter(LogEntry.log_file_id == log_file_id).delete()

        entries = []
        line_number = 0
        current_entry = None
        stack_lines = []

        import re as re_mod
        ts_pattern = re_mod.compile(r'^\s*(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)')
        sev_pattern = re_mod.compile(r'\|\s*(TRACE|DEBUG|INFO|SUCCESS|NOTICE|WARN(?:ING)?|ERROR|CRITICAL|CRIT|FATAL)\s*\|', re_mod.IGNORECASE)

        def _flush_current():
            nonlocal current_entry, stack_lines, entries
            if current_entry is not None:
                if stack_lines:
                    current_entry.stack_trace = '\n'.join(stack_lines[:8000])
                entries.append(current_entry)
                if len(entries) >= 1000:
                    db.bulk_save_objects(entries)
                    db.commit()
                    entries.clear()
            current_entry = None
            stack_lines = []

        with open(log_file.path, 'r', encoding=log_file.encoding, errors='replace') as f:
            for line in f:
                line_number += 1
                line = line.rstrip('\n')
                if not line.strip():
                    continue

                # Check if this line starts a new log entry (has a timestamp at the start)
                ts_match = ts_pattern.match(line)
                sev_match = sev_pattern.search(line)

                if ts_match and sev_match:
                    # New entry — flush the previous one
                    _flush_current()

                    msg = line
                    ts = None
                    ts_str = ts_match.group(1)
                    try:
                        ts = datetime.strptime(ts_str[:19], '%Y-%m-%d %H:%M:%S')
                    except:
                        try:
                            ts = datetime.strptime(ts_str[:19], '%Y-%m-%dT%H:%M:%S')
                        except:
                            pass

                    # Detect severity from the | SEVERITY | pattern
                    sev_str = sev_match.group(1).upper()
                    if sev_str.startswith('WARN'):
                        severity = Severity.WARNING
                    elif sev_str == 'CRIT':
                        severity = Severity.CRITICAL
                    else:
                        try:
                            severity = Severity(sev_str.lower())
                        except ValueError:
                            severity = Severity.UNKNOWN

                    # Extract logger/module from format: | SEV | LoggerName [thread] - MESSAGE:
                    logger_name = None
                    module_name = None
                    after_sev = line[sev_match.end():]
                    logger_match = re_mod.match(r'\s*([A-Za-z_][\w.<>]+)', after_sev)
                    if logger_match:
                        logger_name = logger_match.group(1)
                        if '.' in logger_name:
                            parts = logger_name.rsplit('.', 1)
                            module_name = parts[0]

                    # Extract exception info
                    exception_type = None
                    exception_msg = None
                    if 'Exception' in line:
                        parts = line.split('Exception')
                        if len(parts) > 1:
                            prefix_words = parts[0].strip().split()
                            exception_type = (prefix_words[-1] + 'Exception') if prefix_words else 'Exception'
                            exception_msg = 'Exception' + parts[1]
                    elif 'Error:' in line:
                        parts = line.split('Error:')
                        if len(parts) > 1:
                            prefix_words = parts[0].strip().split()
                            exception_type = (prefix_words[-1] + 'Error') if prefix_words else 'Error'
                            exception_msg = 'Error:' + parts[1]

                    current_entry = LogEntry(
                        log_file_id=log_file_id,
                        line_number=line_number,
                        timestamp=ts,
                        severity=severity,
                        message=msg[:4000] if len(msg) > 4000 else msg,
                        raw_line=line[:8045] if len(line) > 8045 else line,
                        logger=logger_name,
                        module=module_name,
                        exception_type=exception_type,
                        exception_message=exception_msg
                    )
                    stack_lines = []
                else:
                    # Continuation line — either stack trace or multi-line content
                    if current_entry is not None:
                        stripped = line.strip()
                        # Detect exception type lines like "Npgsql.PostgresException (...)"
                        exc_match = re_mod.match(r'^([\w.]+Exception\b)', stripped)
                        if exc_match and not current_entry.exception_type:
                            current_entry.exception_type = exc_match.group(1)
                            current_entry.exception_message = stripped
                        # Detect "Severity: ERROR" in Npgsql exception output
                        elif re_mod.match(r'^Severity:\s*(\w+)', stripped, re_mod.IGNORECASE):
                            sev_inner = re_mod.match(r'^Severity:\s*(\w+)', stripped, re_mod.IGNORECASE)
                            if sev_inner and current_entry.severity == Severity.UNKNOWN:
                                try:
                                    current_entry.severity = Severity(sev_inner.group(1).lower())
                                except ValueError:
                                    pass
                        stack_lines.append(line[:8045])
                    else:
                        # No current entry — create a standalone entry
                        current_entry = LogEntry(
                            log_file_id=log_file_id,
                            line_number=line_number,
                            timestamp=None,
                            severity=Severity.UNKNOWN,
                            message=line[:4000],
                            raw_line=line[:8045],
                        )
                        stack_lines = []

        _flush_current()

        if entries:
            db.bulk_save_objects(entries)
            db.commit()

        log_file.line_count = line_number
        log_file.parse_status = "completed"
        log_file.last_parsed = datetime.now(timezone.utc)
        db.commit()

        # Update source totals
        source = db.query(LogSource).filter(LogSource.id == log_file.log_source_id).first()
        if source:
            source.total_entries = db.query(LogEntry).join(LogFile).filter(
                LogFile.log_source_id == source.id
            ).count()
            db.commit()

        return {
            "message": f"Parsed {line_number} lines",
            "entries_created": db.query(LogEntry).filter(LogEntry.log_file_id == log_file_id).count()
        }

    except Exception as e:
        log_file.parse_status = "error"
        log_file.error_message = str(e)
        db.commit()
        logger.error(f"Error parsing log file {log_file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Parse error: {str(e)}")

@router.get("/files/{file_id}/raw")
def get_raw_log_file(
    file_id: int,
    offset: int = 0,
    limit: int = 500,
    search: Optional[str] = None,
    tail: bool = False,
    db: Session = Depends(get_db)
):
    """Read raw log file content with optional search, pagination and tail mode."""
    log_file = db.query(LogFile).filter(LogFile.id == file_id).first()
    if not log_file:
        raise HTTPException(status_code=404, detail="Log file not found")
    if not os.path.exists(log_file.path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    lines_out = []
    total_lines = 0
    matched_lines = 0

    try:
        with open(log_file.path, 'r', encoding=log_file.encoding or 'utf-8', errors='replace') as f:
            if search:
                search_lower = search.lower()
                for i, line in enumerate(f):
                    total_lines += 1
                    if search_lower in line.lower():
                        matched_lines += 1
                        if matched_lines > offset and len(lines_out) < limit:
                            lines_out.append({"line_number": i + 1, "content": line.rstrip('\n\r')})
            elif tail:
                all_lines = []
                for i, line in enumerate(f):
                    total_lines += 1
                    all_lines.append((i + 1, line.rstrip('\n\r')))
                start_idx = max(0, len(all_lines) - limit)
                lines_out = [
                    {"line_number": ln, "content": content}
                    for ln, content in all_lines[start_idx:]
                ]
                matched_lines = total_lines
            else:
                for i, line in enumerate(f):
                    total_lines += 1
                    if i < offset:
                        continue
                    if len(lines_out) >= limit:
                        continue
                    lines_out.append({"line_number": i + 1, "content": line.rstrip('\n\r')})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    return {
        "filename": log_file.filename,
        "file_id": log_file.id,
        "path": log_file.path,
        "total_lines": total_lines,
        "matched_lines": matched_lines if search else total_lines,
        "offset": offset,
        "limit": limit,
        "search": search,
        "lines": lines_out,
    }


@router.get("/entries", response_model=List[LogEntrySchema])
def search_entries(
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    log_source_id: Optional[int] = None,
    log_file_id: Optional[int] = None,
    severity: Optional[str] = None,
    log_file_ids: Optional[str] = None,
    log_source_ids: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search_query: Optional[str] = None,
    is_regex: bool = False,
    exception_type: Optional[str] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    logger_name: Optional[str] = None,
    logger: Optional[str] = None,
    module: Optional[str] = None,
    machine_name: Optional[str] = None,
    bookmarked_only: bool = False,
    limit: int = 1000,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Search and filter log entries with full-text support."""
    query = db.query(LogEntry)

    # Apply file/source scoping — most specific first
    file_id_list = [int(v) for v in log_file_ids.split(',') if v.strip().isdigit()] if log_file_ids else []
    source_id_list = [int(v) for v in log_source_ids.split(',') if v.strip().isdigit()] if log_source_ids else []

    if log_file_id:
        query = query.filter(LogEntry.log_file_id == log_file_id)
    elif file_id_list:
        query = query.filter(LogEntry.log_file_id.in_(file_id_list))
    elif log_source_id:
        query = query.join(LogFile).filter(LogFile.log_source_id == log_source_id)
    elif source_id_list:
        query = query.join(LogFile).filter(LogFile.log_source_id.in_(source_id_list))
    elif environment_id:
        query = query.join(LogFile).join(LogSource).filter(LogSource.environment_id == environment_id)
    elif project_id:
        query = query.join(LogFile).join(LogSource).filter(LogSource.project_id == project_id)

    if severity:
        sev_list = [s.strip().lower() for s in severity.split(',') if s.strip()]
        if sev_list:
            query = query.filter(LogEntry.severity.in_(sev_list))

    if start_date:
        query = query.filter(LogEntry.timestamp >= start_date)
    if end_date:
        query = query.filter(LogEntry.timestamp <= end_date)

    if search_query:
        if is_regex:
            try:
                query = query.filter(LogEntry.message.op('REGEXP')(search_query))
            except:
                query = query.filter(LogEntry.message.contains(search_query))
        else:
            query = query.filter(LogEntry.message.contains(search_query))

    if exception_type:
        query = query.filter(LogEntry.exception_type == exception_type)
    if request_id:
        query = query.filter(LogEntry.request_id == request_id)
    if correlation_id:
        query = query.filter(LogEntry.correlation_id == correlation_id)
    if logger_name:
        query = query.filter(LogEntry.logger == logger_name)
    if logger:
        values = [v.strip() for v in logger.split(',') if v.strip()]
        if values:
            query = query.filter(LogEntry.logger.in_(values))
    if module:
        values = [v.strip() for v in module.split(',') if v.strip()]
        if values:
            query = query.filter(LogEntry.module.in_(values))
    if machine_name:
        values = [v.strip() for v in machine_name.split(',') if v.strip()]
        if values:
            query = query.filter(LogEntry.machine_name.in_(values))
    if bookmarked_only:
        query = query.filter(LogEntry.bookmarked == True)

    total = query.count()
    entries = query.order_by(LogEntry.timestamp.desc().nulls_last()).offset(offset).limit(limit).all()

    return entries

@router.get("/entries/{entry_id}", response_model=LogEntrySchema)
def get_entry(
    entry_id: int,
    db: Session = Depends(get_db)
):
    """Get single log entry."""
    entry = db.query(LogEntry).filter(LogEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry

@router.put("/entries/{entry_id}/bookmark")
def toggle_bookmark(
    entry_id: int,
    db: Session = Depends(get_db)
):
    """Toggle bookmark on a log entry."""
    entry = db.query(LogEntry).filter(LogEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry.bookmarked = not entry.bookmarked
    db.commit()
    return {"bookmarked": entry.bookmarked}

@router.put("/entries/{entry_id}/notes")
def update_notes(
    entry_id: int,
    notes: str,
    db: Session = Depends(get_db)
):
    """Add notes to a log entry."""
    entry = db.query(LogEntry).filter(LogEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry.notes = notes
    db.commit()
    return {"notes": entry.notes}


@router.delete("/entries/{entry_id}")
def delete_entry(
    entry_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a log entry."""
    entry = db.query(LogEntry).filter(LogEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    db.delete(entry)
    db.commit()
    logger.info(f"Log entry {entry_id} deleted by {current_user.username}")
    return {"message": "Log entry deleted"}

@router.get("/stats")
def get_log_stats(
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    log_source_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get log statistics."""
    query = db.query(LogEntry)

    if log_source_id:
        query = query.join(LogFile).filter(LogFile.log_source_id == log_source_id)
    elif environment_id:
        query = query.join(LogFile).join(LogSource).filter(LogSource.environment_id == environment_id)
    elif project_id:
        query = query.join(LogFile).join(LogSource).filter(LogSource.project_id == project_id)

    if start_date:
        query = query.filter(LogEntry.timestamp >= start_date)
    if end_date:
        query = query.filter(LogEntry.timestamp <= end_date)

    total = query.count()

    severity_counts = {}
    for sev in Severity:
        count = query.filter(LogEntry.severity == sev).count()
        severity_counts[sev.value] = count

    unique_exceptions = db.query(LogEntry.exception_type).filter(
        LogEntry.exception_type != None
    ).distinct().count()

    date_range = db.query(
        func.min(LogEntry.timestamp),
        func.max(LogEntry.timestamp)
    ).select_from(LogEntry).join(LogFile).join(LogSource)

    if log_source_id:
        date_range = date_range.filter(LogSource.id == log_source_id)
    elif environment_id:
        date_range = date_range.filter(LogSource.environment_id == environment_id)
    elif project_id:
        date_range = date_range.filter(LogSource.project_id == project_id)

    min_ts, max_ts = date_range.first() or (None, None)

    return LogStats(
        total_entries=total,
        error_count=severity_counts.get('error', 0),
        warning_count=severity_counts.get('warning', 0),
        critical_count=severity_counts.get('critical', 0),
        fatal_count=severity_counts.get('fatal', 0),
        info_count=severity_counts.get('info', 0),
        debug_count=severity_counts.get('debug', 0),
        trace_count=severity_counts.get('trace', 0),
        unique_exceptions=unique_exceptions,
        date_range_start=min_ts,
        date_range_end=max_ts
    )

@router.get("/severity-distribution")
def get_severity_distribution(
    project_id: Optional[int] = None,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get severity distribution over time."""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(
        func.date(LogEntry.timestamp).label('date'),
        LogEntry.severity,
        func.count(LogEntry.id).label('count')
    ).filter(LogEntry.timestamp >= from_date)

    if project_id:
        query = query.join(LogFile).join(LogSource).filter(LogSource.project_id == project_id)

    results = query.group_by(func.date(LogEntry.timestamp), LogEntry.severity).all()

    distribution = {}
    for date, severity, count in results:
        date_str = str(date)
        if date_str not in distribution:
            distribution[date_str] = {}
        distribution[date_str][severity.value] = count

    return distribution

@router.get("/top-exceptions")
def get_top_exceptions(
    project_id: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get top exception types."""
    query = db.query(
        LogEntry.exception_type,
        func.count(LogEntry.id).label('count')
    ).filter(LogEntry.exception_type != None)

    if project_id:
        query = query.join(LogFile).join(LogSource).filter(LogSource.project_id == project_id)

    results = query.group_by(LogEntry.exception_type).order_by(func.count(LogEntry.id).desc()).limit(limit).all()

    return [{"exception_type": r[0], "count": r[1]} for r in results]


def _build_entry_query(
    db: Session,
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    log_source_id: Optional[int] = None,
    log_file_id: Optional[int] = None,
    severity: Optional[str] = None,
    log_file_ids: Optional[str] = None,
    log_source_ids: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search_query: Optional[str] = None,
    is_regex: bool = False,
    filters: Optional[dict] = None,
):
    """Build a base LogEntry query with common filters."""
    file_id_list = [int(v) for v in log_file_ids.split(',') if v.strip().isdigit()] if log_file_ids else []
    source_id_list = [int(v) for v in log_source_ids.split(',') if v.strip().isdigit()] if log_source_ids else []

    if log_file_id:
        query = db.query(LogEntry).filter(LogEntry.log_file_id == log_file_id)
    elif file_id_list:
        query = db.query(LogEntry).filter(LogEntry.log_file_id.in_(file_id_list))
    elif log_source_id:
        query = db.query(LogEntry).join(LogFile).filter(LogFile.log_source_id == log_source_id)
    elif source_id_list:
        query = db.query(LogEntry).join(LogFile).filter(LogFile.log_source_id.in_(source_id_list))
    elif environment_id:
        query = db.query(LogEntry).join(LogFile).join(LogSource).filter(LogSource.environment_id == environment_id)
    elif project_id:
        query = db.query(LogEntry).join(LogFile).join(LogSource).filter(LogSource.project_id == project_id)
    else:
        query = db.query(LogEntry).join(LogFile).join(LogSource)

    if severity:
        sev_list = [s.strip().lower() for s in severity.split(',') if s.strip()]
        if sev_list:
            query = query.filter(LogEntry.severity.in_(sev_list))

    if start_date:
        query = query.filter(LogEntry.timestamp >= start_date)
    if end_date:
        query = query.filter(LogEntry.timestamp <= end_date)

    if search_query:
        if is_regex:
            try:
                query = query.filter(LogEntry.message.op('REGEXP')(search_query))
            except Exception:
                query = query.filter(LogEntry.message.contains(search_query))
        else:
            query = query.filter(LogEntry.message.contains(search_query))

    filters = filters or {}
    for field, value in filters.items():
        if value is None:
            continue
        if isinstance(value, str):
            values = [v.strip() for v in value.split(',') if v.strip()]
        elif isinstance(value, list):
            values = value
        else:
            values = [value]

        if not values:
            continue

        if field == 'machine_name':
            query = query.filter(LogEntry.machine_name.in_(values))
        elif field == 'logger':
            query = query.filter(LogEntry.logger.in_(values))
        elif field == 'module':
            query = query.filter(LogEntry.module.in_(values))
        elif field == 'severity':
            query = query.filter(LogEntry.severity.in_([v.lower() for v in values]))
        elif field == 'log_source_id':
            query = query.filter(LogSource.id.in_([int(v) for v in values if str(v).isdigit()]))
        elif field == 'log_file_id':
            query = query.filter(LogFile.id.in_([int(v) for v in values if str(v).isdigit()]))

    return query


@router.get("/facets")
def get_facets(
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    log_source_id: Optional[int] = None,
    log_file_id: Optional[int] = None,
    severity: Optional[str] = None,
    log_file_ids: Optional[str] = None,
    log_source_ids: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search_query: Optional[str] = None,
    is_regex: bool = False,
    machine_name: Optional[str] = None,
    logger: Optional[str] = None,
    module: Optional[str] = None,
    top: int = 50,
    db: Session = Depends(get_db)
):
    """Get facet counts for log entries.

    Each facet is computed WITHOUT its own filter applied, so that
    selecting e.g. 'error' severity doesn't hide the other severity
    options from the sidebar — you can still see and multi-select them.
    """
    def _query(exclude_field=None):
        """Build the base query, optionally skipping one filter field."""
        sev = None if exclude_field == 'severity' else severity
        mn = None if exclude_field == 'machine_name' else machine_name
        lg = None if exclude_field == 'logger' else logger
        md = None if exclude_field == 'module' else module
        lfi = None if exclude_field == 'log_file_ids' else log_file_ids
        lsi = None if exclude_field == 'log_source_ids' else log_source_ids

        filters = {}
        if mn:
            filters['machine_name'] = mn
        if lg:
            filters['logger'] = lg
        if md:
            filters['module'] = md
        return _build_entry_query(
            db, project_id, environment_id, log_source_id, log_file_id,
            sev, lfi, lsi,
            start_date, end_date, search_query, is_regex, filters
        )

    def _facet_counts(column, exclude_field=None):
        q = _query(exclude_field).with_entities(column, func.count(LogEntry.id).label('count'))
        if column is not LogEntry.severity:
            q = q.filter(column != None)
        return [
            {"value": value, "count": count}
            for value, count in q.group_by(column).order_by(func.count(LogEntry.id).desc()).limit(top).all()
            if value is not None
        ]

    base = _query()
    source_counts = base.with_entities(
        LogSource.id, LogSource.name, func.count(LogEntry.id).label('count')
    ).group_by(LogSource.id, LogSource.name).order_by(func.count(LogEntry.id).desc()).limit(top).all()

    file_counts = _query('log_file_ids').with_entities(
        LogFile.id, LogFile.filename, func.count(LogEntry.id).label('count')
    ).group_by(LogFile.id, LogFile.filename).order_by(func.count(LogEntry.id).desc()).limit(top).all()

    return {
        "severity": _facet_counts(LogEntry.severity, 'severity'),
        "machine_name": _facet_counts(LogEntry.machine_name, 'machine_name'),
        "logger": _facet_counts(LogEntry.logger, 'logger'),
        "module": _facet_counts(LogEntry.module, 'module'),
        "sources": [{"id": sid, "name": name, "count": count} for sid, name, count in source_counts],
        "files": [{"id": fid, "name": name, "count": count} for fid, name, count in file_counts],
    }


@router.get("/histogram")
def get_histogram(
    project_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    log_source_id: Optional[int] = None,
    log_file_id: Optional[int] = None,
    severity: Optional[str] = None,
    log_file_ids: Optional[str] = None,
    log_source_ids: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search_query: Optional[str] = None,
    is_regex: bool = False,
    machine_name: Optional[str] = None,
    logger: Optional[str] = None,
    module: Optional[str] = None,
    interval: str = "minute",
    db: Session = Depends(get_db)
):
    """Get time-bucketed log volume for the current query."""
    if interval not in ("minute", "hour", "day"):
        interval = "minute"

    bucket_format = {
        "minute": "%Y-%m-%dT%H:%M:00",
        "hour": "%Y-%m-%dT%H:00:00",
        "day": "%Y-%m-%d",
    }[interval]

    filters = {}
    if machine_name:
        filters['machine_name'] = machine_name
    if logger:
        filters['logger'] = logger
    if module:
        filters['module'] = module
    query = _build_entry_query(
        db, project_id, environment_id, log_source_id, log_file_id,
        severity, log_file_ids, log_source_ids,
        start_date, end_date, search_query, is_regex, filters
    )

    results = query.with_entities(
        func.strftime(bucket_format, LogEntry.timestamp).label('bucket'),
        func.count(LogEntry.id).label('count')
    ).filter(LogEntry.timestamp != None).group_by('bucket').order_by('bucket').all()

    return [{"timestamp": ts, "count": count} for ts, count in results]
