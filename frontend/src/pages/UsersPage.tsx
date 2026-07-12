import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users, Plus, Shield, UserCog, Eye, EyeOff, Trash2,
  Check, X, Lock, FolderKanban
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { authApi, projectApi } from '@/services/api'
import { useToast } from '@/components/ui/toast'
import type { User, UserProjectAccess } from '@/types'

export function UsersPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    role: 'viewer'
  })
  const [showPassword, setShowPassword] = useState(false)
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const [manageUser, setManageUser] = useState<User | null>(null)
  const [showProjects, setShowProjects] = useState(false)

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => authApi.listUsers().then(r => r.data)
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => authApi.register(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowCreate(false)
      setNewUser({ username: '', email: '', full_name: '', password: '', role: 'viewer' })
      addToast({ title: 'User created successfully' })
    },
    onError: (error: any) => {
      addToast({
        title: 'Failed to create user',
        description: typeof error.response?.data?.detail === 'string' ? error.response.data.detail : JSON.stringify(error.response?.data?.detail),
        variant: 'destructive'
      })
    }
  })

  const disableMutation = useMutation({
    mutationFn: (id: number) => authApi.disableUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addToast({ title: 'User disabled' })
    }
  })

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) => authApi.updateRole(id, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addToast({ title: 'Role updated' })
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => authApi.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addToast({ title: 'User deleted' })
    },
    onError: (error: any) => {
      addToast({
        title: 'Failed to delete user',
        description: error?.response?.data?.detail || 'Unknown error',
        variant: 'destructive'
      })
    }
  })

  const { data: allProjects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectApi.list().then(r => r.data),
    enabled: showProjects
  })

  const { data: userProjects } = useQuery({
    queryKey: ['user-projects', manageUser?.id],
    queryFn: () => authApi.getUserProjects(manageUser!.id).then(r => r.data),
    enabled: !!manageUser && showProjects
  })

  const grantProjectMutation = useMutation({
    mutationFn: ({ userId, projectId }: { userId: number; projectId: number }) =>
      authApi.grantProjectAccess(userId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-projects', manageUser?.id] })
      addToast({ title: 'Project access granted' })
    },
    onError: (error: any) => {
      addToast({
        title: 'Failed to grant access',
        description: error?.response?.data?.detail || 'Unknown error',
        variant: 'destructive'
      })
    }
  })

  const revokeProjectMutation = useMutation({
    mutationFn: ({ userId, projectId }: { userId: number; projectId: number }) =>
      authApi.revokeProjectAccess(userId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-projects', manageUser?.id] })
      addToast({ title: 'Project access revoked' })
    }
  })

  const roleColors: Record<string, string> = {
    admin: 'bg-red-500',
    developer: 'bg-blue-500',
    viewer: 'bg-gray-500'
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Users className="h-8 w-8" />
            Users
          </h1>
          <p className="text-muted-foreground">Manage user accounts and permissions</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add User
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="divide-y">
            {(users || []).map((user: User) => (
              <div key={user.id} className="flex items-center justify-between p-4 hover:bg-accent/50 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold text-primary">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{user.full_name || user.username}</span>
                      <Badge className={`text-xs ${roleColors[user.role]} text-white`}>
                        {user.role}
                      </Badge>
                      {!user.is_active && (
                        <Badge variant="outline" className="text-xs text-destructive">Disabled</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">{user.email}</p>
                    <p className="text-xs text-muted-foreground">
                      Last login: {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                    </p>
                  </div>
                </div>
                  <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => { setManageUser(user); setShowProjects(true) }}
                    disabled={user.is_superuser}
                  >
                    <FolderKanban className="h-3.5 w-3.5 mr-1" />
                    Projects
                  </Button>
                  <select
                    className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                    value={user.role}
                    onChange={(e) => roleMutation.mutate({ id: user.id, role: e.target.value })}
                    disabled={user.is_superuser}
                  >
                    <option value="admin">Admin</option>
                    <option value="developer">Developer</option>
                    <option value="viewer">Viewer</option>
                  </select>
                  {!user.is_superuser && (
                    <>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => disableMutation.mutate(user.id)}
                      >
                        {user.is_active ? <X className="h-4 w-4 text-destructive" /> : <Check className="h-4 w-4 text-green-500" />}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => {
                          if (confirm(`Delete user ${user.username}? This cannot be undone.`)) {
                            deleteMutation.mutate(user.id)
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogHeader>
          <DialogTitle>Create New User</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Username</label>
            <Input
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              placeholder="johndoe"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Email</label>
            <Input
              type="email"
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
              placeholder="john@example.com"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Full Name</label>
            <Input
              value={newUser.full_name}
              onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
              placeholder="John Doe"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Password</label>
            <div className="relative">
              <Input
                type={showPassword ? 'text' : 'password'}
                value={newUser.password}
                onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                placeholder="Min 8 characters"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Role</label>
            <select
              className="w-full h-10 rounded-md border border-input bg-background px-3"
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            >
              <option value="admin">Administrator</option>
              <option value="developer">Developer</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
          <Button
            onClick={() => createMutation.mutate(newUser)}
            disabled={!newUser.username || !newUser.password || createMutation.isPending}
          >
            {createMutation.isPending ? 'Creating...' : 'Create User'}
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Manage Project Access Dialog */}
      <Dialog open={showProjects} onOpenChange={setShowProjects}>
        <DialogHeader>
          <DialogTitle>Project Access: {manageUser?.username}</DialogTitle>
        </DialogHeader>
        <div className="py-4 space-y-3 max-h-[60vh] overflow-y-auto">
          {(allProjects || []).map((project: any) => {
            const hasAccess = (userProjects || []).some((up: UserProjectAccess) => up.project_id === project.id)
            const isOwner = project.owner_id === manageUser?.id
            return (
              <div key={project.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium text-sm">{project.name}</p>
                  {isOwner && <Badge variant="outline" className="text-xs mt-1">Owner</Badge>}
                </div>
                {isOwner ? (
                  <Badge className="text-xs">Owner</Badge>
                ) : hasAccess ? (
                  <Button
                    variant="destructive"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => revokeProjectMutation.mutate({ userId: manageUser!.id, projectId: project.id })}
                    disabled={revokeProjectMutation.isPending}
                  >
                    Revoke
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => grantProjectMutation.mutate({ userId: manageUser!.id, projectId: project.id })}
                    disabled={grantProjectMutation.isPending}
                  >
                    Grant
                  </Button>
                )}
              </div>
            )
          })}
          {(allProjects || []).length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">No projects available</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => { setShowProjects(false); setManageUser(null) }}>Close</Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
