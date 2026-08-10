import { useCallback, useEffect, useRef, useState } from 'react'
import { KLineChartPro } from '@klinecharts/pro'
import type { ActionCallback } from 'klinecharts'
import { ActionType } from 'klinecharts'
import '@klinecharts/pro/dist/klinecharts-pro.css'
import type { AStockDatafeed } from '../datafeed/AStockDatafeed'
import { OrderBookPanel } from './OrderBookPanel'
import { periodToPro, proPeriods, toProSymbol } from '../datafeed/AStockDatafeed'
import type { Theme } from '../hooks/useTheme'
import { formatVolume } from '../utils/format'
import { loadSymbolChartState, saveSymbolChartState } from '../utils/chartStorage'
import type { OverlaySnapshot } from '../utils/chartStorage'
import type { AdjustKey, PeriodKey, StockSymbol } from '../types/market'

interface Props {
  symbol: StockSymbol
  period: PeriodKey
  adjust: AdjustKey
  theme: Theme
  datafeed: AStockDatafeed
  /** 当前最新价，用于五档盘口与浮窗 */
  lastPrice?: number | null
  /** 父组件可通过此回调拿到"删除当前画线"函数，用于键盘快捷键 */
  registerDeleteOverlay?: (fn: (() => void) | null) => void
}

type ProInstance = InstanceType<typeof KLineChartPro>

interface CrosshairData {
  open: number
  high: number
  low: number
  close: number
  volume: number
  change: number
  changePct: number
}

const SYNC_RETRY_DELAYS = [0, 250, 750, 1500, 3000]

const darkStyles = {
  grid: {
    horizontal: { color: '#1f2937', size: 1 },
    vertical: { color: '#1f2937', size: 1 }
  },
  candle: {
    bar: {
      upColor: '#ef4444',
      downColor: '#22c55e',
      noChangeColor: '#9ca3af',
      upBorderColor: '#ef4444',
      downBorderColor: '#22c55e',
      noChangeBorderColor: '#9ca3af',
      upWickColor: '#ef4444',
      downWickColor: '#22c55e',
      noChangeWickColor: '#9ca3af'
    }
  },
  xAxis: {
    tickText: { color: '#94a3b8' },
    axisLine: { color: '#273244' }
  },
  yAxis: {
    tickText: { color: '#94a3b8' },
    axisLine: { color: '#273244' }
  },
  separator: {
    color: '#273244'
  },
  overlay: {
    line: { color: '#f59e0b', size: 2 },
    point: { color: '#f59e0b', borderColor: '#111827' }
  }
}

const lightStyles = {
  grid: {
    horizontal: { color: '#e2e8f0', size: 1 },
    vertical: { color: '#e2e8f0', size: 1 }
  },
  candle: {
    bar: {
      upColor: '#dc2626',
      downColor: '#16a34a',
      noChangeColor: '#64748b',
      upBorderColor: '#dc2626',
      downBorderColor: '#16a34a',
      noChangeBorderColor: '#64748b',
      upWickColor: '#dc2626',
      downWickColor: '#16a34a',
      noChangeWickColor: '#64748b'
    }
  },
  xAxis: {
    tickText: { color: '#475569' },
    axisLine: { color: '#cbd5e1' }
  },
  yAxis: {
    tickText: { color: '#475569' },
    axisLine: { color: '#cbd5e1' }
  },
  separator: {
    color: '#cbd5e1'
  },
  overlay: {
    line: { color: '#d97706', size: 2 },
    point: { color: '#d97706', borderColor: '#ffffff' }
  }
}

function stylesFor(theme: Theme) {
  return theme === 'light' ? lightStyles : darkStyles
}

export function ChartPanel({ symbol, period, adjust, theme, datafeed, lastPrice, registerDeleteOverlay }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<ProInstance | null>(null)
  const didRunSymbolSync = useRef(false)
  const didRunPeriodSync = useRef(false)
  const [tip, setTip] = useState<CrosshairData | null>(null)

  const deleteOverlay = useCallback(() => {
    const api = getChartApi(chartRef.current)
    api?.removeOverlay?.()
  }, [])

  // 注册/注销删除画线函数，供父组件快捷键调用
  useEffect(() => {
    registerDeleteOverlay?.(deleteOverlay)
    return () => registerDeleteOverlay?.(null)
  }, [deleteOverlay, registerDeleteOverlay])

  useEffect(() => {
    if (!containerRef.current) return
    datafeed.setAdjust(adjust)
    chartRef.current = new KLineChartPro({
      container: containerRef.current,
      symbol: toProSymbol(symbol),
      period: periodToPro(period),
      periods: proPeriods,
      timezone: 'Asia/Shanghai',
      locale: 'zh-CN',
      theme,
      drawingBarVisible: true,
      mainIndicators: ['MA', 'EMA'],
      subIndicators: ['VOL', 'MACD', 'RSI', 'KDJ'],
      styles: stylesFor(theme),
      datafeed
    })

    // 十字光标浮窗：订阅底层图表的 onCrosshairChange
    const api = getChartApi(chartRef.current)
    const onCrosshairChange = crosshairHandler(setTip)
    if (hasActionApi(api)) {
      api.subscribeAction(ActionType.OnCrosshairChange, onCrosshairChange)
      // 恢复该 symbol 的画线
      restoreOverlays(api, symbol.symbol)
    }

    return () => {
      // 保存该 symbol 的画线后再卸载
      if (hasActionApi(api)) {
        api.unsubscribeAction(ActionType.OnCrosshairChange, onCrosshairChange)
        captureOverlays(api, symbol.symbol)
      }
      datafeed.closeAll()
      chartRef.current = null
      containerRef.current?.replaceChildren()
    }
  }, [])

  // 主题切换联动
  useEffect(() => {
    chartRef.current?.setTheme(theme)
    chartRef.current?.setStyles(stylesFor(theme))
  }, [theme])

  useEffect(() => {
    if (!didRunSymbolSync.current) {
      didRunSymbolSync.current = true
      return
    }
    return scheduleChartSync(() => {
      datafeed.setAdjust(adjust)
      chartRef.current?.setSymbol(toProSymbol(symbol))
    })
  }, [symbol.symbol, symbol.name, symbol.code, symbol.market, adjust, datafeed])

  useEffect(() => {
    if (!didRunPeriodSync.current) {
      didRunPeriodSync.current = true
      return
    }
    return scheduleChartSync(() => {
      datafeed.setAdjust(adjust)
      chartRef.current?.setPeriod(periodToPro(period))
    })
  }, [period, adjust, datafeed])

  const handleScreenshot = () => {
    const api = getChartApi(chartRef.current)
    if (!api) return
    const url = api.screenshot?.() ?? api.getConvertPictureUrl?.(true, 'png', theme === 'dark' ? '#151517' : '#ffffff')
    if (!url) return
    const link = document.createElement('a')
    link.download = `${symbol.code}-${period}-${Date.now()}.png`
    link.href = url
    link.click()
  }

  return (
    <section className="chart-panel">
      <div className="chart-toolbar-hint">
        <span className="hint-group">
          <span>画线：趋势线/水平线/线段/价格线/斐波那契/通道（自动按股票保存）</span>
        </span>
        <span className="hint-group">
          <span>指标：MA / EMA / VOL / MACD / RSI / KDJ</span>
          <button type="button" className="chart-action" onClick={handleScreenshot} title="导出当前图表为 PNG">
            📷 截图
          </button>
        </span>
      </div>
      <div className="kline-pro-host">
        <CrosshairTip symbol={symbol} data={tip} />
        <OrderBookPanel symbol={symbol.symbol} lastPrice={lastPrice ?? tip?.close} />
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      </div>
    </section>
  )
}

function CrosshairTip({ symbol, data }: { symbol: StockSymbol; data: CrosshairData | null }) {
  if (!data) return <div className="crosshair-tip hidden" />
  const trend = data.change > 0 ? 'trend-up' : data.change < 0 ? 'trend-down' : 'trend-flat'
  const sign = data.change > 0 ? '+' : ''
  return (
    <div className="crosshair-tip">
      <div className="tip-title">
        <span>{symbol.code} {symbol.name}</span>
      </div>
      <div className="tip-row"><span className="label">开盘</span><span>{fmt(data.open)}</span></div>
      <div className="tip-row"><span className="label">最高</span><span className="trend-up">{fmt(data.high)}</span></div>
      <div className="tip-row"><span className="label">最低</span><span className="trend-down">{fmt(data.low)}</span></div>
      <div className="tip-row"><span className="label">收盘</span><span className={trend}>{fmt(data.close)}</span></div>
      <div className="tip-row"><span className="label">涨跌</span><span className={trend}>{sign}{fmt(data.change)} ({sign}{data.changePct.toFixed(2)}%)</span></div>
      <div className="tip-row"><span className="label">成交量</span><span>{formatVolume(data.volume)}</span></div>
    </div>
  )
}

function fmt(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
}

interface ChartApi {
  subscribeAction?(type: ActionType, callback: ActionCallback): void
  unsubscribeAction?(type: ActionType, callback?: ActionCallback): void
  getDataList?(): Array<{ open: number; high: number; low: number; close: number; volume?: number }>
  getOverlayList?(): OverlayItem[]
  createOverlay?(value: unknown): unknown
  removeOverlay?(remove?: unknown): void
  screenshot?(): string | undefined
  getConvertPictureUrl?(includeOverlay?: boolean, type?: string, backgroundColor?: string): string
}

interface OverlayItem {
  name: string
  points: Array<{ timestamp?: number; value?: number }>
  styles?: unknown
}

type SetTip = (data: CrosshairData | null) => void

function getChartApi(chart: ProInstance | null): ChartApi | null {
  const maybeChart = chart as unknown as { _chartApi?: ChartApi } | null
  return maybeChart?._chartApi ?? null
}

function hasActionApi(api: ChartApi | null): api is ChartApi & Required<Pick<ChartApi, 'subscribeAction' | 'unsubscribeAction'>> {
  return typeof api?.subscribeAction === 'function' && typeof api.unsubscribeAction === 'function'
}

function crosshairHandler(setTip: SetTip): ActionCallback {
  return (payload) => {
    const data = payload as { kLineData?: { open: number; high: number; low: number; close: number; volume?: number; preClose?: number } } | undefined
    const k = data?.kLineData
    if (!k) {
      setTip(null)
      return
    }
    const pre = k.preClose ?? k.close
    const change = k.close - pre
    const changePct = pre ? (change / pre) * 100 : 0
    setTip({
      open: k.open,
      high: k.high,
      low: k.low,
      close: k.close,
      volume: k.volume ?? 0,
      change,
      changePct
    })
  }
}

function restoreOverlays(api: ChartApi, symbol: string): void {
  const state = loadSymbolChartState(symbol)
  if (!state?.overlays?.length) return
  state.overlays.forEach((overlay: OverlaySnapshot) => {
    try {
      api.createOverlay?.({ name: overlay.name, points: overlay.points, styles: overlay.styles })
    } catch {
      /* 忽略不支持的画线类型 */
    }
  })
}

function captureOverlays(api: ChartApi, symbol: string): void {
  const list = api.getOverlayList?.() ?? []
  if (!list.length) return
  const overlays = list.map((item) => ({
    name: item.name,
    points: item.points.map((p) => ({ timestamp: p.timestamp, value: p.value })),
    styles: item.styles
  }))
  saveSymbolChartState(symbol, { overlays })
}

function scheduleChartSync(sync: () => void): () => void {
  const timers = SYNC_RETRY_DELAYS.map((delay) => window.setTimeout(sync, delay))
  return () => timers.forEach((timer) => window.clearTimeout(timer))
}
