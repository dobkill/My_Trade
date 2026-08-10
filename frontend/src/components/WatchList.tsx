import type { Quote, StockSymbol } from '../types/market'

interface Props {
  items: StockSymbol[]
  quotes?: Record<string, Quote>
  active: string
  onSelect: (symbol: StockSymbol) => void
  onRemove: (symbol: string) => void
}

type QuoteMap = Record<string, Quote>

function fmtPrice(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
}

function fmtPct(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function trendOf(quote?: Quote): 'up' | 'down' | 'flat' {
  const change = quote?.change ?? 0
  if (change > 0) return 'up'
  if (change < 0) return 'down'
  return 'flat'
}

export function WatchList({ items, quotes = {}, active, onSelect, onRemove }: Props) {
  const quoteMap: QuoteMap = quotes
  return (
    <aside className="watch-list">
      <div className="panel-title">自选股</div>
      <div className="watch-head">
        <span>名称代码</span>
        <span>现价</span>
        <span>涨跌%</span>
      </div>
      <div className="watch-items">
        {items.map((item) => {
          const quote = quoteMap[item.symbol]
          const trend = trendOf(quote)
          const trendClass = `trend-${trend}`
          return (
            <div key={item.symbol} className={`watch-item ${active === item.symbol ? 'active' : ''}`}>
              <button type="button" className="main" onClick={() => onSelect(item)}>
                <span className="watch-meta">
                  <span className="code">{item.code}</span>
                  <span className="name">{item.name}</span>
                </span>
                <span className={`watch-price ${trendClass}`}>{quote ? fmtPrice(quote.price) : '--'}</span>
                <span className={`watch-change ${trendClass}`}>{fmtPct(quote?.change_pct)}</span>
              </button>
              <button type="button" className="remove" title="删除自选" onClick={() => onRemove(item.symbol)}>
                ×
              </button>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
