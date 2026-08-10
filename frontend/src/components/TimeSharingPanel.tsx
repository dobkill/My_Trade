import { useEffect, useRef } from 'react'
import { CandleType, dispose, init, YAxisPosition } from 'klinecharts'
import type { Chart, DeepPartial, Styles } from 'klinecharts'
import { getKLines } from '../api/marketApi'
import type { AdjustKey } from '../types/market'
import type { Theme } from '../hooks/useTheme'
import { formatPrice } from '../utils/format'

interface Props {
  symbolCode: string
  symbol: string
  name: string
  adjust: AdjustKey
  theme: Theme
  preClose?: number | null
}

interface MinuteBar {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  turnover: number
}

/**
 * 分时图：当日 1m 数据，价格面积线 + 成交量副图。
 * 以昨收为基准，红涨绿跌着色。后端已有 1m period，无需额外接口。
 */
export function TimeSharingPanel({ symbolCode, symbol, name, adjust, theme, preClose }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<Chart | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const chart = init(containerRef.current, {
      styles: theme === 'light' ? lightTimeStyles(preClose ?? null) : darkTimeStyles(preClose ?? null)
    })
    if (!chart) return
    chartRef.current = chart
    chart.createIndicator('VOL', false, { id: 'pane_vol' })

    let alive = true
    const load = async () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
      try {
        const resp = await getKLines(symbol, '1m', adjust, start, now.getTime())
        if (!alive) return
        const bars: MinuteBar[] = resp.data
        chart.applyNewData(
          bars.map((b) => ({
            timestamp: b.timestamp,
            open: b.open,
            high: b.high,
            low: b.low,
            close: b.close,
            volume: b.volume,
            turnover: b.turnover
          }))
        )
      } catch {
        if (!alive) return
        chart.applyNewData([])
      }
    }
    load()

    return () => {
      alive = false
      if (containerRef.current) dispose(containerRef.current)
      chartRef.current = null
    }
  }, [symbol, adjust])

  useEffect(() => {
    chartRef.current?.setStyles(theme === 'light' ? lightTimeStyles(preClose ?? null) : darkTimeStyles(preClose ?? null))
  }, [theme, preClose])

  return (
    <section className="chart-panel time-sharing">
      <div className="chart-toolbar-hint">
        <span className="hint-group">
          <span>{symbolCode} {name} · 分时</span>
          {preClose ? <span>昨收 {formatPrice(preClose)}</span> : null}
        </span>
        <span className="hint-group">
          <span>价格面积线 / 成交量</span>
        </span>
      </div>
      <div className="kline-pro-host">
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      </div>
    </section>
  )
}

function darkTimeStyles(_preClose: number | null): DeepPartial<Styles> {
  return {
    grid: {
      horizontal: { color: '#1f2937' },
      vertical: { color: '#1f2937' }
    },
    candle: {
      type: CandleType.Area,
      area: {
        lineSize: 1,
        lineColor: '#e2e8f0',
        value: '#e2e8f0',
        smooth: true,
        backgroundColor: [
          { offset: 0, color: 'rgba(226, 232, 240, 0.28)' },
          { offset: 1, color: 'rgba(226, 232, 240, 0.02)' }
        ]
      },
      bar: {
        upColor: '#ef4444',
        downColor: '#22c55e',
        noChangeColor: '#9ca3af',
        upBorderColor: '#ef4444',
        downBorderColor: '#22c55e',
        noChangeBorderColor: '#9ca3af',
        upWickColor: '#ef4444',
        downWickColor: '#22c55e'
      },
      priceMark: {
        last: { upColor: '#ef4444', downColor: '#22c55e', noChangeColor: '#9ca3af' }
      }
    },
    xAxis: {
      tickText: { color: '#94a3b8' },
      axisLine: { color: '#273244' }
    },
    yAxis: {
      tickText: { color: '#94a3b8' },
      axisLine: { color: '#273244' },
      position: YAxisPosition.Right
    }
  }
}

function lightTimeStyles(_preClose: number | null): DeepPartial<Styles> {
  return {
    grid: {
      horizontal: { color: '#e2e8f0' },
      vertical: { color: '#e2e8f0' }
    },
    candle: {
      type: CandleType.Area,
      area: {
        lineSize: 1,
        lineColor: '#0f172a',
        value: '#0f172a',
        smooth: true,
        backgroundColor: [
          { offset: 0, color: 'rgba(15, 23, 42, 0.2)' },
          { offset: 1, color: 'rgba(15, 23, 42, 0.01)' }
        ]
      },
      bar: {
        upColor: '#dc2626',
        downColor: '#16a34a',
        noChangeColor: '#64748b',
        upBorderColor: '#dc2626',
        downBorderColor: '#16a34a',
        noChangeBorderColor: '#64748b',
        upWickColor: '#dc2626',
        downWickColor: '#16a34a'
      },
      priceMark: {
        last: { upColor: '#dc2626', downColor: '#16a34a', noChangeColor: '#64748b' }
      }
    },
    xAxis: {
      tickText: { color: '#475569' },
      axisLine: { color: '#cbd5e1' }
    },
    yAxis: {
      tickText: { color: '#475569' },
      axisLine: { color: '#cbd5e1' },
      position: YAxisPosition.Right
    }
  }
}
