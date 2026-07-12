export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: 'admin' | 'developer' | 'viewer';
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  last_login: string | null;
  avatar_url: string | null;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  tags: string[];
  status: 'active' | 'archived' | 'disabled';
  owner_id: number;
  created_at: string;
  updated_at: string;
  last_scan: string | null;
  environment_count: number;
  log_source_count: number;
}

export interface Environment {
  id: number;
  name: string;
  type: 'development' | 'qa' | 'uat' | 'staging' | 'production' | 'custom';
  description: string | null;
  project_id: number;
  created_at: string;
  log_source_count: number;
}

export interface LogSource {
  id: number;
  name: string;
  path: string;
  project_id: number;
  environment_id: number;
  enabled: boolean;
  recursive_scan: boolean;
  auto_refresh: boolean;
  encoding: string;
  timezone: string;
  retention_days: number;
  file_pattern: string;
  parser_template_id: number | null;
  created_at: string;
  updated_at: string;
  last_scan: string | null;
  total_files: number;
  total_entries: number;
}

export interface LogFile {
  id: number;
  filename: string;
  path: string;
  size_bytes: number;
  line_count: number;
  log_source_id: number;
  hash: string | null;
  first_seen: string;
  last_modified: string | null;
  last_parsed: string | null;
  parse_status: string;
  error_message: string | null;
  encoding: string;
  is_archived: boolean;
  is_compressed: boolean;
}

export interface LogEntry {
  id: number;
  log_file_id: number;
  line_number: number;
  timestamp: string | null;
  severity: Severity;
  message: string;
  raw_line: string;
  logger: string | null;
  module: string | null;
  class_name: string | null;
  method: string | null;
  thread_name: string | null;
  thread_id: string | null;
  process_id: string | null;
  request_id: string | null;
  correlation_id: string | null;
  session_id: string | null;
  user_id: string | null;
  machine_name: string | null;
  exception_type: string | null;
  exception_message: string | null;
  stack_trace: string | null;
  custom_fields: Record<string, any>;
  parsed_at: string;
  ai_summary: string | null;
  ai_analyzed: boolean;
  bookmarked: boolean;
  notes: string | null;
  tags: string[];
}

export type Severity = 'trace' | 'debug' | 'info' | 'success' | 'notice' | 'warning' | 'error' | 'critical' | 'fatal' | 'unknown';

export interface DashboardStats {
  total_projects: number;
  total_log_files: number;
  total_entries: number;
  active_monitors: number;
  logs_today: number;
  errors_today: number;
  warnings_today: number;
  critical_logs: number;
  ai_alerts: number;
  storage_used_mb: number;
  recent_activities: ActivityLog[];
  recent_searches: any[];
  top_error_categories: { name: string; count: number }[];
  top_applications: any[];
  environment_health: any[];
  log_volume_data: { date: string; count: number }[];
  error_trend_data: { date: string; count: number }[];
}

export interface ActivityLog {
  id: number;
  user_id: number | null;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  details: Record<string, any>;
  ip_address: string | null;
  created_at: string;
}

export interface AIProvider {
  id: number;
  name: string;
  provider_type: string;
  api_key: string | null;
  base_url: string | null;
  model: string | null;
  is_default: boolean;
  is_enabled: boolean;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface AlertRule {
  id: number;
  name: string;
  description: string | null;
  condition: string;
  config: Record<string, any>;
  severity: string;
  enabled: boolean;
  project_id: number | null;
  environment_id: number | null;
  log_source_id: number | null;
  cooldown_minutes: number;
  last_triggered: string | null;
  trigger_count: number;
  created_by_id: number | null;
  created_at: string;
  notify_desktop: boolean;
  notify_email: boolean;
  email_recipients: string[];
  notify_webhook: boolean;
  webhook_url: string | null;
  notify_slack: boolean;
  slack_webhook: string | null;
  notify_teams: boolean;
  teams_webhook: string | null;
  notify_discord: boolean;
  discord_webhook: string | null;
}

export interface Notification {
  id: number;
  title: string;
  message: string;
  severity: string;
  is_read: boolean;
  user_id: number | null;
  alert_rule_id: number | null;
  entity_type: string | null;
  entity_id: number | null;
  created_at: string;
}

export interface FacetValue {
  value: string;
  count: number;
  id?: number;
  name?: string;
}

export interface LogFacets {
  severity: FacetValue[];
  machine_name: FacetValue[];
  logger: FacetValue[];
  module: FacetValue[];
  sources: FacetValue[];
  files: FacetValue[];
}

export interface HistogramPoint {
  timestamp: string;
  count: number;
}

export interface RawLogLine {
  line_number: number;
  content: string;
}

export interface RawLogResponse {
  filename: string;
  file_id: number;
  path: string;
  total_lines: number;
  matched_lines: number;
  offset: number;
  limit: number;
  search: string | null;
  lines: RawLogLine[];
}

export interface ParserTemplate {
  id: number;
  name: string;
  description: string | null;
  format_type: string;
  pattern: string;
  timestamp_format: string | null;
  severity_mapping: Record<string, string>;
  field_mapping: Record<string, string>;
  sample_log: string | null;
  is_builtin: boolean;
  is_shared: boolean;
  created_by_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface UserProjectAccess {
  project_id: number;
  project_name: string;
  granted_by: number | null;
  granted_at: string;
}
