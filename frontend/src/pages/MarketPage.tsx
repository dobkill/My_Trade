import { useEffect, useMemo, useState } from 'react'
import { getHealth, getQuote } from '../api/marketApi'
import { AStockDatafeed } from '../datafeed/AStockDatafeed'
import { ChartPanel } from '../components/ChartPanel'
import { ConnectionStatus } from '../components/ConnectionStatus'
import { ExportButton } from '../components/ExportButton'
import { PeriodToolbar } from '../components/PeriodToolbar'
import { QuoteHeader } from '../components/QuoteHeader'
import { StockSearch } from '../components/StockSearch'
import { WatchList } from '../components/WatchList'
import { useWatchList } from '../hooks/useWatchList'
import type { AdjustKey, HealthResponse, PeriodKey, Quote, RealtimeStatus, StockSymbol } from '../types/market'

export function MarketPage() {
  const { watchList, add, remove } = useWatchList()
  const [active, setActive] = useState<StockSymbol>(watchList[0])
  const [period, setPeriod] = useState<PeriodKey>('1d')
  const [adjust, setAdjust] = useState<AdjustKey>('qfq')
  const [quote, setQuote] = useState<Quote | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState('')
  const [realtime, setRealtime] = useState<RealtimeStatus>({ state: 'reconnecting' })
  const datafeed = useMemo(() => new AStockDatafeed(adjust, setRealtime, setQuote), [])

  useEffect(() => {
    getHealth().then(setHealth).catch((err) => setError(err instanceof Error ? err.message : '后端健康检查失败'))
  }, [])

  useEffect(() => {
    let alive = true
    getQuote(active.symbol)
      .then((data) => {
        if (!alive) return
        setQuote(data)
        setRealtime({ state: data.market_status === 'closed' ? 'closed' : 'realtime', provider: data.source })
      })
      .catch((err) => {
        if (!alive) return
        setError(err instanceof Error ? err.message : '行情源暂时不可用，正在重试')
        setRealtime({ state: 'reconnecting' })
      })
    return () => {
      alive = false
    }
  }, [active.symbol])

  const selectSymbol = (symbol: StockSymbol) => {
    setActive(symbol)
    add(symbol)
    setError('')
  }

  return (
    <main className="market-page">
      <header className="top-bar">
        <div className="brand">A-Trade</div>
        <StockSearch onSelect={selectSymbol} />
        <ConnectionStatus health={health} realtime={realtime} />
        <button className="theme-toggle" type="button">深色</button>
      </header>
      <div className="terminal-layout">
        <WatchList items={watchList} active={active.symbol} onSelect={setActive} onRemove={remove} />
        <section className="workspace">
          <QuoteHeader symbol={active} quote={quote} />
          <div className="workspace-actions">
            <PeriodToolbar period={period} adjust={adjust} onPeriod={setPeriod} onAdjust={setAdjust} />
            <ExportButton symbol={active.symbol} period={period} adjust={adjust} />
          </div>
          {error ? <div className="error-banner">{error}</div> : null}
          <ChartPanel symbol={active} period={period} adjust={adjust} datafeed={datafeed} />
        </section>
      </div>
    </main>
  )
}
