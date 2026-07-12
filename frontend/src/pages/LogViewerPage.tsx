import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Search, Filter, Download, Bookmark, BrainCircuit, ChevronDown, ChevronRight,
  X, RefreshCw, Clock, Calendar, Play, Pause, PanelRightOpen, PanelRightClose,
  LayoutList, Monitor, Server, Layers, FileText, AlertTriangle, Trash2, Terminal
} from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { logApi, aiApi, projectApi } from '@/services/api'
import { useToast } from '@/components/ui/toast'
import { useAppStore } from '@/store/appStore'
import { useAuthStore } from '@/store/authStore'
import { RawLogTerminal } from '@/components/RawLogTerminal'
import { Markdown } from '@/components/ui/markdown'
import { MarkdownModal, ExpandButton } from '@/components/ui/markdown-modal'
import type { LogEntry, LogFile, LogSource, Project, Environment, LogFacets, HistogramPoint } from '@/types'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
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
  unknown: '#6b7280',
}

const timePresets = [
  { label: '15m', ms: 15 * 60 * 1000 },
  { label: '1h', ms: 60 * 60 * 1000 },
  { label: '6h', ms: 6 * 60 * 60 * 1000 },
  { label: '24h', ms: 24 * 60 * 60 * 1000 },
  { label: '7d', ms: 7 * 24 * 60 * 60 * 1000 },
  { label: 'All', ms: 0 },
]

function getTimeRange(presetMs: number) {
  const end = new Date()
  if (presetMs === 0) {
    return { start: new Date(0), end }
  }
  const start = new Date(end.getTime() - presetMs)
  return { start, end }
}

function formatBucket(ts: string, interval: string) {
  const d = new Date(ts)
  if (interval === 'day') return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  if (interval === 'hour') return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

function formatShort(num: number) {
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'k'
  return num.toString()
}

export function LogViewerPage() {
  const { addToast } = useToast()
  const queryClient = useQueryClient()
  const { refreshInterval } = useAppStore()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'
  const [searchParams, setSearchParams] = useSearchParams()

  const numParam = (key: string): number | '' => {
    const v = searchParams.get(key)
    return v ? Number(v) : ''
  }

  const [selectedProject, setSelectedProject] = useState<number | ''>(numParam('project'))
  const [selectedEnvironment, setSelectedEnvironment] = useState<number | ''>(numParam('env'))
  const [selectedSource, setSelectedSource] = useState<number | ''>(numParam('source'))
  const [selectedFile, setSelectedFile] = useState<number | ''>(numParam('file'))

  const [viewMode, setViewMode] = useState<'explorer' | 'raw'>('explorer')
  const [preset, setPreset] = useState(timePresets[4].ms)
  const [searchQuery, setSearchQuery] = useState('')
  const [isRegex, setIsRegex] = useState(false)
  const [caseSensitive, setCaseSensitive] = useState(false)
  const [liveTail, setLiveTail] = useState(false)

  const [selectedSeverity, setSelectedSeverity] = useState<string[]>([])
  const [selectedHosts, setSelectedHosts] = useState<string[]>([])
  const [selectedServices, setSelectedServices] = useState<string[]>([])
  const [selectedModules, setSelectedModules] = useState<string[]>([])
  const [selectedSources, setSelectedSources] = useState<number[]>([])
  const [selectedFiles, setSelectedFiles] = useState<number[]>([])

  const [selectedEntry, setSelectedEntry] = useState<LogEntry | null>(null)
  const [aiResult, setAiResult] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)

  const [modalOpen, setModalOpen] = useState(false)
  const [modalTitle, setModalTitle] = useState('')
  const [modalContent, setModalContent] = useState('')

  const openModal = (title: string, content: string) => {
    setModalTitle(title)
    setModalContent(content)
    setModalOpen(true)
  }

  const { start, end } = useMemo(() => getTimeRange(preset), [preset])
  const interval = useMemo(() => {
    const range = end.getTime() - start.getTime()
    if (range <= 60 * 60 * 1000) return 'minute'
    if (range <= 24 * 60 * 60 * 1000) return 'hour'
    return 'day'
  }, [start, end])

  const baseParams = useMemo(() => ({
    project_id: selectedProject || undefined,
    environment_id: selectedEnvironment || undefined,
    log_source_id: selectedSource || undefined,
    log_file_id: selectedFile || undefined,
    severity: selectedSeverity.length ? selectedSeverity.join(',') : undefined,
    start_date: preset === 0 ? undefined : start.toISOString(),
    end_date: preset === 0 ? undefined : end.toISOString(),
    search_query: searchQuery || undefined,
    is_regex: isRegex,
    machine_name: selectedHosts.length ? selectedHosts.join(',') : undefined,
    logger: selectedServices.length ? selectedServices.join(',') : undefined,
    module: selectedModules.length ? selectedModules.join(',') : undefined,
    log_file_ids: selectedFiles.length ? selectedFiles.join(',') : undefined,
    log_source_ids: selectedSources.length ? selectedSources.join(',') : undefined,
  }), [selectedProject, selectedEnvironment, selectedSource, selectedFile, selectedSeverity, start, end, preset, searchQuery, isRegex, selectedHosts, selectedServices, selectedModules, selectedFiles, selectedSources])

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectApi.list().then(r => r.data)
  })

  // Auto-select first project on initial load if none selected
  useEffect(() => {
    if (!selectedProject && projects && projects.length > 0) {
      setSelectedProject(projects[0].id)
    }
  }, [projects, selectedProject])

  // Sync selection state to URL query params
  useEffect(() => {
    const params: Record<string, string> = {}
    if (selectedProject) params.project = String(selectedProject)
    if (selectedEnvironment) params.env = String(selectedEnvironment)
    if (selectedSource) params.source = String(selectedSource)
    if (selectedFile) params.file = String(selectedFile)
    setSearchParams(params, { replace: true })
  }, [selectedProject, selectedEnvironment, selectedSource, selectedFile, setSearchParams])

  const { data: environments } = useQuery({
    queryKey: ['environments', selectedProject],
    queryFn: () => projectApi.environments(Number(selectedProject)).then(r => r.data),
    enabled: !!selectedProject
  })

  const { data: sources } = useQuery({
    queryKey: ['sources', selectedProject, selectedEnvironment],
    queryFn: () => projectApi.logSources(Number(selectedProject)).then(r => r.data),
    enabled: !!selectedProject
  })

  const { data: files } = useQuery({
    queryKey: ['files', selectedSource],
    queryFn: () => logApi.listFiles({ log_source_id: selectedSource }).then(r => r.data),
    enabled: !!selectedSource
  })

  const { data: entries, isLoading: entriesLoading, refetch: refetchEntries } = useQuery({
    queryKey: ['entries', baseParams],
    queryFn: () => logApi.search({ ...baseParams, limit: 500 }).then(r => r.data),
    enabled: !!selectedProject
  })

  const { data: facets, refetch: refetchFacets } = useQuery({
    queryKey: ['facets', baseParams],
    queryFn: () => logApi.facets(baseParams).then(r => r.data as LogFacets),
    enabled: !!selectedProject
  })

  const { data: histogram, refetch: refetchHistogram } = useQuery({
    queryKey: ['histogram', baseParams, interval],
    queryFn: () => logApi.histogram({ ...baseParams, interval }).then(r => r.data as HistogramPoint[]),
    enabled: !!selectedProject
  })

  const bookmarkMutation = useMutation({
    mutationFn: (id: number) => logApi.toggleBookmark(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entries'] })
      if (selectedEntry) setSelectedEntry({ ...selectedEntry, bookmarked: !selectedEntry.bookmarked })
    }
  })

  const parseFileMutation = useMutation({
    mutationFn: (fileId: number) => logApi.parseFile(fileId),
  })

  const deleteEntryMutation = useMutation({
    mutationFn: (id: number) => logApi.deleteEntry(id),
    onSuccess: () => {
      addToast({ title: 'Log entry deleted' })
      setSelectedEntry(null)
      queryClient.invalidateQueries({ queryKey: ['entries'] })
      queryClient.invalidateQueries({ queryKey: ['facets'] })
      queryClient.invalidateQueries({ queryKey: ['histogram'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      addToast({
        title: 'Failed to delete log entry',
        description: typeof detail === 'string' ? detail : JSON.stringify(detail),
        variant: 'destructive'
      })
    }
  })

  const handleAnalyze = async (entry: LogEntry) => {
    setAiLoading(true)
    setAiResult(null)
    try {
      const result = await aiApi.analyzeException(
        entry.exception_type || 'Unknown',
        entry.stack_trace || entry.message
      )
      setAiResult(result.data.content)
    } catch {
      setAiResult('AI analysis failed. Please check your AI provider configuration.')
    } finally {
      setAiLoading(false)
    }
  }

  const handleScan = async () => {
    if (!selectedSource) {
      addToast({ title: 'Select a log source to scan', variant: 'destructive' })
      return
    }
    try {
      const response = await logApi.scanSource(Number(selectedSource))
      const scannedFiles = response.data.files || []
      addToast({ title: `Scan complete: ${scannedFiles.length} files found` })
      queryClient.invalidateQueries({ queryKey: ['files'] })
      queryClient.invalidateQueries({ queryKey: ['sources', selectedProject] })

      if (scannedFiles.length > 0) {
        addToast({ title: `Parsing ${scannedFiles.length} files...` })
        await Promise.all(scannedFiles.map((f: any) => parseFileMutation.mutateAsync(f.id)))
        queryClient.invalidateQueries({ queryKey: ['entries'] })
        queryClient.invalidateQueries({ queryKey: ['facets'] })
        queryClient.invalidateQueries({ queryKey: ['histogram'] })
        queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
        addToast({ title: 'Parsing complete' })
      }
    } catch (error: any) {
      const detail = error.response?.data?.detail
      addToast({ title: 'Scan failed', description: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'destructive' })
    }
  }

  const toggleFilter = (value: string, list: string[], setList: (v: string[]) => void) => {
    if (list.includes(value)) {
      setList(list.filter(v => v !== value))
    } else {
      setList([...list, value])
    }
  }

  const activeFilters = useMemo(() => {
    const filters: { label: string; value: string; onRemove: () => void }[] = []
    selectedSeverity.forEach(v => filters.push({ label: 'Severity', value: v, onRemove: () => setSelectedSeverity(selectedSeverity.filter(x => x !== v)) }))
    selectedHosts.forEach(v => filters.push({ label: 'Host', value: v, onRemove: () => setSelectedHosts(selectedHosts.filter(x => x !== v)) }))
    selectedServices.forEach(v => filters.push({ label: 'Service', value: v, onRemove: () => setSelectedServices(selectedServices.filter(x => x !== v)) }))
    selectedModules.forEach(v => filters.push({ label: 'Module', value: v, onRemove: () => setSelectedModules(selectedModules.filter(x => x !== v)) }))
    selectedSources.forEach(id => {
      const s = (sources || []).find((x: LogSource) => x.id === id)
      filters.push({ label: 'Source', value: s?.name || String(id), onRemove: () => setSelectedSources(selectedSources.filter(x => x !== id)) })
    })
    selectedFiles.forEach(id => {
      const f = (files || []).find((x: LogFile) => x.id === id)
      filters.push({ label: 'File', value: f?.filename || String(id), onRemove: () => setSelectedFiles(selectedFiles.filter(x => x !== id)) })
    })
    return filters
  }, [selectedSeverity, selectedHosts, selectedServices, selectedModules, selectedSources, selectedFiles, sources, files])

  useEffect(() => {
    if (!liveTail) return
    const id = setInterval(() => {
      refetchEntries()
      refetchFacets()
      refetchHistogram()
    }, Math.max(5000, refreshInterval * 1000))
    return () => clearInterval(id)
  }, [liveTail, refreshInterval, refetchEntries, refetchFacets, refetchHistogram])

  const filteredSources = useMemo(() => {
    if (!selectedEnvironment) return sources || []
    return (sources || []).filter((s: LogSource) => s.environment_id === Number(selectedEnvironment))
  }, [sources, selectedEnvironment])

  const totalHits = (entries || []).length
  const selectedFilename = (files || []).find((f: LogFile) => f.id === Number(selectedFile))?.filename || ''

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Header */}
      <div className="border-b bg-card px-4 py-3 space-y-3">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-xl font-bold mr-4 flex items-center gap-2">
            <LayoutList className="h-5 w-5 text-primary" />
            Log Explorer
          </h1>

          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={selectedProject}
            onChange={(e) => {
              const v = Number(e.target.value) || ''
              setSelectedProject(v)
              setSelectedEnvironment('')
              setSelectedSource('')
              setSelectedFile('')
            }}
          >
            <option value="">Select Project</option>
            {(projects || []).map((p: Project) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>

          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={selectedEnvironment}
            onChange={(e) => { setSelectedEnvironment(Number(e.target.value) || ''); setSelectedSource(''); setSelectedFile('') }}
            disabled={!selectedProject}
          >
            <option value="">All Environments</option>
            {(environments || []).map((env: Environment) => (
              <option key={env.id} value={env.id}>{env.name}</option>
            ))}
          </select>

          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={selectedSource}
            onChange={(e) => { setSelectedSource(Number(e.target.value) || ''); setSelectedFile('') }}
            disabled={!selectedProject}
          >
            <option value="">All Sources</option>
            {filteredSources.map((s: LogSource) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>

          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={selectedFile}
            onChange={(e) => setSelectedFile(Number(e.target.value) || '')}
            disabled={!selectedSource}
          >
            <option value="">All Files</option>
            {(files || []).map((f: LogFile) => (
              <option key={f.id} value={f.id}>{f.filename}</option>
            ))}
          </select>

          <div className="h-6 w-px bg-border mx-1" />

          <div className="flex items-center gap-1 bg-muted rounded-md p-1">
            {timePresets.map((t) => (
              <button
                key={t.label}
                onClick={() => setPreset(t.ms)}
                className={`px-2 py-1 text-xs rounded ${preset === t.ms ? 'bg-background shadow-sm font-medium' : 'text-muted-foreground hover:text-foreground'}`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-1 bg-muted rounded-md p-1">
            <button
              onClick={() => setViewMode('explorer')}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded transition-colors ${viewMode === 'explorer' ? 'bg-background shadow-sm font-medium' : 'text-muted-foreground hover:text-foreground'}`}
            >
              <LayoutList className="h-3.5 w-3.5" />
              Explorer
            </button>
            <button
              onClick={() => setViewMode('raw')}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded transition-colors ${viewMode === 'raw' ? 'bg-background shadow-sm font-medium' : 'text-muted-foreground hover:text-foreground'}`}
            >
              <Terminal className="h-3.5 w-3.5" />
              Raw Terminal
            </button>
          </div>

          <Button variant={liveTail ? 'default' : 'outline'} size="sm" onClick={() => setLiveTail(!liveTail)}>
            {liveTail ? <Pause className="h-4 w-4 mr-1" /> : <Play className="h-4 w-4 mr-1" />}
            Live
          </Button>
          <Button variant="outline" size="sm" onClick={handleScan} disabled={!selectedSource}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Scan
          </Button>
        </div>

        {/* Search */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search logs... (supports regex)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && refetchEntries()}
            />
          </div>
          <Button
            variant={isRegex ? 'default' : 'outline'}
            size="sm"
            onClick={() => setIsRegex(!isRegex)}
          >
            .*
          </Button>
          <Button
            variant={caseSensitive ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCaseSensitive(!caseSensitive)}
          >
            Aa
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetchEntries()}>
            <Search className="h-4 w-4" />
          </Button>
        </div>

        {/* Active filters */}
        {activeFilters.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            {activeFilters.map((f, i) => (
              <Badge key={i} variant="secondary" className="gap-1 pl-2">
                <span className="text-muted-foreground text-xs">{f.label}:</span>
                {f.value}
                <button onClick={f.onRemove} className="ml-1 hover:text-destructive">
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
            <Button variant="ghost" size="sm" className="h-7" onClick={() => {
              setSelectedSeverity([])
              setSelectedHosts([])
              setSelectedServices([])
              setSelectedModules([])
              setSelectedSources([])
              setSelectedFiles([])
            }}>
              Clear filters
            </Button>
          </div>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 flex overflow-hidden">
        {viewMode === 'raw' ? (
          <RawLogTerminal
            fileId={selectedFile}
            filename={selectedFilename}
            searchQuery={searchQuery}
            liveTail={liveTail}
            refreshInterval={refreshInterval}
          />
        ) : (
        <>
        {/* Facets sidebar */}
        <ScrollArea className="w-64 border-r bg-card">
          <div className="p-3 space-y-5">
            {!selectedProject && (
              <p className="text-sm text-muted-foreground text-center py-8">Select a project to explore logs</p>
            )}

            {facets && (
              <>
                <FacetSection
                  title="Status"
                  icon={AlertTriangle}
                  items={(facets.severity || []).map(f => ({ ...f, color: severityColors[f.value] || 'gray' }))}
                  selected={selectedSeverity}
                  onToggle={(v) => toggleFilter(v, selectedSeverity, setSelectedSeverity)}
                />
                <FacetSection
                  title="Host"
                  icon={Server}
                  items={facets.machine_name || []}
                  selected={selectedHosts}
                  onToggle={(v) => toggleFilter(v, selectedHosts, setSelectedHosts)}
                />
                <FacetSection
                  title="Service"
                  icon={Monitor}
                  items={facets.logger || []}
                  selected={selectedServices}
                  onToggle={(v) => toggleFilter(v, selectedServices, setSelectedServices)}
                />
                <FacetSection
                  title="Module"
                  icon={Layers}
                  items={facets.module || []}
                  selected={selectedModules}
                  onToggle={(v) => toggleFilter(v, selectedModules, setSelectedModules)}
                />
              </>
            )}
          </div>
        </ScrollArea>

        {/* Main */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Histogram */}
          <div className="h-48 border-b bg-card p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium">
                {(histogram || []).reduce((a, b) => a + b.count, 0).toLocaleString()} logs
              </div>
              <div className="text-xs text-muted-foreground">
                {preset === 0 ? 'All Time' : `${start.toLocaleString()} → ${end.toLocaleString()}`}
              </div>
            </div>
            <ResponsiveContainer width="100%" height="85%">
              <BarChart data={histogram || []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                <XAxis dataKey="timestamp" tickFormatter={(v) => formatBucket(v, interval)} tick={{ fontSize: 11 }} minTickGap={20} />
                <YAxis tickFormatter={formatShort} tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ fontSize: 12 }}
                  formatter={(value: any) => [Number(value).toLocaleString(), 'Logs']}
                  labelFormatter={(label: any) => new Date(label).toLocaleString()}
                />
                <Bar dataKey="count">
                  {(histogram || []).map((_, i) => (
                    <Cell key={i} fill="#3b82f6" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Table */}
          <ScrollArea className="flex-1">
            <div className="min-w-full">
              {/* Header */}
              <div className="sticky top-0 z-10 flex items-center bg-muted/80 backdrop-blur text-xs font-medium text-muted-foreground border-b">
                <div className="w-40 px-3 py-2">Time</div>
                <div className="w-24 px-3 py-2">Severity</div>
                <div className="w-32 px-3 py-2">Host</div>
                <div className="w-32 px-3 py-2">Service</div>
                <div className="flex-1 px-3 py-2">Message</div>
              </div>

              {entriesLoading ? (
                <div className="p-8 text-center text-muted-foreground">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                  Loading logs...
                </div>
              ) : !selectedProject ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Search className="h-12 w-12 mx-auto mb-3 opacity-30" />
                  <p>Select a project to start exploring logs</p>
                </div>
              ) : (entries || []).length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Search className="h-12 w-12 mx-auto mb-3 opacity-30" />
                  <p>No logs found for the current filters</p>
                </div>
              ) : (
                (entries || []).map((entry: LogEntry) => (
                  <div
                    key={entry.id}
                    onClick={() => { setSelectedEntry(entry); setAiResult(null) }}
                    className={`flex items-center text-sm border-b hover:bg-accent/40 cursor-pointer ${selectedEntry?.id === entry.id ? 'bg-primary/5' : ''}`}
                  >
                    <div className="w-40 px-3 py-2 text-xs text-muted-foreground font-mono">
                      {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '-'}
                    </div>
                    <div className="w-24 px-3 py-2">
                      <Badge variant="outline" className="text-xs capitalize" style={{ borderColor: severityColors[entry.severity], color: severityColors[entry.severity] }}>
                        {entry.severity}
                      </Badge>
                    </div>
                    <div className="w-32 px-3 py-2 truncate text-muted-foreground" title={entry.machine_name || ''}>
                      {entry.machine_name || '-'}
                    </div>
                    <div className="w-32 px-3 py-2 truncate text-muted-foreground" title={entry.logger || ''}>
                      {entry.logger || '-'}
                    </div>
                    <div className="flex-1 px-3 py-2 truncate font-mono text-xs">
                      {entry.message}
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Side panel - Terminal style */}
        {selectedEntry && (
          <div className="w-[480px] border-l flex flex-col animate-in slide-in-from-right duration-200 bg-zinc-950 text-zinc-100">
            {/* Terminal header */}
            <div className="flex items-center justify-between px-4 py-3 bg-zinc-900 border-b border-zinc-800">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-full bg-red-500" />
                  <span className="h-3 w-3 rounded-full bg-yellow-500" />
                  <span className="h-3 w-3 rounded-full bg-green-500" />
                </div>
                <span className="text-xs font-mono text-zinc-400">log_entry_{selectedEntry.id}.log</span>
              </div>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-300 hover:text-white hover:bg-zinc-800" onClick={() => bookmarkMutation.mutate(selectedEntry.id)}>
                  <Bookmark className={`h-4 w-4 ${selectedEntry.bookmarked ? 'text-yellow-500 fill-yellow-500' : ''}`} />
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-300 hover:text-white hover:bg-zinc-800" onClick={() => handleAnalyze(selectedEntry)}>
                  <BrainCircuit className="h-4 w-4" />
                </Button>
                {isAdmin && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-zinc-300 hover:text-white hover:bg-zinc-800"
                    onClick={() => {
                      if (confirm('Are you sure you want to delete this log entry? This cannot be undone.')) {
                        deleteEntryMutation.mutate(selectedEntry.id)
                      }
                    }}
                    disabled={deleteEntryMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4 text-red-400" />
                  </Button>
                )}
                <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-300 hover:text-white hover:bg-zinc-800" onClick={() => setSelectedEntry(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <ScrollArea className="flex-1 p-4 font-mono text-sm">
              <div className="space-y-4">
                {/* Metadata lines */}
                <div className="space-y-1 text-xs text-zinc-400">
                  <div><span className="text-zinc-500">$</span> <span className="text-green-400">timestamp</span>  {selectedEntry.timestamp ? new Date(selectedEntry.timestamp).toISOString() : '-'}</div>
                  <div><span className="text-zinc-500">$</span> <span className="text-green-400">severity</span>   <span style={{ color: severityColors[selectedEntry.severity] || '#fff' }}>{selectedEntry.severity}</span></div>
                  {selectedEntry.machine_name && <div><span className="text-zinc-500">$</span> <span className="text-green-400">host</span>       {selectedEntry.machine_name}</div>}
                  {selectedEntry.logger && <div><span className="text-zinc-500">$</span> <span className="text-green-400">service</span>    {selectedEntry.logger}</div>}
                  {selectedEntry.module && <div><span className="text-zinc-500">$</span> <span className="text-green-400">module</span>     {selectedEntry.module}</div>}
                  {selectedEntry.method && <div><span className="text-zinc-500">$</span> <span className="text-green-400">method</span>     {selectedEntry.method}</div>}
                  {selectedEntry.thread_name && <div><span className="text-zinc-500">$</span> <span className="text-green-400">thread</span>     {selectedEntry.thread_name}</div>}
                  {selectedEntry.request_id && <div><span className="text-zinc-500">$</span> <span className="text-green-400">request_id</span> {selectedEntry.request_id}</div>}
                </div>

                {/* Message */}
                <div>
                  <div className="text-zinc-500 text-xs mb-1"># message</div>
                  <div className="bg-zinc-900/50 border border-zinc-800 rounded p-3 whitespace-pre-wrap text-zinc-200 leading-relaxed">
                    {selectedEntry.message}
                  </div>
                </div>

                {/* Exception */}
                {selectedEntry.exception_type && (
                  <div>
                    <div className="text-red-400 text-xs mb-1"># exception</div>
                    <div className="bg-red-950/20 border border-red-900/30 rounded p-3 text-red-300">
                      <div className="font-bold">{selectedEntry.exception_type}</div>
                      {selectedEntry.exception_message && <div className="text-red-400/80">{selectedEntry.exception_message}</div>}
                    </div>
                  </div>
                )}

                {/* Stack trace */}
                {selectedEntry.stack_trace && (
                  <div>
                    <div className="text-red-400 text-xs mb-1"># stack trace</div>
                    <pre className="bg-zinc-900/80 border border-zinc-800 rounded p-3 overflow-x-auto max-h-80 text-xs text-red-300 whitespace-pre-wrap">
                      {selectedEntry.stack_trace}
                    </pre>
                  </div>
                )}

                {/* Raw line */}
                {selectedEntry.raw_line && selectedEntry.raw_line !== selectedEntry.message && (
                  <div>
                    <div className="text-zinc-500 text-xs mb-1"># raw line</div>
                    <pre className="bg-zinc-900/50 border border-zinc-800 rounded p-3 overflow-x-auto text-xs text-zinc-400 whitespace-pre-wrap">
                      {selectedEntry.raw_line}
                    </pre>
                  </div>
                )}

                {/* AI Analysis */}
                {aiLoading && (
                  <div className="flex items-center gap-2 text-xs text-zinc-400">
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    Analyzing with AI...
                  </div>
                )}
                {aiResult && (
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-primary text-xs font-medium"># ai analysis</div>
                      <ExpandButton onClick={() => openModal('AI Analysis', aiResult)} />
                    </div>
                    <div className="bg-card border border-border rounded p-3">
                      <Markdown content={aiResult} />
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        )}
        </>
        )}
      </div>

      <MarkdownModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title={modalTitle}
        content={modalContent}
      />
    </div>
  )
}

function FacetSection({ title, icon: Icon, items, selected, onToggle }: {
  title: string
  icon: any
  items: { value: string; count: number; color?: string; label?: string }[]
  selected: string[]
  onToggle: (value: string) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const visible = expanded ? items : items.slice(0, 5)

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-sm font-medium mb-2"
      >
        <span className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {title}
        </span>
        <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${expanded ? '' : '-rotate-90'}`} />
      </button>
      <div className="space-y-1">
        {visible.map((item) => {
          const value = item.value
          const isSelected = selected.includes(value)
          return (
            <label
              key={value}
              className={`flex items-center justify-between px-2 py-1.5 rounded text-sm cursor-pointer hover:bg-accent ${isSelected ? 'bg-primary/10' : ''}`}
            >
              <span className="flex items-center gap-2 min-w-0">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onToggle(value)}
                  className="shrink-0"
                />
                {item.color && (
                  <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                )}
                <span className="truncate" title={item.label || value}>{item.label || value}</span>
              </span>
              <span className="text-xs text-muted-foreground shrink-0">{formatShort(item.count)}</span>
            </label>
          )
        })}
        {items.length === 0 && <p className="text-xs text-muted-foreground px-2">No values</p>}
      </div>
      {items.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-primary mt-1 hover:underline"
        >
          {expanded ? 'Show less' : `Show ${items.length - 5} more`}
        </button>
      )}
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-muted/50 rounded-lg p-2">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-medium truncate" title={value}>{value}</div>
    </div>
  )
}
