import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppState {
  theme: 'light' | 'dark' | 'system'
  sidebarOpen: boolean
  currentProject: number | null
  currentEnvironment: number | null
  linesPerPage: number
  refreshInterval: number
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setSidebarOpen: (open: boolean) => void
  setCurrentProject: (id: number | null) => void
  setCurrentEnvironment: (id: number | null) => void
  setLinesPerPage: (value: number) => void
  setRefreshInterval: (value: number) => void
  toggleSidebar: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: 'system',
      sidebarOpen: true,
      currentProject: null,
      currentEnvironment: null,
      linesPerPage: 1000,
      refreshInterval: 30,
      setTheme: (theme) => set({ theme }),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setCurrentProject: (id) => set({ currentProject: id }),
      setCurrentEnvironment: (id) => set({ currentEnvironment: id }),
      setLinesPerPage: (value) => set({ linesPerPage: value }),
      setRefreshInterval: (value) => set({ refreshInterval: value }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({
        theme: state.theme,
        sidebarOpen: state.sidebarOpen,
        currentProject: state.currentProject,
        linesPerPage: state.linesPerPage,
        refreshInterval: state.refreshInterval,
      }),
    }
  )
)
