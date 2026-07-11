import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FolderOpen, ArrowLeft, Plus, Trash2, RefreshCw, Play,
  Settings2, FileText, Activity, Calendar, Tag, Edit2, Power
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { projectApi, logApi } from '@/services/api'
import { useToast } from '@/components/ui/toast'
import { useAuthStore } from '@/store/authStore'
import type { Project, Environment, LogSource } from '@/types'

export function ProjectDetailPage() {
  const { user } = useAuthStore()
  const canEdit = user?.role === 'admin'
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { addToast } = useToast()
  const projectId = Number(id)

  const [activeTab, setActiveTab] = useState('overview')
  const [showEnvDialog, setShowEnvDialog] = useState(false)
  const [showSourceDialog, setShowSourceDialog] = useState(false)
  const [editingSource, setEditingSource] = useState<LogSource | null>(null)
  const [editSourceForm, setEditSourceForm] = useState<any>({})
  const [newEnv, setNewEnv] = useState({ name: '', type: 'development', description: '' })
  const [newSource, setNewSource] = useState({
    name: '',
    path: '',
    environment_id: '',
    file_pattern: '*',
    recursive_scan: true,
    auto_refresh: true,
  })

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectApi.get(projectId).then(r => r.data),
    enabled: !!projectId
  })

  const { data: environments } = useQuery({
    queryKey: ['environments', projectId],
    queryFn: () => projectApi.environments(projectId).then(r => r.data),
    enabled: !!projectId
  })

  const { data: sources } = useQuery({
    queryKey: ['sources', projectId],
    queryFn: () => projectApi.logSources(projectId).then(r => r.data),
    enabled: !!projectId
  })

  const createEnvMutation = useMutation({
    mutationFn: (data: any) => projectApi.createEnvironment(projectId, { ...data, project_id: projectId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['environments', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowEnvDialog(false)
      setNewEnv({ name: '', type: 'development', description: '' })
      addToast({ title: 'Environment created' })
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      addToast({ title: 'Failed to create environment', description: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'destructive' })
    }
  })

  const createSourceMutation = useMutation({
    mutationFn: (data: any) => projectApi.createLogSource(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setShowSourceDialog(false)
      setNewSource({ name: '', path: '', environment_id: '', file_pattern: '*', recursive_scan: true, auto_refresh: true })
      addToast({ title: 'Log source created' })
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      addToast({ title: 'Failed to create log source', description: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'destructive' })
    }
  })

  const deleteEnvMutation = useMutation({
    mutationFn: (envId: number) => projectApi.deleteEnvironment(projectId, envId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['environments', projectId] })
      addToast({ title: 'Environment deleted' })
    }
  })

  const deleteSourceMutation = useMutation({
    mutationFn: (sourceId: number) => projectApi.deleteLogSource(projectId, sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      addToast({ title: 'Log source deleted' })
    }
  })

  const updateSourceMutation = useMutation({
    mutationFn: ({ sourceId, data }: { sourceId: number; data: any }) => projectApi.updateLogSource(projectId, sourceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      setEditingSource(null)
      addToast({ title: 'Log source updated' })
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      addToast({ title: 'Failed to update log source', description: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'destructive' })
    }
  })

  const parseFileMutation = useMutation({
    mutationFn: (fileId: number) => logApi.parseFile(fileId),
  })

  const scanSourceMutation = useMutation({
    mutationFn: (sourceId: number) => logApi.scanSource(sourceId),
    onSuccess: async (response: any, sourceId: number) => {
      const scannedFiles = response.data.files || []
      queryClient.invalidateQueries({ queryKey: ['files'] })
      queryClient.invalidateQueries({ queryKey: ['sources', projectId] })
      addToast({ title: `Scan complete: ${scannedFiles.length} files found` })
      if (scannedFiles.length > 0) {
        addToast({ title: `Parsing ${scannedFiles.length} files...` })
        await Promise.all(scannedFiles.map((f: any) => parseFileMutation.mutateAsync(f.id)))
        queryClient.invalidateQueries({ queryKey: ['entries'] })
        addToast({ title: 'Parsing complete' })
      }
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      addToast({ title: 'Scan failed', description: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'destructive' })
    }
  })

  if (projectLoading) {
    return (
      <div className="p-6">
        <div className="h-40 bg-muted rounded-lg animate-pulse" />
      </div>
    )
  }

  const p = project as Project

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={() => navigate('/projects')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <FolderOpen className="h-8 w-8 text-primary" />
            {p?.name || 'Project'}
          </h1>
          <p className="text-muted-foreground">{p?.description || 'Project details'}</p>
        </div>
        <div className="ml-auto">
          <Badge variant={p?.status === 'active' ? 'default' : 'secondary'}>{p?.status}</Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Environments</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(environments || []).length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Log Sources</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(sources || []).length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Created</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{p?.created_at ? new Date(p.created_at).toLocaleDateString() : '-'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Owner ID</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{p?.owner_id}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="environments">Environments</TabsTrigger>
          <TabsTrigger value="sources">Log Sources</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Project Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-1">
                {(p?.tags || []).map((tag) => (
                  <Badge key={tag} variant="outline">
                    <Tag className="h-3 w-3 mr-1" />
                    {tag}
                  </Badge>
                ))}
              </div>
              <div className="text-sm text-muted-foreground">
                <span className="font-medium text-foreground">Last scan:</span>{' '}
                {p?.last_scan ? new Date(p.last_scan).toLocaleString() : 'Never'}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="environments" className="mt-4 space-y-4">
          <div className="flex justify-end">
            {canEdit && (
              <Button onClick={() => setShowEnvDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Environment
              </Button>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(environments || []).map((env: Environment) => (
              <Card key={env.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">{env.name}</CardTitle>
                      <CardDescription className="capitalize">{env.type}</CardDescription>
                    </div>
                    {canEdit && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => deleteEnvMutation.mutate(env.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{env.description || 'No description'}</p>
                  <p className="text-xs text-muted-foreground mt-2">
                    {env.log_source_count} log source(s)
                  </p>
                </CardContent>
              </Card>
            ))}
            {(environments || []).length === 0 && (
              <p className="text-muted-foreground text-sm">No environments yet.</p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="sources" className="mt-4 space-y-4">
          <div className="flex justify-end">
            {canEdit && (
              <Button onClick={() => setShowSourceDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Log Source
              </Button>
            )}
          </div>
          <div className="space-y-3">
            {(sources || []).map((source: LogSource) => (
              <Card key={source.id}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium">{source.name}</h3>
                        <Badge variant={source.enabled ? 'default' : 'secondary'}>
                          {source.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground font-mono">{source.path}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Pattern: {source.file_pattern} • Encoding: {source.encoding} • Files: {source.total_files} • Entries: {source.total_entries}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={() => scanSourceMutation.mutate(source.id)}>
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Scan
                      </Button>
                      {canEdit && (
                        <>
                          <Button
                            variant={source.enabled ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => updateSourceMutation.mutate({ sourceId: source.id, data: { enabled: !source.enabled } })}
                          >
                            <Power className="h-3.5 w-3.5 mr-1" />
                            {source.enabled ? 'Disable' : 'Enable'}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setEditingSource(source)
                              setEditSourceForm({
                                name: source.name,
                                path: source.path,
                                file_pattern: source.file_pattern,
                                enabled: source.enabled,
                                recursive_scan: source.recursive_scan,
                                auto_refresh: source.auto_refresh,
                              })
                            }}
                          >
                            <Edit2 className="h-3.5 w-3.5 mr-1" />
                            Edit
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => deleteSourceMutation.mutate(source.id)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {(sources || []).length === 0 && (
              <p className="text-muted-foreground text-sm">No log sources yet.</p>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Add Environment Dialog */}
      <Dialog open={showEnvDialog} onOpenChange={setShowEnvDialog}>
        <DialogHeader>
          <DialogTitle>Add Environment</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input value={newEnv.name} onChange={(e) => setNewEnv({ ...newEnv, name: e.target.value })} placeholder="Production" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Type</label>
            <select
              className="w-full h-10 rounded-md border border-input bg-background px-3"
              value={newEnv.type}
              onChange={(e) => setNewEnv({ ...newEnv, type: e.target.value })}
            >
              <option value="development">Development</option>
              <option value="qa">QA</option>
              <option value="uat">UAT</option>
              <option value="staging">Staging</option>
              <option value="production">Production</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Input value={newEnv.description} onChange={(e) => setNewEnv({ ...newEnv, description: e.target.value })} placeholder="Optional" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowEnvDialog(false)}>Cancel</Button>
          <Button onClick={() => createEnvMutation.mutate(newEnv)} disabled={!newEnv.name}>
            Create
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Add Log Source Dialog */}
      <Dialog open={showSourceDialog} onOpenChange={setShowSourceDialog}>
        <DialogHeader>
          <DialogTitle>Add Log Source</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input value={newSource.name} onChange={(e) => setNewSource({ ...newSource, name: e.target.value })} placeholder="Application Logs" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Path</label>
            <Input value={newSource.path} onChange={(e) => setNewSource({ ...newSource, path: e.target.value })} placeholder="/var/log/app or C:\\logs" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Environment</label>
            <select
              className="w-full h-10 rounded-md border border-input bg-background px-3"
              value={newSource.environment_id}
              onChange={(e) => setNewSource({ ...newSource, environment_id: e.target.value })}
            >
              <option value="">Select environment</option>
              {(environments || []).map((env: Environment) => (
                <option key={env.id} value={env.id}>{env.name}</option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">File Pattern</label>
            <Input value={newSource.file_pattern} onChange={(e) => setNewSource({ ...newSource, file_pattern: e.target.value })} placeholder="logfile*, *.log, error_*" />
            <p className="text-xs text-muted-foreground">Comma-separated glob patterns. Use * for wildcards.</p>
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={newSource.recursive_scan}
                onChange={(e) => setNewSource({ ...newSource, recursive_scan: e.target.checked })}
              />
              Recursive Scan
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={newSource.auto_refresh}
                onChange={(e) => setNewSource({ ...newSource, auto_refresh: e.target.checked })}
              />
              Auto Refresh
            </label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowSourceDialog(false)}>Cancel</Button>
          <Button
            onClick={() => createSourceMutation.mutate({
              ...newSource,
              project_id: projectId,
              environment_id: Number(newSource.environment_id),
              enabled: true,
              encoding: 'utf-8',
              timezone: 'UTC',
              retention_days: 90,
            })}
            disabled={!newSource.name || !newSource.path || !newSource.environment_id}
          >
            Create
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Edit Log Source Dialog */}
      <Dialog open={!!editingSource} onOpenChange={() => setEditingSource(null)}>
        <DialogHeader>
          <DialogTitle>Edit Log Source</DialogTitle>
        </DialogHeader>
        {editingSource && (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Name</label>
              <Input value={editSourceForm.name} onChange={(e) => setEditSourceForm({ ...editSourceForm, name: e.target.value })} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Path</label>
              <Input value={editSourceForm.path} onChange={(e) => setEditSourceForm({ ...editSourceForm, path: e.target.value })} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">File Pattern</label>
              <Input value={editSourceForm.file_pattern} onChange={(e) => setEditSourceForm({ ...editSourceForm, file_pattern: e.target.value })} placeholder="logfile*, *.log, error_*" />
              <p className="text-xs text-muted-foreground">Comma-separated glob patterns. Use * for wildcards.</p>
            </div>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={editSourceForm.enabled}
                  onChange={(e) => setEditSourceForm({ ...editSourceForm, enabled: e.target.checked })}
                />
                Enabled
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={editSourceForm.recursive_scan}
                  onChange={(e) => setEditSourceForm({ ...editSourceForm, recursive_scan: e.target.checked })}
                />
                Recursive Scan
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={editSourceForm.auto_refresh}
                  onChange={(e) => setEditSourceForm({ ...editSourceForm, auto_refresh: e.target.checked })}
                />
                Auto Refresh
              </label>
            </div>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => setEditingSource(null)}>Cancel</Button>
          <Button
            onClick={() => editingSource && updateSourceMutation.mutate({
              sourceId: editingSource.id,
              data: {
                name: editSourceForm.name,
                path: editSourceForm.path,
                file_pattern: editSourceForm.file_pattern,
                enabled: editSourceForm.enabled,
                recursive_scan: editSourceForm.recursive_scan,
                auto_refresh: editSourceForm.auto_refresh,
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
