/**
 * 画线/图表状态按 symbol 持久化到 localStorage。
 * 之所以按 symbol 而非全局，是因为不同股票的画线坐标（timestamp+value）互不通用。
 */

const STORAGE_PREFIX = 'a-trade.chart.'

export interface OverlaySnapshot {
  name: string
  points: Array<{ timestamp?: number; value?: number }>
  styles?: unknown
}

export interface ChartState {
  overlays: OverlaySnapshot[]
}

export function loadSymbolChartState(symbol: string): ChartState | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + symbol)
    if (!raw) return null
    const parsed = JSON.parse(raw) as ChartState
    return Array.isArray(parsed?.overlays) ? parsed : null
  } catch {
    return null
  }
}

export function saveSymbolChartState(symbol: string, state: ChartState): void {
  try {
    window.localStorage.setItem(STORAGE_PREFIX + symbol, JSON.stringify(state))
  } catch {
    /* 配额超限等，忽略 */
  }
}

export function clearSymbolChartState(symbol: string): void {
  window.localStorage.removeItem(STORAGE_PREFIX + symbol)
}
