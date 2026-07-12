import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  BrainCircuit, MessageSquare, Send, Sparkles, Loader2,
  TrendingUp, AlertTriangle, Lightbulb, FileSearch
} from 'lucide-react'
import { useState as useLocalState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { aiApi, logApi, projectApi } from '@/services/api'
import { useToast } from '@/components/ui/toast'
import { Markdown } from '@/components/ui/markdown'
import { MarkdownModal, ExpandButton } from '@/components/ui/markdown-modal'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export function AnalysisPage() {
  const [activeTab, setActiveTab] = useState('chat')
  const [chatInput, setChatInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Hello! I am your AI log analysis assistant. Ask me anything about your logs - I can help summarize errors, find patterns, explain exceptions, and more.',
      timestamp: new Date()
    }
  ])
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [analyzingException, setAnalyzingException] = useState<string | null>(null)
  const [exceptionAnalysis, setExceptionAnalysis] = useState<Record<string, string>>({})
  const { addToast } = useToast()

  const [modalOpen, setModalOpen] = useState(false)
  const [modalTitle, setModalTitle] = useState('')
  const [modalContent, setModalContent] = useState('')

  const openModal = (title: string, content: string) => {
    setModalTitle(title)
    setModalContent(content)
    setModalOpen(true)
  }

  const { data: topExceptions } = useQuery({
    queryKey: ['top-exceptions'],
    queryFn: () => logApi.topExceptions({ limit: 10 }).then(r => r.data)
  })

  const { data: severityDist } = useQuery({
    queryKey: ['severity-distribution'],
    queryFn: () => logApi.severityDistribution({ days: 7 }).then(r => r.data)
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectApi.list().then(r => r.data)
  })

  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)

  const handleAnalyzeException = async (exceptionType: string, count: number) => {
    setAnalyzingException(exceptionType)
    try {
      const response = await aiApi.analyzeException(
        exceptionType,
        `Exception ${exceptionType} occurred ${count} times in the selected time range.`
      )
      const data = response.data
      if (data.error) {
        addToast({
          title: `AI analysis error: ${data.provider || 'unknown'}`,
          description: data.error,
          variant: 'destructive'
        })
        setExceptionAnalysis(prev => ({ ...prev, [exceptionType]: `Error: ${data.error}` }))
      } else {
        setExceptionAnalysis(prev => ({ ...prev, [exceptionType]: data.content || 'No analysis returned.' }))
      }
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || 'Unknown error'
      addToast({
        title: 'AI analysis failed',
        description: String(detail),
        variant: 'destructive'
      })
    } finally {
      setAnalyzingException(null)
    }
  }

  const handleSendMessage = async (text?: string) => {
    const content = text || chatInput
    if (!content.trim()) return

    const userMsg: ChatMessage = {
      role: 'user',
      content: content.trim(),
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMsg])
    if (!text) setChatInput('')
    setIsChatLoading(true)

    try {
      const response = await aiApi.chat({
        messages: messages.slice(-5).concat(userMsg).map(m => ({
          role: m.role,
          content: m.content
        })),
        project_id: selectedProjectId || undefined,
        max_tokens: 500,
      })

      const data = response.data
      if (data.error) {
        const errorMsg: ChatMessage = {
          role: 'assistant',
          content: `Error: ${data.error}`,
          timestamp: new Date()
        }
        setMessages(prev => [...prev, errorMsg])
        addToast({
          title: `AI Error (${data.provider || 'unknown'})`,
          description: data.error,
          variant: 'destructive'
        })
      } else {
        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: data.content || 'I apologize, but I could not process your request.',
          timestamp: new Date()
        }
        setMessages(prev => [...prev, assistantMsg])
      }
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unknown error'
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: `Error: ${detail}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMsg])
      addToast({
        title: 'AI Error',
        description: String(detail),
        variant: 'destructive'
      })
    } finally {
      setIsChatLoading(false)
    }
  }

  const quickQuestions = [
    'Why did production fail?',
    'Show authentication errors',
    'Which service is unstable?',
    'Summarize yesterday\'s logs',
    'Find memory leaks',
    'Compare errors vs warnings'
  ]

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col p-6">
      <div className="mb-4">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <BrainCircuit className="h-8 w-8 text-primary" />
          AI Analysis
        </h1>
        <p className="text-muted-foreground">Intelligent log analysis powered by AI</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="chat">
            <MessageSquare className="h-4 w-4 mr-2" />
            AI Chat
          </TabsTrigger>
          <TabsTrigger value="insights">
            <Lightbulb className="h-4 w-4 mr-2" />
            Insights
          </TabsTrigger>
          <TabsTrigger value="exceptions">
            <AlertTriangle className="h-4 w-4 mr-2" />
            Exceptions
          </TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="flex-1 flex flex-col mt-4">
          <Card className="flex-1 flex flex-col">
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                        <Sparkles className="h-4 w-4 text-primary" />
                      </div>
                    )}
                    <div
                      className={`max-w-[80%] rounded-lg p-3 text-sm ${
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-card border border-border shadow-sm'
                      }`}
                    >
                      {msg.role === 'assistant' ? (
                        <div className="text-foreground">
                          <Markdown content={msg.content} />
                          <ExpandButton
                            onClick={() => openModal('AI Response', msg.content)}
                            className="mt-2"
                          />
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      )}
                      <span className="text-xs opacity-50 mt-1 block">
                        {msg.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))}
                {isChatLoading && (
                  <div className="flex gap-3">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <Sparkles className="h-4 w-4 text-primary animate-pulse" />
                    </div>
                    <div className="bg-muted rounded-lg p-3">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Project Selector */}
            <div className="px-4 py-2 border-t">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground whitespace-nowrap">Project:</span>
                <select
                  className="flex-1 h-8 rounded-md border border-input bg-background px-2 text-xs"
                  value={selectedProjectId || ''}
                  onChange={(e) => setSelectedProjectId(e.target.value ? Number(e.target.value) : null)}
                >
                  <option value="">All projects</option>
                  {(projects || []).map((p: any) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
                {selectedProjectId && (
                  <Badge variant="outline" className="text-xs">
                    Scoped
                  </Badge>
                )}
              </div>
            </div>

            {/* Quick Questions */}
            <div className="px-4 py-2 border-t">
              <div className="flex gap-2 overflow-x-auto pb-2">
                {quickQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSendMessage(q)}
                    className="text-xs px-3 py-1.5 rounded-full border bg-background hover:bg-accent whitespace-nowrap transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>

            {/* Input */}
            <div className="p-4 border-t">
              <div className="flex gap-2">
                <Input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about your logs..."
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  className="flex-1"
                />
                <Button onClick={() => handleSendMessage()} disabled={isChatLoading || !chatInput.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="insights" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-primary" />
                  Error Trends
                </CardTitle>
                <CardDescription>Top error patterns detected</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(topExceptions || []).slice(0, 5).map((exc: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <div>
                        <p className="font-mono text-sm">{exc.exception_type}</p>
                        <p className="text-xs text-muted-foreground">{exc.count} occurrences</p>
                      </div>
                      <Badge variant="destructive">{exc.count}</Badge>
                    </div>
                  ))}
                  {(topExceptions || []).length === 0 && (
                    <p className="text-muted-foreground text-sm">No exceptions found</p>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileSearch className="h-5 w-5 text-primary" />
                  AI Recommendations
                </CardTitle>
                <CardDescription>Smart suggestions based on log patterns</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
                    <div className="flex items-center gap-2 text-amber-800 dark:text-amber-400 font-medium text-sm">
                      <AlertTriangle className="h-4 w-4" />
                      High Error Rate Detected
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      Error rate is 3x higher than last week. Consider reviewing recent deployments.
                    </p>
                  </div>
                  <div className="p-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <div className="flex items-center gap-2 text-blue-800 dark:text-blue-400 font-medium text-sm">
                      <Lightbulb className="h-4 w-4" />
                      Missing Log Rotation
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      Some log files are growing beyond recommended size. Enable rotation.
                    </p>
                  </div>
                  <div className="p-3 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg">
                    <div className="flex items-center gap-2 text-green-800 dark:text-green-400 font-medium text-sm">
                      <TrendingUp className="h-4 w-4" />
                      Performance Improvement
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      Response times have improved by 15% since last deployment.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="exceptions" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Exception Analysis</CardTitle>
              <CardDescription>Detailed breakdown of all exceptions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {(topExceptions || []).map((exc: any, i: number) => (
                  <div key={i} className="flex flex-col p-4 border rounded-lg hover:bg-accent/50 transition-colors space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-muted-foreground font-mono text-sm w-8">#{i + 1}</span>
                        <div>
                          <p className="font-mono text-sm font-medium">{exc.exception_type}</p>
                          <p className="text-xs text-muted-foreground">{exc.count} occurrences</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={exc.count > 100 ? 'destructive' : 'secondary'}>
                          {exc.count}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleAnalyzeException(exc.exception_type, exc.count)}
                          disabled={analyzingException === exc.exception_type}
                        >
                          <BrainCircuit className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    {analyzingException === exc.exception_type && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Analyzing with AI...
                      </div>
                    )}
                    {exceptionAnalysis[exc.exception_type] && (
                      <div className="bg-card border border-border rounded-lg p-3 text-sm">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-1 text-primary text-xs font-medium">
                            <Sparkles className="h-3 w-3" />
                            AI Analysis
                          </div>
                          <ExpandButton
                            onClick={() => openModal(`Analysis: ${exc.exception_type}`, exceptionAnalysis[exc.exception_type])}
                          />
                        </div>
                        <Markdown content={exceptionAnalysis[exc.exception_type]} />
                      </div>
                    )}
                  </div>
                ))}
                {(topExceptions || []).length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-3 opacity-30" />
                    <p>No exceptions found in the current time range</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <MarkdownModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title={modalTitle}
        content={modalContent}
      />
    </div>
  )
}
