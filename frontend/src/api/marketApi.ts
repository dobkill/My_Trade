import type { AdjustKey, HealthResponse, KLineResponse, PeriodKey, Quote, StockSymbol } from '../types/market'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

export function apiBaseUrl(): string {
  return API_BASE.replace(/\/$/, '')
}

export function websocketUrl(symbol: string): string {
  const base = apiBaseUrl().replace(/^http/, 'ws')
  return `${base}/ws/stocks/${encodeURIComponent(symbol)}`
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`)
  if (!response.ok) {
    const payload = await response.json().catch(() => undefined)
    const message = payload?.detail?.message ?? payload?.detail ?? response.statusText
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }
  return response.json() as Promise<T>
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health')
}

export async function searchSymbols(q: string): Promise<StockSymbol[]> {
  const payload = await request<{ data: StockSymbol[] }>(`/api/symbols/search?q=${encodeURIComponent(q)}`)
  return payload.data
}

export async function getQuote(symbol: string): Promise<Quote> {
  return request<Quote>(`/api/stocks/${encodeURIComponent(symbol)}/quote`)
}

export async function getKLines(
  symbol: string,
  period: PeriodKey,
  adjust: AdjustKey,
  from?: number,
  to?: number
): Promise<KLineResponse> {
  const params = new URLSearchParams({ period, adjust })
  if (from) params.set('start', new Date(from).toISOString())
  if (to) params.set('end', new Date(to).toISOString())
  return request<KLineResponse>(`/api/stocks/${encodeURIComponent(symbol)}/klines?${params.toString()}`)
}

export function exportUrl(symbol: string, period: PeriodKey, adjust: AdjustKey, format: 'csv' | 'parquet'): string {
  const params = new URLSearchParams({ period, adjust, format })
  return `${apiBaseUrl()}/api/stocks/${encodeURIComponent(symbol)}/export?${params.toString()}`
}
