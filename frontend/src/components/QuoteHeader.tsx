import type { Quote, StockSymbol } from '../types/market'

interface Props {
  symbol: StockSymbol
  quote?: Quote | null
}

function fmt(value?: number | null, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return value.toLocaleString('zh-CN', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

export function QuoteHeader({ symbol, quote }: Props) {
  const change = quote?.change ?? 0
  const trend = change > 0 ? 'up' : change < 0 ? 'down' : 'flat'
  return (
    <section className="quote-header">
      <div>
        <div className="symbol-line">
          <strong>{symbol.code}</strong>
          <span>{quote?.name || symbol.name}</span>
          <small>{symbol.symbol}</small>
        </div>
        <div className={`price-line ${trend}`}>
          <span className="last-price">{fmt(quote?.price)}</span>
          <span>{fmt(quote?.change)}</span>
          <span>{fmt(quote?.change_pct)}%</span>
        </div>
      </div>
      <div className="quote-grid">
        <span>今开 {fmt(quote?.open)}</span>
        <span>最高 {fmt(quote?.high)}</span>
        <span>最低 {fmt(quote?.low)}</span>
        <span>昨收 {fmt(quote?.pre_close)}</span>
        <span>成交量 {fmt(quote?.volume, 0)}</span>
        <span>成交额 {fmt(quote?.turnover, 0)}</span>
      </div>
    </section>
  )
}
