import { useEffect, useRef } from 'react'
import { KLineChartPro } from '@klinecharts/pro'
import '@klinecharts/pro/dist/klinecharts-pro.css'
import type { AStockDatafeed } from '../datafeed/AStockDatafeed'
import { periodToPro, proPeriods, toProSymbol } from '../datafeed/AStockDatafeed'
import type { AdjustKey, PeriodKey, StockSymbol } from '../types/market'

interface Props {
  symbol: StockSymbol
  period: PeriodKey
  adjust: AdjustKey
  datafeed: AStockDatafeed
}

type ProInstance = InstanceType<typeof KLineChartPro>

const chartStyles = {
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

export function ChartPanel({ symbol, period, adjust, datafeed }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<ProInstance | null>(null)

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
      theme: 'dark',
      drawingBarVisible: true,
      mainIndicators: ['MA', 'EMA'],
      subIndicators: ['VOL', 'MACD', 'RSI', 'KDJ'],
      styles: chartStyles,
      datafeed
    })
    return () => {
      datafeed.closeAll()
      if (containerRef.current) containerRef.current.innerHTML = ''
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    datafeed.setAdjust(adjust)
    chartRef.current?.setSymbol(toProSymbol(symbol))
  }, [symbol.symbol])

  useEffect(() => {
    datafeed.setAdjust(adjust)
    chartRef.current?.setPeriod(periodToPro(period))
  }, [period, adjust])

  return (
    <section className="chart-panel">
      <div className="chart-toolbar-hint">
        <span>内置画线工具已启用：趋势线、水平线、线段、价格线、斐波那契、平行线/通道</span>
        <span>指标：MA / EMA / VOL / MACD / RSI / KDJ</span>
      </div>
      <div ref={containerRef} className="kline-pro-host" />
    </section>
  )
}
