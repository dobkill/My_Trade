import type { StockSymbol } from '../types/market'

interface Props {
  items: StockSymbol[]
  active: string
  onSelect: (symbol: StockSymbol) => void
  onRemove: (symbol: string) => void
}

export function WatchList({ items, active, onSelect, onRemove }: Props) {
  return (
    <aside className="watch-list">
      <div className="panel-title">自选股</div>
      <div className="watch-items">
        {items.map((item) => (
          <div key={item.symbol} className={`watch-item ${active === item.symbol ? 'active' : ''}`}>
            <button type="button" onClick={() => onSelect(item)}>
              <span>{item.code}</span>
              <small>{item.name}</small>
            </button>
            <button type="button" className="remove" title="删除自选" onClick={() => onRemove(item.symbol)}>
              -
            </button>
          </div>
        ))}
      </div>
    </aside>
  )
}
