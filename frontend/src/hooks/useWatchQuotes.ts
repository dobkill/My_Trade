import { useEffect, useState } from 'react'
import { websocketUrl } from '../api/marketApi'
import type { Quote, StockSymbol } from '../types/market'

const MAX_PARALLEL = 30

type QuoteMap = Record<string, Quote>

interface Watcher {
  ws: WebSocket | null
  retryTimer: number | undefined
  closed: boolean
}

/**
 * 自选股实时行情：为每只自选股维持一条 WebSocket，合并所有 quote 推送。
 * - 服务端已有 /ws/stocks/{symbol} 通道，会下发 { type:'quote', data } 与 { type:'status' }
 * - 仅订阅 quote 类型用于刷新自选列表展示，bar 由主图自身订阅
 * - 超过 MAX_PARALLEL 只订阅前 N 只，避免连接爆炸
 */
export function useWatchQuotes(watchList: StockSymbol[]): QuoteMap {
  const [quotes, setQuotes] = useState<QuoteMap>({})

  useEffect(() => {
    const symbols = watchList.slice(0, MAX_PARALLEL).map((item) => item.symbol)
    if (symbols.length === 0) return

    const watchers = new Map<string, Watcher>()
    const RECONNECT_DELAY = 2000

    symbols.forEach((symbol) => {
      const watcher: Watcher = { ws: null, retryTimer: undefined, closed: false }
      watchers.set(symbol, watcher)

      const connect = () => {
        if (watcher.closed) return
        const ws = new WebSocket(websocketUrl(symbol))
        watcher.ws = ws
        ws.onmessage = (event) => {
          if (watcher.closed) return
          let payload: Record<string, unknown>
          try {
            payload = JSON.parse(event.data)
          } catch {
            return
          }
          if (payload.type === 'quote') {
            const data = payload.data as Quote
            setQuotes((current) => ({ ...current, [symbol]: { ...data, symbol } }))
          }
        }
        ws.onclose = () => {
          if (watcher.closed) return
          watcher.retryTimer = window.setTimeout(connect, RECONNECT_DELAY)
        }
        ws.onerror = () => {
          // 交由 onclose 接管重连
        }
      }
      connect()
    })

    return () => {
      watchers.forEach((watcher) => {
        watcher.closed = true
        if (watcher.retryTimer !== undefined) window.clearTimeout(watcher.retryTimer)
        watcher.ws?.close()
      })
      watchers.clear()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchList.map((item) => item.symbol).join('|')])

  return quotes
}
