import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getHealth, getQuote } from '../api/marketApi'
import { AStockDatafeed } from '../datafeed/AStockDatafeed'
import { ChartPanel } from '../components/ChartPanel'
import { TimeSharingPanel } from '../components/TimeSharingPanel'
import { TickTable } from '../components/TickTable'
import { ConnectionStatus } from '../components/ConnectionStatus'
import { ExportButton } from '../components/ExportButton'
import { PeriodToolbar } from '../components/PeriodToolbar'
import { QuoteHeader } from '../components/QuoteHeader'
import { StockSearch } from '../components/StockSearch'
import { WatchList } from '../components/WatchList'
import { useHotkeys } from '../hooks/useHotkeys'
import { useTheme } from '../hooks/useTheme'
import { useWatchList } from '../hooks/useWatchList'
import { useWatchQuotes } from '../hooks/useWatchQuotes'
import type { AdjustKey, HealthResponse, PeriodKey, Quote, RealtimeStatus, StockSymbol } from '../types/market'

export function MarketPage() {
  const { theme, toggle: toggleTheme } = useTheme()
  const { watchList, add, remove } = useWatchList()
  const quotes = useWatchQuotes(watchList)
  const [active, setActive] = useState<StockSymbol>(watchList[0])
  const [period, setPeriod] = useState<PeriodKey | 'time'>('1d')
  const [adjust, setAdjust] = useState<AdjustKey>('qfq')
  const [quote, setQuote] = useState<Quote | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState('')
  const [realtime, setRealtime] = useState<RealtimeStatus>({ state: 'reconnecting' })
  const datafeed = useMemo(() => new AStockDatafeed(adjust, setRealtime, setQuote), [])
  const activeInWatchList = watchList.some((item) => item.symbol === active.symbol)

  // 删除画线函数由 ChartPanel 注册，键盘 Delete 时调用
  const deleteOverlayRef = useRef<(() => void) | null>(null)
  const registerDeleteOverlay = useCallback((fn: (() => void) | null) => {
    deleteOverlayRef.current = fn
  }, [])
  const handleDeleteOverlay = useCallback(() => {
    deleteOverlayRef.current?.()
  }, [])

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
    setError('')
  }

  useHotkeys({ watchList, active, onSelect: selectSymbol, onDeleteOverlay: handleDeleteOverlay })

  const addSymbol = (symbol: StockSymbol) => {
    add(symbol)
    setError('')
  }

  const removeSymbol = (symbol: string) => {
    remove(symbol)
    if (symbol === active.symbol) {
      const next = watchList.find((item) => item.symbol !== symbol)
      if (next) setActive(next)
    }
  }

  return (
    <main className="market-page">
      <header className="top-bar">
        <div className="brand">A-Trade</div>
        <StockSearch onSelect={selectSymbol} onAdd={addSymbol} isWatched={(symbol) => watchList.some((item) => item.symbol === symbol)} />
        <ConnectionStatus health={health} realtime={realtime} />
        <button className="theme-toggle" type="button" onClick={toggleTheme} title="切换深色/浅色主题">
          {theme === 'dark' ? '🌙 深色' : '☀️ 浅色'}
        </button>
      </header>
      <div className="terminal-layout">
        <WatchList
          items={watchList}
          quotes={quotes}
          active={active.symbol}
          onSelect={selectSymbol}
          onRemove={removeSymbol}
        />
        <section className="workspace">
          <QuoteHeader symbol={active} quote={quote} />
          <div className="workspace-actions">
            <PeriodToolbar period={period} adjust={adjust} onPeriod={setPeriod} onAdjust={setAdjust} />
            {!activeInWatchList ? (
              <button className="watch-action" type="button" onClick={() => addSymbol(active)}>
                + 加自选
              </button>
            ) : null}
            <ExportButton symbol={active.symbol} period={period === 'time' ? '1d' : period} adjust={adjust} />
          </div>
          {error ? <div className="error-banner">{error}</div> : null}
          {period === 'time' ? (
            <TimeSharingPanel
              symbolCode={active.code}
              symbol={active.symbol}
              name={active.name}
              adjust={adjust}
              theme={theme}
              preClose={quote?.pre_close}
            />
          ) : (
            <ChartPanel
              symbol={active}
              period={period}
              adjust={adjust}
              theme={theme}
              datafeed={datafeed}
              lastPrice={quote?.price}
              registerDeleteOverlay={registerDeleteOverlay}
            />
          )}
          <TickTable symbol={active.symbol} preClose={quote?.pre_close} />
        </section>
      </div>
    </main>
  )
}
