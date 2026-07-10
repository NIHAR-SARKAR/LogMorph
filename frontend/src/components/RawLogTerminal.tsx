import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Search, ChevronUp, ChevronDown, Terminal, RefreshCw, X
} from 'lucide-react'
import { logApi } from '@/services/api'
import type { RawLogResponse } from '@/types'

const PAGE_SIZE = 500

const severityStyles: { pattern: RegExp; color: string }[] = [
  { pattern: /\b(FATAL|fatal)\b/, color: 'text-red-500 font-semibold' },
  { pattern: /\b(CRITICAL|critical|CRIT)\b/, color: 'text-red-500 font-semibold' },
  { pattern: /\bERROR\b|\berror\b/, color: 'text-red-400' },
  { pattern: /\b(WARN|WARNING|warn|warning)\b/, color: 'text-amber-400' },
  { pattern: /\bINFO\b|\binfo\b/, color: 'text-green-400' },
  { pattern: /\bDEBUG\b|\bdebug\b/, color: 'text-cyan-400' },
  { pattern: /\bTRACE\b|\btrace\b/, color: 'text-zinc-500' },
]

function getLineClass(content: string): string {
  for (const { pattern, color } of severityStyles) {
    if (pattern.test(content)) return color
  }
  return 'text-zinc-300'
}

function highlightSearch(text: string, search: string): React.ReactNode {
  if (!search) return text
  const lower = text.toLowerCase()
  const searchLower = search.toLowerCase()
  const parts: React.ReactNode[] = []
  let remaining = text
  let remainingLower = lower
  let key = 0

  while (remainingLower.length > 0) {
    const idx = remainingLower.indexOf(searchLower)
    if (idx === -1) {
      parts.push(remaining)
      break
    }
    if (idx > 0) {
      parts.push(remaining.slice(0, idx))
    }
    parts.push(
      <mark key={key++} className="bg-yellow-500/30 text-yellow-200 rounded px-0.5">
        {remaining.slice(idx, idx + search.length)}
      </mark>
    )
    remaining = remaining.slice(idx + search.length)
    remainingLower = remainingLower.slice(idx + search.length)
  }
  return parts
}

interface RawLogTerminalProps {
  fileId: number | ''
  filename: string
  searchQuery: string
  liveTail: boolean
  refreshInterval: number
}

export function RawLogTerminal({
  fileId, filename, searchQuery, liveTail, refreshInterval,
}: RawLogTerminalProps) {
  const [mode, setMode] = useState<'tail' | 'all'>('tail')
  const [offset, setOffset] = useState(0)
  const [loadedLines, setLoadedLines] = useState<RawLogResponse['lines']>([])
  const [totalLines, setTotalLines] = useState(0)
  const [matchedLines, setMatchedLines] = useState(0)
  const [localSearch, setLocalSearch] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const lastFileIdRef = useRef(fileId)
  const lastModeRef = useRef(mode)
  const lastSearchRef = useRef('')

  const effectiveSearch = searchQuery || localSearch

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['raw-log', fileId, mode, offset, effectiveSearch],
    queryFn: () => logApi.rawFile(Number(fileId), {
      offset,
      limit: PAGE_SIZE,
      search: effectiveSearch || undefined,
      tail: mode === 'tail' && offset === 0 && !effectiveSearch,
    }).then(r => r.data as RawLogResponse),
    enabled: !!fileId,
  })

  // Single source of truth for updating loadedLines.
  // On file/mode/search change we REPLACE; on offset increase we APPEND.
  useEffect(() => {
    if (!data) return
    setTotalLines(data.total_lines)
    setMatchedLines(data.matched_lines)

    const epochChanged =
      lastFileIdRef.current !== fileId ||
      lastModeRef.current !== mode ||
      lastSearchRef.current !== effectiveSearch

    if (epochChanged || offset === 0) {
      setLoadedLines(data.lines)
    } else {
      setLoadedLines(prev => [...prev, ...data.lines])
    }

    lastFileIdRef.current = fileId
    lastModeRef.current = mode
    lastSearchRef.current = effectiveSearch
  }, [data, fileId, mode, effectiveSearch, offset])

  // Reset offset when the query "epoch" changes (mode, file, or search).
  useEffect(() => {
    setOffset(0)
  }, [fileId, mode, effectiveSearch])

  // Auto-scroll to bottom in tail mode
  useEffect(() => {
    if (mode === 'tail' && offset === 0 && !effectiveSearch) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [loadedLines, mode, offset, effectiveSearch])

  // Live tail polling
  useEffect(() => {
    if (!liveTail || !fileId) return
    const id = setInterval(() => {
      if (mode === 'tail' && !effectiveSearch) {
        setOffset(0)
        refetch()
      }
    }, Math.max(3000, refreshInterval * 1000))
    return () => clearInterval(id)
  }, [liveTail, refreshInterval, fileId, mode, effectiveSearch, refetch])

  const handleScroll = useCallback(() => {}, [])

  const loadMore = () => {
    setOffset(prev => prev + PAGE_SIZE)
  }

  const jumpToTop = () => {
    setMode('all')
  }

  const jumpToBottom = () => {
    setMode('tail')
  }

  const handleRefresh = () => {
    setOffset(0)
    setLoadedLines([])
    refetch()
  }

  const command = useMemo(() => {
    if (effectiveSearch) return `grep -in "${effectiveSearch}" ${filename || 'logfile'}`
    if (mode === 'tail') return `tail -f ${filename || 'logfile'}`
    return `cat ${filename || 'logfile'}`
  }, [mode, effectiveSearch, filename])

  if (!fileId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-zinc-950">
        <div className="text-center space-y-3">
          <Terminal className="h-12 w-12 text-zinc-700 mx-auto" />
          <p className="text-zinc-600 text-sm font-mono">Select a log file to view raw output</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-zinc-950 min-w-0">
      {/* Terminal title bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-900 border-b border-zinc-800 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="h-3 w-3 rounded-full bg-red-500" />
            <span className="h-3 w-3 rounded-full bg-yellow-500" />
            <span className="h-3 w-3 rounded-full bg-green-500" />
          </div>
          <span className="text-xs font-mono text-zinc-400 truncate">
            {filename || 'logfile'} — raw terminal
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => setMode('tail')}
            className={`px-2 py-1 text-xs font-mono rounded transition-colors ${
              mode === 'tail' ? 'bg-zinc-700 text-green-400' : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            tail
          </button>
          <button
            onClick={() => setMode('all')}
            className={`px-2 py-1 text-xs font-mono rounded transition-colors ${
              mode === 'all' ? 'bg-zinc-700 text-green-400' : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            cat
          </button>
          <div className="w-px h-4 bg-zinc-700 mx-1" />
          <button
            onClick={jumpToTop}
            title="Jump to top"
            className="p-1 text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <ChevronUp className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={jumpToBottom}
            title="Jump to bottom"
            className="p-1 text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={handleRefresh}
            title="Refresh"
            className={`p-1 text-zinc-500 hover:text-zinc-300 transition-colors ${isFetching ? 'animate-spin' : ''}`}
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Command line + local search */}
      <div className="flex items-center gap-2 px-4 py-1.5 bg-zinc-900/50 border-b border-zinc-800/50 shrink-0">
        <span className="text-xs font-mono text-green-500 shrink-0">$</span>
        <span className="text-xs font-mono text-zinc-400 truncate flex-1">{command}</span>
        <div className="relative shrink-0">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-zinc-600" />
          <input
            type="text"
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            placeholder="grep..."
            className="h-7 w-32 pl-7 pr-2 bg-zinc-800 border border-zinc-700 rounded text-xs font-mono text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:border-green-600/50"
          />
          {localSearch && (
            <button
              onClick={() => setLocalSearch('')}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between px-4 py-1 bg-zinc-900/30 border-b border-zinc-800/30 shrink-0">
        <span className="text-[10px] font-mono text-zinc-600">
          {effectiveSearch
            ? `${matchedLines.toLocaleString()} matches in ${totalLines.toLocaleString()} lines`
            : `${totalLines.toLocaleString()} lines total · showing ${loadedLines.length.toLocaleString()}`}
        </span>
        <span className="text-[10px] font-mono text-zinc-600">
          {liveTail && mode === 'tail' && !effectiveSearch && '● following'}
        </span>
      </div>

      {/* Terminal output */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-auto font-mono text-xs leading-relaxed px-2 py-2"
        style={{ scrollbarWidth: 'thin', scrollbarColor: '#3f3f46 #09090b' }}
      >
        {isLoading ? (
          <div className="px-2 py-4 text-zinc-600">
            <RefreshCw className="h-4 w-4 animate-spin inline mr-2" />
            reading {filename}...
          </div>
        ) : loadedLines.length === 0 ? (
          <div className="px-2 py-4 text-zinc-600">
            {effectiveSearch ? `No lines matching "${effectiveSearch}"` : 'File is empty'}
          </div>
        ) : (
          <>
            {loadedLines.map((line) => (
              <div
                key={line.line_number}
                className="flex hover:bg-zinc-900/60 group"
              >
                <span className="text-zinc-700 select-none w-12 shrink-0 text-right pr-3 group-hover:text-zinc-600">
                  {line.line_number}
                </span>
                <span className={`whitespace-pre-wrap break-all ${getLineClass(line.content)}`}>
                  {highlightSearch(line.content, effectiveSearch)}
                </span>
              </div>
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Load more / bottom bar */}
      {loadedLines.length > 0 && (
        <div className="flex items-center justify-center py-2 bg-zinc-900/50 border-t border-zinc-800/50 shrink-0">
          {mode === 'all' || effectiveSearch ? (
            <button
              onClick={loadMore}
              disabled={isFetching || loadedLines.length >= (effectiveSearch ? matchedLines : totalLines)}
              className="px-3 py-1.5 text-xs font-mono text-green-500 hover:text-green-400 hover:bg-zinc-800 rounded transition-colors disabled:text-zinc-700 disabled:cursor-not-allowed"
            >
              {isFetching ? 'loading...' : 'load more ↓'}
            </button>
          ) : (
            <button
              onClick={jumpToTop}
              className="px-3 py-1.5 text-xs font-mono text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded transition-colors"
            >
              ↑ load from top
            </button>
          )}
        </div>
      )}
    </div>
  )
}
