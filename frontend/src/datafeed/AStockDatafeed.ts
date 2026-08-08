import type { Datafeed, DatafeedSubscribeCallback, Period, SymbolInfo } from '@klinecharts/pro'
import type { KLineData } from 'klinecharts'
import { getKLines, searchSymbols, websocketUrl } from '../api/marketApi'
import type { AdjustKey, PeriodKey, Quote, RealtimeStatus } from '../types/market'

type WsEntry = { ws: WebSocket; callback: DatafeedSubscribeCallback }

const A_SHARE_HISTORY_START = 631123200000
const HISTORY_WINDOW_SIZE = 500
const PERIOD_DURATION: Record<PeriodKey, number> = {
  '1m': 60 * 1000,
  '5m': 5 * 60 * 1000,
  '15m': 15 * 60 * 1000,
  '30m': 30 * 60 * 1000,
  '60m': 60 * 60 * 1000,
  '1d': 24 * 60 * 60 * 1000,
  '1w': 7 * 24 * 60 * 60 * 1000,
  '1M': 30 * 24 * 60 * 60 * 1000
}

export class AStockDatafeed implements Datafeed {
  private adjust: AdjustKey
  private readonly sockets = new Map<string, WsEntry>()
  private readonly earliestLoaded = new Map<string, number>()
  private readonly onStatus?: (status: RealtimeStatus) => void
  private readonly onQuote?: (quote: Quote) => void

  constructor(adjust: AdjustKey, onStatus?: (status: RealtimeStatus) => void, onQuote?: (quote: Quote) => void) {
    this.adjust = adjust
    this.onStatus = onStatus
    this.onQuote = onQuote
  }

  setAdjust(adjust: AdjustKey): void {
    this.adjust = adjust
  }

  async searchSymbols(search = ''): Promise<SymbolInfo[]> {
    const symbols = await searchSymbols(search)
    return symbols.map((item) => ({
      ticker: item.symbol,
      name: item.name,
      shortName: item.code,
      exchange: item.market,
      market: 'A股',
      type: 'stock',
      pricePrecision: 2,
      volumePrecision: 0
    }))
  }

  async getHistoryKLineData(symbol: SymbolInfo, period: Period, from: number, to: number): Promise<KLineData[]> {
    const backendPeriod = periodToBackend(period)
    const key = this.historyKey(symbol.ticker, backendPeriod)
    const range = normalizeHistoryRange(backendPeriod, from, to, this.earliestLoaded.get(key))
    try {
      const response = await getKLines(symbol.ticker, backendPeriod, this.adjust, range.from, range.to)
      const data = response.data.map((item) => ({
        timestamp: item.timestamp,
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
        volume: item.volume,
        turnover: item.turnover
      }))
      this.rememberEarliest(key, data)
      return data
    } catch (err) {
      this.onStatus?.({
        state: 'reconnecting',
        message: err instanceof Error ? err.message : '历史行情加载失败'
      })
      return []
    }
  }

  subscribe(symbol: SymbolInfo, period: Period, callback: DatafeedSubscribeCallback): void {
    const key = `${symbol.ticker}:${periodToBackend(period)}`
    this.unsubscribe(symbol, period)
    const ws = new WebSocket(websocketUrl(symbol.ticker))
    this.sockets.set(key, { ws, callback })
    ws.onopen = () => this.onStatus?.({ state: 'realtime' })
    ws.onclose = () => this.onStatus?.({ state: 'reconnecting', message: 'WebSocket 已断开，等待 KLineChart Pro 重新订阅' })
    ws.onerror = () => this.onStatus?.({ state: 'reconnecting', message: 'WebSocket 连接异常' })
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data) as Record<string, unknown>
      if (message.type === 'status') {
        const marketStatus = String(message.market_status ?? '')
        this.onStatus?.({ state: marketStatus === 'closed' ? 'closed' : 'reconnecting', message: String(message.message ?? '') })
        return
      }
      if (message.type === 'quote') {
        const data = message.data as Quote
        this.onQuote?.(data)
        this.onStatus?.({
          state: data.market_status === 'closed' ? 'closed' : 'realtime',
          provider: data.source
        })
        return
      }
      if (message.type === 'bar' && message.period === periodToBackend(period)) {
        const data = message.data as KLineData
        callback(data)
      }
    }
  }

  unsubscribe(symbol: SymbolInfo, period: Period): void {
    const key = `${symbol.ticker}:${periodToBackend(period)}`
    const entry = this.sockets.get(key)
    if (!entry) return
    entry.ws.close()
    this.sockets.delete(key)
  }

  closeAll(): void {
    for (const entry of this.sockets.values()) entry.ws.close()
    this.sockets.clear()
  }

  private historyKey(symbol: string, period: PeriodKey): string {
    return `${symbol}:${period}:${this.adjust}`
  }

  private rememberEarliest(key: string, data: KLineData[]): void {
    const timestamps = data.map((item) => item.timestamp).filter((timestamp): timestamp is number => typeof timestamp === 'number')
    if (!timestamps.length) return
    const earliest = Math.min(...timestamps)
    const previous = this.earliestLoaded.get(key)
    if (previous === undefined || earliest < previous) this.earliestLoaded.set(key, earliest)
  }
}

export function periodToBackend(period: Period): PeriodKey {
  if (period.timespan === 'minute') return `${period.multiplier}m` as PeriodKey
  if (period.timespan === 'hour') return '60m'
  if (period.timespan === 'day') return '1d'
  if (period.timespan === 'week') return '1w'
  if (period.timespan === 'month') return '1M'
  return '1d'
}

export function periodToPro(period: PeriodKey): Period {
  const map: Record<PeriodKey, Period> = {
    '1m': { multiplier: 1, timespan: 'minute', text: '1m' },
    '5m': { multiplier: 5, timespan: 'minute', text: '5m' },
    '15m': { multiplier: 15, timespan: 'minute', text: '15m' },
    '30m': { multiplier: 30, timespan: 'minute', text: '30m' },
    '60m': { multiplier: 1, timespan: 'hour', text: '60m' },
    '1d': { multiplier: 1, timespan: 'day', text: '日' },
    '1w': { multiplier: 1, timespan: 'week', text: '周' },
    '1M': { multiplier: 1, timespan: 'month', text: '月' }
  }
  return map[period]
}

export const proPeriods: Period[] = ['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'].map((item) =>
  periodToPro(item as PeriodKey)
)

export function toProSymbol(symbol: { symbol: string; name: string; code: string; market: string }): SymbolInfo {
  return {
    ticker: symbol.symbol,
    name: symbol.name,
    shortName: symbol.code,
    exchange: symbol.market,
    market: 'A股',
    type: 'stock',
    pricePrecision: 2,
    volumePrecision: 0
  }
}

function normalizeHistoryRange(period: PeriodKey, rawFrom: number, rawTo: number, earliest?: number): { from: number; to: number } {
  const duration = PERIOD_DURATION[period]
  let from = Number.isFinite(rawFrom) ? rawFrom : 0
  let to = Number.isFinite(rawTo) ? rawTo : 0
  const invalidRange = from <= 0 || to <= 0 || from >= to || to < A_SHARE_HISTORY_START

  if (invalidRange) {
    to = (earliest ?? Date.now()) - duration
    from = to - duration * HISTORY_WINDOW_SIZE
  }

  if (to <= A_SHARE_HISTORY_START) {
    to = Date.now()
  }
  if (from < A_SHARE_HISTORY_START) {
    from = A_SHARE_HISTORY_START
  }
  if (from >= to) {
    from = Math.max(A_SHARE_HISTORY_START, to - duration * HISTORY_WINDOW_SIZE)
  }
  return { from, to }
}
