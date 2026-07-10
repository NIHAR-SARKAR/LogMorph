import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SearchState {
  query: string
  isRegex: boolean
  caseSensitive: boolean
  wholeWord: boolean
  severity: string[]
  dateRange: { start: string | null; end: string | null }
  setQuery: (query: string) => void
  setIsRegex: (val: boolean) => void
  setCaseSensitive: (val: boolean) => void
  setWholeWord: (val: boolean) => void
  setSeverity: (severity: string[]) => void
  setDateRange: (range: { start: string | null; end: string | null }) => void
  resetFilters: () => void
}

export const useSearchStore = create<SearchState>()(
  persist(
    (set) => ({
      query: '',
      isRegex: false,
      caseSensitive: false,
      wholeWord: false,
      severity: [],
      dateRange: { start: null, end: null },
      setQuery: (query) => set({ query }),
      setIsRegex: (val) => set({ isRegex: val }),
      setCaseSensitive: (val) => set({ caseSensitive: val }),
      setWholeWord: (val) => set({ wholeWord: val }),
      setSeverity: (severity) => set({ severity }),
      setDateRange: (range) => set({ dateRange: range }),
      resetFilters: () => set({
        query: '',
        isRegex: false,
        caseSensitive: false,
        wholeWord: false,
        severity: [],
        dateRange: { start: null, end: null },
      }),
    }),
    {
      name: 'search-storage',
    }
  )
)
