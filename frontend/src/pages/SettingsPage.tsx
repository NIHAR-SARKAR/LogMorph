import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Settings, Palette, Globe, Database, Key, Shield, User,
  Moon, Sun, Monitor, Save, Check, AlertTriangle, Eye, EyeOff,
  Edit2, Trash2, Power, Star
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { settingsApi, aiApi, authApi } from '@/services/api'
import { useAppStore } from '@/store/appStore'
import { useAuthStore } from '@/store/authStore'
import { useToast } from '@/components/ui/toast'
import type { AIProvider } from '@/types'

const providerTypeMeta: Record<string, { label: string; placeholder?: string; baseUrl?: string; modelPlaceholder?: string }> = {
  ollama: { label: 'Ollama (Local)', baseUrl: 'http://localhost:11434', modelPlaceholder: 'llama3' },
  openai: { label: 'OpenAI', modelPlaceholder: 'gpt-4o' },
  anthropic: { label: 'Anthropic Claude', modelPlaceholder: 'claude-3-sonnet-20240229' },
  azure: { label: 'Azure OpenAI', baseUrl: 'https://<resource>.openai.azure.com/', modelPlaceholder: 'gpt-4-deployment' },
  lmstudio: { label: 'LM Studio', baseUrl: 'http://localhost:1234', modelPlaceholder: 'local-model' },
  openrouter: { label: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1', modelPlaceholder: 'openai/gpt-4o' },
}

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general')
  const { theme, setTheme, linesPerPage, setLinesPerPage, refreshInterval, setRefreshInterval } = useAppStore()
  const { user, setUser } = useAuthStore()
  const { addToast } = useToast()
  const queryClient = useQueryClient()

  const { data: aiProviders } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: () => aiApi.providers().then(r => r.data)
  })

  const themes = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor },
  ]

  // Profile state
  const [profile, setProfile] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
  })
  useEffect(() => {
    if (user) {
      setProfile({ full_name: user.full_name || '', email: user.email })
    }
  }, [user])

  const [passwords, setPasswords] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [showPassword, setShowPassword] = useState(false)

  const profileMutation = useMutation({
    mutationFn: (data: any) => authApi.updateMe(data),
    onSuccess: (response) => {
      setUser(response.data)
      addToast({ title: 'Profile saved successfully' })
    },
    onError: (error: any) => {
      addToast({
        title: 'Failed to save profile',
        description: (typeof error.response?.data?.detail === 'string' ? error.response.data.detail : JSON.stringify(error.response?.data?.detail)) || 'Unknown error',
        variant: 'destructive'
      })
    }
  })

  const handleSaveProfile = () => {
    const payload: any = { full_name: profile.full_name, email: profile.email }
    if (passwords.new_password) {
      if (passwords.new_password !== passwords.confirm_password) {
        addToast({ title: 'Passwords do not match', variant: 'destructive' })
        return
      }
      if (!passwords.current_password) {
        addToast({ title: 'Current password is required', variant: 'destructive' })
        return
      }
      payload.password = passwords.new_password
    }
    profileMutation.mutate(payload)
  }

  // AI Provider add state
  const [newProvider, setNewProvider] = useState({
    provider_type: 'ollama',
    name: '',
    api_key: '',
    base_url: '',
    model: '',
    is_enabled: true,
    api_version: '',
  })

  const createProviderMutation = useMutation({
    mutationFn: (data: any) => aiApi.createProvider(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] })
      setNewProvider({
        provider_type: 'ollama',
        name: '',
        api_key: '',
        base_url: '',
        model: '',
        is_enabled: true,
        api_version: '',
      })
      addToast({ title: 'AI provider added' })
    },
    onError: (error: any) => {
      addToast({
        title: 'Failed to add provider',
        description: (typeof error.response?.data?.detail === 'string' ? error.response.data.detail : JSON.stringify(error.response?.data?.detail)) || 'Unknown error',
        variant: 'destructive'
      })
    }
  })

  const updateProviderMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => aiApi.updateProvider(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] })
      addToast({ title: 'Provider updated' })
    },
    onError: (error: any) => {
      addToast({
        title: 'Failed to update provider',
        description: (typeof error.response?.data?.detail === 'string' ? error.response.data.detail : JSON.stringify(error.response?.data?.detail)) || 'Unknown error',
        variant: 'destructive'
      })
    }
  })

  const deleteProviderMutation = useMutation({
    mutationFn: (id: number) => aiApi.deleteProvider(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] })
      addToast({ title: 'Provider deleted' })
    }
  })

  const handleAddProvider = () => {
    if (!newProvider.name || !newProvider.model) {
      addToast({ title: 'Name and model are required', variant: 'destructive' })
      return
    }
    const payload: any = {
      provider_type: newProvider.provider_type,
      name: newProvider.name,
      api_key: newProvider.api_key || undefined,
      base_url: newProvider.base_url || undefined,
      model: newProvider.model,
      is_enabled: newProvider.is_enabled,
    }
    if (newProvider.provider_type === 'azure' && newProvider.api_version) {
      payload.config = { api_version: newProvider.api_version }
    }
    createProviderMutation.mutate(payload)
  }

  // Configure provider dialog
  const [configureProvider, setConfigureProvider] = useState<AIProvider | null>(null)
  const [editProviderForm, setEditProviderForm] = useState<any>({})

  const openConfigure = (provider: AIProvider) => {
    setConfigureProvider(provider)
    setEditProviderForm({
      name: provider.name,
      api_key: provider.api_key || '',
      base_url: provider.base_url || '',
      model: provider.model || '',
      is_enabled: provider.is_enabled,
      api_version: provider.config?.api_version || '',
    })
  }

  const handleSaveProvider = () => {
    if (!configureProvider) return
    const payload: any = {
      name: editProviderForm.name,
      api_key: editProviderForm.api_key || undefined,
      base_url: editProviderForm.base_url || undefined,
      model: editProviderForm.model,
      is_enabled: editProviderForm.is_enabled,
    }
    if (configureProvider.provider_type === 'azure' && editProviderForm.api_version) {
      payload.config = { api_version: editProviderForm.api_version }
    }
    updateProviderMutation.mutate({ id: configureProvider.id, data: payload })
    setConfigureProvider(null)
  }

  const handleToggleEnabled = (provider: AIProvider) => {
    updateProviderMutation.mutate({ id: provider.id, data: { is_enabled: !provider.is_enabled } })
  }

  const handleSetDefault = (provider: AIProvider) => {
    updateProviderMutation.mutate({ id: provider.id, data: { is_default: true } })
  }

  const meta = providerTypeMeta[newProvider.provider_type]

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Settings className="h-8 w-8" />
          Settings
        </h1>
        <p className="text-muted-foreground">Configure application preferences</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="general">
            <Palette className="h-4 w-4 mr-2" />
            General
          </TabsTrigger>
          <TabsTrigger value="ai">
            <Key className="h-4 w-4 mr-2" />
            AI Providers
          </TabsTrigger>
          <TabsTrigger value="database">
            <Database className="h-4 w-4 mr-2" />
            Database
          </TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Account
              </CardTitle>
              <CardDescription>Update your profile and password</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Username</label>
                  <Input value={user?.username || ''} disabled />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Role</label>
                  <Input value={user?.role || ''} disabled />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Full Name</label>
                  <Input
                    value={profile.full_name}
                    onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                    placeholder="Your full name"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Email</label>
                  <Input
                    type="email"
                    value={profile.email}
                    onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                    placeholder="you@example.com"
                  />
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-3">Change Password</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Current Password</label>
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      value={passwords.current_password}
                      onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })}
                      placeholder="••••••••"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">New Password</label>
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      value={passwords.new_password}
                      onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
                      placeholder="••••••••"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Confirm Password</label>
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      value={passwords.confirm_password}
                      onChange={(e) => setPasswords({ ...passwords, confirm_password: e.target.value })}
                      placeholder="••••••••"
                    />
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm mt-3">
                  <input
                    type="checkbox"
                    checked={showPassword}
                    onChange={(e) => setShowPassword(e.target.checked)}
                  />
                  Show passwords
                </label>
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={handleSaveProfile}
                  disabled={profileMutation.isPending}
                >
                  <Save className="h-4 w-4 mr-2" />
                  {profileMutation.isPending ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5" />
                Appearance
              </CardTitle>
              <CardDescription>Customize the look and feel</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Theme</label>
                <div className="flex gap-3">
                  {themes.map((t) => {
                    const Icon = t.icon
                    return (
                      <button
                        key={t.value}
                        onClick={() => setTheme(t.value as any)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                          theme === t.value
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-input hover:bg-accent'
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                        {t.label}
                      </button>
                    )
                  })}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Log Viewer
              </CardTitle>
              <CardDescription>Default log viewer preferences</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Default Lines Per Page</label>
                  <Input
                    type="number"
                    value={linesPerPage}
                    onChange={(e) => setLinesPerPage(Math.max(100, Math.min(10000, Number(e.target.value) || 100)))}
                    min={100}
                    max={10000}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Auto-refresh Interval (seconds)</label>
                  <Input
                    type="number"
                    value={refreshInterval}
                    onChange={(e) => setRefreshInterval(Math.max(5, Math.min(300, Number(e.target.value) || 5)))}
                    min={5}
                    max={300}
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <Button onClick={() => addToast({ title: 'Preferences saved' })}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Preferences
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>AI Providers</CardTitle>
              <CardDescription>Configure AI providers for log analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {(aiProviders || []).map((provider: AIProvider) => (
                  <div
                    key={provider.id}
                    className={`flex items-center justify-between p-4 border rounded-lg ${
                      provider.is_default ? 'border-primary bg-primary/5' : ''
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-medium">{provider.name}</h4>
                        {provider.is_default && <Badge>Default</Badge>}
                        <Badge variant={provider.is_enabled ? 'default' : 'secondary'}>
                          {provider.is_enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {provider.provider_type} • {provider.model || 'No model'}
                      </p>
                      {provider.base_url && (
                        <p className="text-xs text-muted-foreground truncate">{provider.base_url}</p>
                      )}
                      {provider.api_key && (
                        <p className="text-xs text-muted-foreground">
                          Key: ••••••••{provider.api_key.slice(-4)}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {!provider.is_default && (
                        <Button variant="outline" size="sm" onClick={() => handleSetDefault(provider)}>
                          <Star className="h-3.5 w-3.5 mr-1" />
                          Set Default
                        </Button>
                      )}
                      <Button
                        variant={provider.is_enabled ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => handleToggleEnabled(provider)}
                      >
                        <Power className="h-3.5 w-3.5 mr-1" />
                        {provider.is_enabled ? 'Disable' : 'Enable'}
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => openConfigure(provider)}>
                        <Edit2 className="h-3.5 w-3.5 mr-1" />
                        Configure
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => deleteProviderMutation.mutate(provider.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                ))}
                {(aiProviders || []).length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Key className="h-12 w-12 mx-auto mb-3 opacity-30" />
                    <p>No AI providers configured</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Add Provider</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Provider Type</label>
                  <select
                    className="w-full h-10 rounded-md border border-input bg-background px-3"
                    value={newProvider.provider_type}
                    onChange={(e) => {
                      const type = e.target.value
                      setNewProvider({
                        ...newProvider,
                        provider_type: type,
                        base_url: providerTypeMeta[type].baseUrl || '',
                        model: '',
                      })
                    }}
                  >
                    {Object.entries(providerTypeMeta).map(([key, { label }]) => (
                      <option key={key} value={key}>{label}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Name</label>
                  <Input
                    value={newProvider.name}
                    onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
                    placeholder={meta.label}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">API Key</label>
                <Input
                  type="password"
                  value={newProvider.api_key}
                  onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })}
                  placeholder={newProvider.provider_type === 'azure' ? 'Azure OpenAI key' : 'sk-...'}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {newProvider.provider_type === 'azure' ? 'Azure Endpoint' : 'Base URL'}
                </label>
                <Input
                  value={newProvider.base_url}
                  onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
                  placeholder={meta.baseUrl || 'https://api.example.com'}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    {newProvider.provider_type === 'azure' ? 'Deployment Name' : 'Model'}
                  </label>
                  <Input
                    value={newProvider.model}
                    onChange={(e) => setNewProvider({ ...newProvider, model: e.target.value })}
                    placeholder={meta.modelPlaceholder}
                  />
                </div>
                {newProvider.provider_type === 'azure' && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">API Version</label>
                    <Input
                      value={newProvider.api_version}
                      onChange={(e) => setNewProvider({ ...newProvider, api_version: e.target.value })}
                      placeholder="2024-02-15-preview"
                    />
                  </div>
                )}
              </div>

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newProvider.is_enabled}
                  onChange={(e) => setNewProvider({ ...newProvider, is_enabled: e.target.checked })}
                />
                Enabled
              </label>

              <Button className="w-full" onClick={handleAddProvider} disabled={createProviderMutation.isPending}>
                <Save className="h-4 w-4 mr-2" />
                {createProviderMutation.isPending ? 'Adding...' : 'Add Provider'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="database" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Database Management</CardTitle>
              <CardDescription>Backup and maintenance</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                <div>
                  <p className="font-medium">Database File</p>
                  <p className="text-sm text-muted-foreground">logmorph.db</p>
                </div>
                <Button variant="outline" size="sm">
                  <Database className="h-4 w-4 mr-2" />
                  Backup
                </Button>
              </div>
              <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                <div>
                  <p className="font-medium">Data Retention</p>
                  <p className="text-sm text-muted-foreground">Automatically clean old log entries</p>
                </div>
                <Input type="number" defaultValue={90} className="w-24" />
              </div>
              <div className="p-4 border border-destructive/20 bg-destructive/5 rounded-lg">
                <div className="flex items-center gap-2 text-destructive font-medium">
                  <AlertTriangle className="h-4 w-4" />
                  Danger Zone
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  These actions cannot be undone.
                </p>
                <div className="flex gap-2 mt-3">
                  <Button variant="destructive" size="sm">Clear All Logs</Button>
                  <Button variant="destructive" size="sm">Reset Database</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Configure Provider Dialog */}
      <Dialog open={!!configureProvider} onOpenChange={() => setConfigureProvider(null)}>
        <DialogHeader>
          <DialogTitle>Configure {configureProvider?.name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input
              value={editProviderForm.name || ''}
              onChange={(e) => setEditProviderForm({ ...editProviderForm, name: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">API Key</label>
            <Input
              type="password"
              value={editProviderForm.api_key || ''}
              onChange={(e) => setEditProviderForm({ ...editProviderForm, api_key: e.target.value })}
              placeholder="Leave blank to keep unchanged"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {configureProvider?.provider_type === 'azure' ? 'Azure Endpoint' : 'Base URL'}
            </label>
            <Input
              value={editProviderForm.base_url || ''}
              onChange={(e) => setEditProviderForm({ ...editProviderForm, base_url: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {configureProvider?.provider_type === 'azure' ? 'Deployment Name' : 'Model'}
              </label>
              <Input
                value={editProviderForm.model || ''}
                onChange={(e) => setEditProviderForm({ ...editProviderForm, model: e.target.value })}
              />
            </div>
            {configureProvider?.provider_type === 'azure' && (
              <div className="space-y-2">
                <label className="text-sm font-medium">API Version</label>
                <Input
                  value={editProviderForm.api_version || ''}
                  onChange={(e) => setEditProviderForm({ ...editProviderForm, api_version: e.target.value })}
                />
              </div>
            )}
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={editProviderForm.is_enabled || false}
              onChange={(e) => setEditProviderForm({ ...editProviderForm, is_enabled: e.target.checked })}
            />
            Enabled
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfigureProvider(null)}>Cancel</Button>
          <Button onClick={handleSaveProvider}>Save</Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
