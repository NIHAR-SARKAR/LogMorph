import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Bell, Plus, Trash2, Edit, Check, AlertTriangle, AlertCircle,
  Mail, Webhook, Slack, MessageSquare, ToggleLeft, ToggleRight
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { alertApi } from '@/services/api'
import { useToast } from '@/components/ui/toast'
import type { AlertRule, Notification } from '@/types'

const conditionLabels: Record<string, string> = {
  new_error: 'New Error',
  fatal_error: 'Fatal Error',
  threshold_exceeded: 'Threshold Exceeded',
  pattern_match: 'Pattern Match',
  disk_issue: 'Disk Issue',
  auth_failure: 'Auth Failure',
  db_failure: 'DB Failure',
  custom_regex: 'Custom Regex'
}

const severityColors: Record<string, string> = {
  info: 'bg-blue-500',
  warning: 'bg-amber-500',
  critical: 'bg-red-500'
}

export function AlertsPage() {
  const [activeTab, setActiveTab] = useState('rules')
  const [showCreate, setShowCreate] = useState(false)
  const [newRule, setNewRule] = useState({
    name: '',
    description: '',
    condition: 'new_error',
    severity: 'warning',
    enabled: true,
    notify_desktop: true,
    notify_email: false,
    notify_slack: false,
    notify_webhook: false,
    webhook_url: '',
    config: {}
  })
  const [editRule, setEditRule] = useState<AlertRule | null>(null)
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const { data: rules, isLoading: rulesLoading } = useQuery({
    queryKey: ['alert-rules'],
    queryFn: () => alertApi.listRules().then(r => r.data)
  })

  const { data: notifications } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => alertApi.notifications({ limit: 50 }).then(r => r.data),
    refetchInterval: 30250
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => alertApi.createRule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
      setShowCreate(false)
      setNewRule({
        name: '',
        description: '',
        condition: 'new_error',
        severity: 'warning',
        enabled: true,
        notify_desktop: true,
        notify_email: false,
        notify_slack: false,
        notify_webhook: false,
        webhook_url: '',
        config: {}
      })
      addToast({ title: 'Alert rule created' })
    }
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => alertApi.updateRule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
      setEditRule(null)
      addToast({ title: 'Alert rule updated' })
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => alertApi.deleteRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
      addToast({ title: 'Rule deleted' })
    }
  })

  const markReadMutation = useMutation({
    mutationFn: (id: number) => alertApi.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] })
  })

  const unreadCount = (notifications || []).filter((n: Notification) => !n.is_read).length

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Bell className="h-8 w-8" />
            Alerts
            {unreadCount > 0 && (
              <Badge variant="destructive" className="ml-2">{unreadCount} new</Badge>
            )}
          </h1>
          <p className="text-muted-foreground">Monitor and manage alert rules and notifications</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Rule
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="rules">Rules</TabsTrigger>
          <TabsTrigger value="notifications">
            Notifications
            {unreadCount > 0 && <span className="ml-1 text-destructive">({unreadCount})</span>}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="rules" className="mt-4">
          <div className="space-y-3">
            {(rules || []).map((rule: AlertRule) => (
              <Card key={rule.id} className={!rule.enabled ? 'opacity-60' : ''}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`h-3 w-3 rounded-full ${severityColors[rule.severity] || 'bg-gray-400'}`} />
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">{rule.name}</h3>
                          <Badge variant="outline" className="text-xs">{conditionLabels[rule.condition] || rule.condition}</Badge>
                          {!rule.enabled && <Badge variant="secondary" className="text-xs">Disabled</Badge>}
                        </div>
                        <p className="text-sm text-muted-foreground">{rule.description || 'No description'}</p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Bell className="h-3 w-3" />
                            Triggered {rule.trigger_count} times
                          </span>
                          {rule.last_triggered && (
                            <span>Last: {new Date(rule.last_triggered).toLocaleString()}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        {rule.notify_desktop && <Bell className="h-4 w-4 text-muted-foreground" />}
                        {rule.notify_email && <Mail className="h-4 w-4 text-muted-foreground" />}
                        {rule.notify_slack && <Slack className="h-4 w-4 text-muted-foreground" />}
                        {rule.notify_webhook && <Webhook className="h-4 w-4 text-muted-foreground" />}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => setEditRule(rule)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => updateMutation.mutate({ id: rule.id, data: { enabled: !rule.enabled } })}
                      >
                        {rule.enabled ? 'Disable' : 'Enable'}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => deleteMutation.mutate(rule.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {(rules || []).length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <Bell className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>No alert rules configured</p>
                <Button variant="outline" className="mt-4" onClick={() => setShowCreate(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create your first rule
                </Button>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="notifications" className="mt-4">
          <div className="space-y-2">
            {(notifications || []).map((notif: Notification) => (
              <Card
                key={notif.id}
                className={`transition-colors ${!notif.is_read ? 'bg-primary/5 border-primary/20' : ''}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className={`h-2 w-2 rounded-full mt-2 ${severityColors[notif.severity] || 'bg-gray-400'}`} />
                      <div>
                        <h4 className={`font-medium ${!notif.is_read ? 'text-primary' : ''}`}>{notif.title}</h4>
                        <p className="text-sm text-muted-foreground mt-1">{notif.message}</p>
                        <span className="text-xs text-muted-foreground mt-2 block">
                          {new Date(notif.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                    {!notif.is_read && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => markReadMutation.mutate(notif.id)}
                      >
                        <Check className="h-4 w-4 mr-1" />
                        Mark read
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
            {(notifications || []).length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <Check className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>No notifications</p>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create Rule Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogHeader>
          <DialogTitle>Create Alert Rule</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input
              value={newRule.name}
              onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
              placeholder="Production Error Alert"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Condition</label>
            <select
              className="w-full h-10 rounded-md border border-input bg-background px-3"
              value={newRule.condition}
              onChange={(e) => setNewRule({ ...newRule, condition: e.target.value })}
            >
              {Object.entries(conditionLabels).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Severity</label>
            <select
              className="w-full h-10 rounded-md border border-input bg-background px-3"
              value={newRule.severity}
              onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })}
            >
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Notifications</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newRule.notify_desktop}
                  onChange={(e) => setNewRule({ ...newRule, notify_desktop: e.target.checked })}
                />
                Desktop
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newRule.notify_email}
                  onChange={(e) => setNewRule({ ...newRule, notify_email: e.target.checked })}
                />
                Email
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newRule.notify_slack}
                  onChange={(e) => setNewRule({ ...newRule, notify_slack: e.target.checked })}
                />
                Slack
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newRule.notify_webhook}
                  onChange={(e) => setNewRule({ ...newRule, notify_webhook: e.target.checked })}
                />
                Webhook
              </label>
            </div>
            {newRule.notify_webhook && (
              <Input
                className="mt-2"
                value={newRule.webhook_url}
                onChange={(e) => setNewRule({ ...newRule, webhook_url: e.target.value })}
                placeholder="https://hooks.example.com/alert"
              />
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
          <Button onClick={() => createMutation.mutate(newRule)} disabled={!newRule.name}>
            Create Rule
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Edit Rule Dialog */}
      <Dialog open={!!editRule} onOpenChange={() => setEditRule(null)}>
        <DialogHeader>
          <DialogTitle>Edit Alert Rule</DialogTitle>
        </DialogHeader>
        {editRule && (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Name</label>
              <Input
                value={editRule.name}
                onChange={(e) => setEditRule({ ...editRule, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Input
                value={editRule.description || ''}
                onChange={(e) => setEditRule({ ...editRule, description: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Condition</label>
              <select
                className="w-full h-10 rounded-md border border-input bg-background px-3"
                value={editRule.condition}
                onChange={(e) => setEditRule({ ...editRule, condition: e.target.value })}
              >
                {Object.entries(conditionLabels).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Severity</label>
              <select
                className="w-full h-10 rounded-md border border-input bg-background px-3"
                value={editRule.severity}
                onChange={(e) => setEditRule({ ...editRule, severity: e.target.value })}
              >
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={editRule.enabled}
                onChange={(e) => setEditRule({ ...editRule, enabled: e.target.checked })}
              />
              Enabled
            </label>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => setEditRule(null)}>Cancel</Button>
          <Button
            onClick={() => editRule && updateMutation.mutate({
              id: editRule.id,
              data: {
                name: editRule.name,
                description: editRule.description,
                condition: editRule.condition,
                severity: editRule.severity,
                enabled: editRule.enabled,
              }
            })}
          >
            Save Changes
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
