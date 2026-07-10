import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard, FolderOpen, FileText, Activity, AlertTriangle,
  AlertOctagon, TrendingUp, HardDrive, Zap, Clock, Search
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { dashboardApi } from '@/services/api'
import { Skeleton } from '@/components/ui/skeleton'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell
} from 'recharts'

const severityColors: Record<string, string> = {
  trace: '#94a3b8',
  debug: '#8b5cf6',
  info: '#3b82f6',
  success: '#22c55e',
  notice: '#06b6d4',
  warning: '#f59e0b',
  error: '#ef4444',
  critical: '#dc2626',
  fatal: '#991b1b',
}

function StatCard({ title, value, icon: Icon, description, trend }: any) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
        {trend && (
          <div className="flex items-center gap-1 mt-2 text-xs text-green-600">
            <TrendingUp className="h-3 w-3" />
            {trend}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.stats().then(r => r.data),
    refetchInterval: 30250
  })

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array(8).fill(0).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-80" />
      </div>
    )
  }

  const s = stats || {}

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your log infrastructure</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Projects" value={s.total_projects || 0} icon={FolderOpen} />
        <StatCard title="Log Files" value={s.total_log_files || 0} icon={FileText} />
        <StatCard title="Total Entries" value={(s.total_entries || 0).toLocaleString()} icon={LayoutDashboard} />
        <StatCard title="Active Monitors" value={s.active_monitors || 0} icon={Activity} />
        <StatCard title="Logs Today" value={(s.logs_today || 0).toLocaleString()} icon={Clock} />
        <StatCard title="Errors Today" value={s.errors_today || 0} icon={AlertTriangle} description="Across all projects" />
        <StatCard title="Warnings" value={s.warnings_today || 0} icon={AlertOctagon} />
        <StatCard title="Storage Used" value={`${(s.storage_used_mb || 0).toFixed(1)} MB`} icon={HardDrive} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Log Volume (7 Days)</CardTitle>
            <CardDescription>Total log entries per day</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={s.log_volume_data || []}>
                <defs>
                  <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="count" stroke="#3b82f6" fillOpacity={1} fill="url(#colorVolume)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Error Trend</CardTitle>
            <CardDescription>Error count over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={s.error_trend_data || []}>
                <defs>
                  <linearGradient id="colorError" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="count" stroke="#ef4444" fillOpacity={1} fill="url(#colorError)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(s.recent_activities || []).length === 0 ? (
                <p className="text-sm text-muted-foreground">No recent activity</p>
              ) : (
                (s.recent_activities || []).slice(0, 8).map((activity: any) => (
                  <div key={activity.id} className="flex items-center gap-3 text-sm">
                    <div className="h-2 w-2 rounded-full bg-primary shrink-0" />
                    <span className="capitalize">{activity.action}</span>
                    <span className="text-muted-foreground ml-auto text-xs">
                      {new Date(activity.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Error Categories</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(s.top_error_categories || []).length === 0 ? (
                <p className="text-sm text-muted-foreground">No errors found</p>
              ) : (
                (s.top_error_categories || []).slice(0, 8).map((err: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 text-sm">
                    <span className="text-muted-foreground w-6">{i + 1}.</span>
                    <span className="font-mono text-xs truncate flex-1">{err.exception_type}</span>
                    <span className="text-destructive font-medium">{err.count}</span>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
