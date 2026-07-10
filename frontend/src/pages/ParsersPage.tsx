import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FileCode, Plus, Play, Save, Trash2, Copy, Check,
  Regex, Braces, Table, Type
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { parserApi } from '@/services/api'
import { useToast } from '@/components/ui/toast'
import type { ParserTemplate } from '@/types'

const formatIcons: Record<string, any> = {
  regex: Regex,
  json: Braces,
  csv: Table,
  delimiter: Type,
  custom: FileCode
}

export function ParsersPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [showTest, setShowTest] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<ParserTemplate | null>(null)
  const [testResult, setTestResult] = useState<any>(null)
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    description: '',
    format_type: 'regex',
    pattern: '',
    timestamp_format: '%Y-%m-%d %H:%M:%S',
    severity_mapping: '{}',
    field_mapping: '{}',
    sample_log: ''
  })
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const { data: templates, isLoading } = useQuery({
    queryKey: ['parser-templates'],
    queryFn: () => parserApi.list(true).then(r => r.data)
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => parserApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parser-templates'] })
      setShowCreate(false)
      addToast({ title: 'Parser template created' })
    }
  })

  const testMutation = useMutation({
    mutationFn: (data: any) => parserApi.test(data),
    onSuccess: (data) => {
      setTestResult(data.data)
      addToast({ title: testResult?.success ? 'Pattern matched!' : 'Pattern did not match' })
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => parserApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parser-templates'] })
      addToast({ title: 'Template deleted' })
    }
  })

  const handleTest = () => {
    testMutation.mutate({
      pattern: newTemplate.pattern,
      format_type: newTemplate.format_type,
      sample_log: newTemplate.sample_log,
      timestamp_format: newTemplate.timestamp_format,
      severity_mapping: JSON.parse(newTemplate.severity_mapping || '{}'),
      field_mapping: JSON.parse(newTemplate.field_mapping || '{}')
    })
  }

  const handleCreate = () => {
    createMutation.mutate({
      ...newTemplate,
      severity_mapping: JSON.parse(newTemplate.severity_mapping || '{}'),
      field_mapping: JSON.parse(newTemplate.field_mapping || '{}')
    })
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Parser Templates</h1>
          <p className="text-muted-foreground">Manage log parsing configurations</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Template
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(templates || []).map((template: ParserTemplate) => {
          const Icon = formatIcons[template.format_type] || FileCode
          return (
            <Card key={template.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                  </div>
                  <div className="flex gap-1">
                    {template.is_builtin && (
                      <Badge variant="secondary" className="text-xs">Built-in</Badge>
                    )}
                    {template.is_shared && (
                      <Badge variant="outline" className="text-xs">Shared</Badge>
                    )}
                  </div>
                </div>
                <CardDescription className="line-clamp-2">
                  {template.description || `${template.format_type} parser`}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="bg-muted rounded-lg p-3">
                  <p className="text-xs font-mono text-muted-foreground truncate">
                    {template.pattern || 'JSON parser'}
                  </p>
                </div>
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="text-xs capitalize">
                    {template.format_type}
                  </Badge>
                  <div className="flex gap-1">
                    {!template.is_builtin && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => deleteMutation.mutate(template.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogHeader>
          <DialogTitle>Create Parser Template</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4 max-h-[70vh] overflow-y-auto">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input
              value={newTemplate.name}
              onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
              placeholder="My Log Format"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Format Type</label>
            <select
              className="w-full h-10 rounded-md border border-input bg-background px-3"
              value={newTemplate.format_type}
              onChange={(e) => setNewTemplate({ ...newTemplate, format_type: e.target.value })}
            >
              <option value="regex">Regex</option>
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
              <option value="delimiter">Delimiter</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Pattern</label>
            <textarea
              className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
              value={newTemplate.pattern}
              onChange={(e) => setNewTemplate({ ...newTemplate, pattern: e.target.value })}
              placeholder={newTemplate.format_type === 'regex' ? '^(?P<timestamp>...)\s+(?P<severity>\w+)' : ''}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Timestamp Format</label>
            <Input
              value={newTemplate.timestamp_format}
              onChange={(e) => setNewTemplate({ ...newTemplate, timestamp_format: e.target.value })}
              placeholder="%Y-%m-%d %H:%M:%S"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Sample Log Line</label>
            <textarea
              className="w-full min-h-[60px] rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
              value={newTemplate.sample_log}
              onChange={(e) => setNewTemplate({ ...newTemplate, sample_log: e.target.value })}
              placeholder="2024-01-01 12:00:00 ERROR Something went wrong"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Field Mapping (JSON)</label>
            <textarea
              className="w-full min-h-[60px] rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
              value={newTemplate.field_mapping}
              onChange={(e) => setNewTemplate({ ...newTemplate, field_mapping: e.target.value })}
              placeholder='{"timestamp": "timestamp", "level": "severity"}'
            />
          </div>

          {/* Test Section */}
          <div className="border rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-sm">Test Parser</h4>
              <Button variant="outline" size="sm" onClick={handleTest} disabled={testMutation.isPending}>
                <Play className="h-3 w-3 mr-1" />
                {testMutation.isPending ? 'Testing...' : 'Test'}
              </Button>
            </div>
            {testResult && (
              <div className={`p-3 rounded-lg text-sm ${testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <p className="font-medium">{testResult.success ? 'Match Successful' : 'Match Failed'}</p>
                {testResult.success && (
                  <div className="mt-2 space-y-1 text-xs">
                    <p><span className="font-medium">Severity:</span> {testResult.severity}</p>
                    <p><span className="font-medium">Message:</span> {testResult.message}</p>
                    <p><span className="font-medium">Timestamp:</span> {testResult.timestamp}</p>
                    {Object.keys(testResult.extracted_fields || {}).length > 0 && (
                      <div>
                        <span className="font-medium">Fields:</span>
                        <pre className="mt-1 bg-background p-2 rounded">{JSON.stringify(testResult.extracted_fields, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )}
                {testResult.error && <p className="text-red-600">{testResult.error}</p>}
              </div>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!newTemplate.name || createMutation.isPending}>
            <Save className="h-4 w-4 mr-1" />
            {createMutation.isPending ? 'Creating...' : 'Create'}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
