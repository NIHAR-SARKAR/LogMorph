import { X, Maximize2 } from 'lucide-react'
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Markdown } from './markdown'
import { ScrollArea } from './scroll-area'

interface MarkdownModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  content: string
}

export function MarkdownModal({ open, onOpenChange, title, content }: MarkdownModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Maximize2 className="h-4 w-4 text-primary" />
          {title}
        </DialogTitle>
      </DialogHeader>
      <ScrollArea className="max-h-[60vh] pr-4">
        <div className="py-2">
          <Markdown content={content} />
        </div>
      </ScrollArea>
      <DialogFooter>
        <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
          <X className="h-4 w-4 mr-1" />
          Close
        </Button>
      </DialogFooter>
    </Dialog>
  )
}

interface ExpandButtonProps {
  onClick: () => void
  className?: string
}

export function ExpandButton({ onClick, className = '' }: ExpandButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors ${className}`}
      title="Open in full view"
    >
      <Maximize2 className="h-3 w-3" />
      Expand
    </button>
  )
}
