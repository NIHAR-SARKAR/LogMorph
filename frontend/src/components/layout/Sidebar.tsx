import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, FolderOpen, Search, Bell, Settings, LogOut,
  ChevronLeft, ChevronRight, FileText, BrainCircuit, Shield,
  Menu, X, Sparkles
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useAppStore } from '@/store/appStore'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
  { icon: FolderOpen, label: 'Projects', path: '/projects' },
  { icon: Search, label: 'Log Viewer', path: '/logs' },
  { icon: BrainCircuit, label: 'AI Analysis', path: '/analysis' },
  { icon: FileText, label: 'Parsers', path: '/parsers' },
  { icon: Bell, label: 'Alerts', path: '/alerts' },
  { icon: Shield, label: 'Users', path: '/users' },
  { icon: Settings, label: 'Settings', path: '/settings' },
]

export function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useAppStore()
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-card transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-16'
      )}
    >
      <div className="flex h-16 items-center justify-between px-4 border-b">
        <div className="flex items-center gap-2 overflow-hidden">
          <Sparkles className="h-6 w-6 text-primary shrink-0" />
          {sidebarOpen && (
            <span className="font-bold text-lg whitespace-nowrap animate-fade-in">
              LogMorph AI
            </span>
          )}
        </div>
        <Button variant="ghost" size="icon" onClick={toggleSidebar} className="shrink-0">
          {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || location.pathname.startsWith(item.path + '/')
          if (item.path === '/users' && user?.role !== 'admin') return null

          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                !sidebarOpen && 'justify-center px-2'
              )}
              title={item.label}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {sidebarOpen && <span className="whitespace-nowrap">{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      <div className="border-t p-3">
        <div className={cn('flex items-center gap-3', !sidebarOpen && 'justify-center')}>
          <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary shrink-0">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </div>
          {sidebarOpen && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.full_name || user?.username}</p>
              <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
            </div>
          )}
          {sidebarOpen && (
            <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => { logout(); navigate('/login') }}>
              <LogOut className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </aside>
  )
}

export function MobileNav() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  return (
    <>
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 h-14 bg-card border-b flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <span className="font-bold">LogMorph AI</span>
        </div>
        <Button variant="ghost" size="icon" onClick={() => setOpen(!open)}>
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>
      {open && (
        <div className="lg:hidden fixed inset-0 z-40 bg-background pt-14">
          <nav className="p-4 space-y-1">
            {navItems.map((item) => {
              if (item.path === '/users' && user?.role !== 'admin') return null
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setOpen(false)}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium',
                    isActive ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent'
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                </Link>
              )
            })}
            <Separator className="my-4" />
            <button
              onClick={() => { logout(); navigate('/login') }}
              className="flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium text-destructive w-full"
            >
              <LogOut className="h-5 w-5" />
              Logout
            </button>
          </nav>
        </div>
      )}
    </>
  )
}
