import { useEffect, useState } from 'react'
import type { StockSymbol } from '../types/market'

const STORAGE_KEY = 'a-trade.watchlist'

export const defaultWatchList: StockSymbol[] = [
  { symbol: 'SH.600519', code: '600519', name: '贵州茅台', market: 'SH', source: 'preset' },
  { symbol: 'SZ.000001', code: '000001', name: '平安银行', market: 'SZ', source: 'preset' },
  { symbol: 'SZ.300750', code: '300750', name: '宁德时代', market: 'SZ', source: 'preset' }
]

export function useWatchList() {
  const [watchList, setWatchList] = useState<StockSymbol[]>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return defaultWatchList
    try {
      const parsed = JSON.parse(stored) as StockSymbol[]
      return parsed.length ? parsed : defaultWatchList
    } catch {
      return defaultWatchList
    }
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(watchList))
  }, [watchList])

  const add = (symbol: StockSymbol) => {
    setWatchList((current) => (current.some((item) => item.symbol === symbol.symbol) ? current : [symbol, ...current]))
  }

  const remove = (symbol: string) => {
    setWatchList((current) => current.filter((item) => item.symbol !== symbol))
  }

  return { watchList, add, remove }
}
