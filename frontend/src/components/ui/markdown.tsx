import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'

interface MarkdownProps {
  content: string
  className?: string
}

export function Markdown({ content, className = '' }: MarkdownProps) {
  return (
    <div
      className={`
        prose prose-sm max-w-none
        prose-headings:text-foreground
        prose-p:text-foreground
        prose-strong:text-foreground
        prose-li:text-foreground
        prose-a:text-primary hover:prose-a:text-primary/80 prose-a:underline
        prose-code:text-foreground prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-mono
        prose-pre:bg-muted prose-pre:text-foreground prose-pre:rounded-md prose-pre:p-3 prose-pre:my-2 prose-pre:overflow-x-auto
        prose-blockquote:border-l-primary prose-blockquote:bg-muted/50 prose-blockquote:py-1 prose-blockquote:px-3 prose-blockquote:rounded-r-md
        prose-blockquote:text-foreground
        prose-table:text-foreground prose-th:text-foreground prose-td:text-foreground
        prose-hr:border-border
        dark:prose-invert
        ${className}
      `}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          pre: ({ children }) => <pre className="not-prose overflow-x-auto">{children}</pre>,
          code: ({ className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || '')
            const isInline = !match && !String(children).includes('\n')
            return isInline ? (
              <code className="not-prose bg-muted px-1 py-0.5 rounded text-xs font-mono text-foreground" {...props}>
                {children}
              </code>
            ) : (
              <pre className="not-prose bg-muted p-3 rounded-md overflow-x-auto my-2 border border-border">
                <code className="text-xs font-mono text-foreground" {...props}>
                  {children}
                </code>
              </pre>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
