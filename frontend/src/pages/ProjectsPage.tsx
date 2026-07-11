import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  FolderOpen, Plus, MoreVertical, Edit, Trash2, ExternalLink,
  Tag, Calendar, Activity, ChevronRight
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { projectApi } from '@/services/api'
import { useToast } from '@/components/ui/toast'
import { useAuthStore } from '@/store/authStore'
import type { Project } from '@/types'

export function ProjectsPage() {
  const { user } = useAuthStore()
  const canEdit = user?.role === 'admin'
  const [showCreate, setShowCreate] = useState(false)
  const [newProject, setNewProject] = useState({ name: '', description: '', tags: '', path: '' })
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectApi.list().then(r => r.data)
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => projectApi.create(data),
    onSuccess: async (response) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      const projectId = response.data.id
      if (newProject.path.trim()) {
        try {
          const envRes = await projectApi.createEnvironment(projectId, {
            name: 'Default',
            type: 'development',
            description: 'Default environment'
          })
          await projectApi.createLogSource(projectId, {
            name: 'Default Source',
            path: newProject.path.trim(),
            environment_id: envRes.data.id,
            enabled: true,
            recursive_scan: true,
            auto_refresh: true,
            file_pattern: '*'
          })
          addToast({ title: 'Project and default log source created' })
        } catch (e: any) {
          const detail = e.response?.data?.detail
          addToast({
            title: 'Project created but log source failed',
            description: typeof detail === 'string' ? detail : JSON.stringify(detail),
            variant: 'destructive'
          })
        }
      } else {
        addToast({ title: 'Project created successfully' })
      }
      setShowCreate(false)
      setNewProject({ name: '', description: '', tags: '', path: '' })
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      addToast({ title: 'Failed to create project', description: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'destructive' })
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => projectApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setDeleteId(null)
      addToast({ title: 'Project deleted' })
    }
  })

  const handleCreate = () => {
    createMutation.mutate({
      name: newProject.name,
      description: newProject.description,
      tags: newProject.tags.split(',').map(t => t.trim()).filter(Boolean)
    })
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Projects</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array(6).fill(0).map((_, i) => (
            <div key={i} className="h-40 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground">Manage your log projects</p>
        </div>
        <Button onClick={() => setShowCreate(true)} disabled={!canEdit}>
          <Plus className="h-4 w-4 mr-2" />
          New Project
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(projects || []).map((project: Project) => (
          <Card key={project.id} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <FolderOpen className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg">{project.name}</CardTitle>
                </div>
                <Badge variant={project.status === 'active' ? 'default' : 'secondary'}>
                  {project.status}
                </Badge>
              </div>
              <CardDescription className="line-clamp-2">
                {project.description || 'No description'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-1">
                {(project.tags || []).map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    <Tag className="h-3 w-3 mr-1" />
                    {tag}
                  </Badge>
                ))}
              </div>
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    {project.environment_count} envs
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Link to={`/projects/${project.id}`}>
                    <Button variant="ghost" size="sm">
                      View <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input
              value={newProject.name}
              onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
              placeholder="Project name"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Input
              value={newProject.description}
              onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
              placeholder="Project description"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Tags (comma separated)</label>
            <Input
              value={newProject.tags}
              onChange={(e) => setNewProject({ ...newProject, tags: e.target.value })}
              placeholder="web, api, production"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Default Log Source Path (optional)</label>
            <Input
              value={newProject.path}
              onChange={(e) => setNewProject({ ...newProject, path: e.target.value })}
              placeholder="/var/log/myapp or C:\\logs"
            />
            <p className="text-xs text-muted-foreground">
              If provided, a default environment and log source will be created automatically.
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!newProject.name || createMutation.isPending}>
            {createMutation.isPending ? 'Creating...' : 'Create'}
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogHeader>
          <DialogTitle>Delete Project</DialogTitle>
        </DialogHeader>
        <p className="py-4">Are you sure you want to delete this project? This action cannot be undone.</p>
        <DialogFooter>
          <Button variant="outline" onClick={() => setDeleteId(null)}>Cancel</Button>
          <Button variant="destructive" onClick={() => deleteId && deleteMutation.mutate(deleteId)}>
            Delete
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
