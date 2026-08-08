export type PeriodKey = '1m' | '5m' | '15m' | '30m' | '60m' | '1d' | '1w' | '1M'
export type AdjustKey = 'none' | 'qfq' | 'hfq'

export interface StockSymbol {
  symbol: string
  code: string
  name: string
  market: string
  source: string
}

export interface Quote {
  symbol: string
  name?: string | null
  price?: number | null
  open?: number | null
  high?: number | null
  low?: number | null
  pre_close?: number | null
  change?: number | null
  change_pct?: number | null
  volume?: number | null
  turnover?: number | null
  timestamp: number
  source: string
  market_status: string
}

export interface KLineBar {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  turnover: number
}

export interface KLineResponse {
  symbol: string
  period: PeriodKey
  adjust: AdjustKey
  source: string
  data: KLineBar[]
}

export interface HealthResponse {
  status: string
  active_provider?: string | null
  providers: Array<{ provider: string; available: boolean; message: string }>
}

export interface RealtimeStatus {
  state: 'realtime' | 'delayed' | 'closed' | 'reconnecting'
  provider?: string
  message?: string
}
