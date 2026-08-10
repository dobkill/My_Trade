import { useEffect, useState } from 'react'
import { getOrderBook } from '../api/marketApi'
import { formatPrice, formatVolume } from '../utils/format'
import type { OrderBook } from '../types/market'

interface Props {
  symbol: string
  lastPrice?: number | null
}

const REFRESH_MS = 2000

/**
 * 五档买卖盘面板：每 2 秒拉取一次，叠加在图表右上角。
 * 接口不可用时优雅隐藏，不阻塞看盘。
 */
export function OrderBookPanel({ symbol, lastPrice }: Props) {
  const [book, setBook] = useState<OrderBook | null>(null)
  const [available, setAvailable] = useState(true)

  useEffect(() => {
    let alive = true
    let timer: number | undefined

    const tick = async () => {
      try {
        const data = await getOrderBook(symbol)
        if (!alive) return
        setBook(data)
        setAvailable(true)
      } catch {
        if (!alive) return
        setAvailable(false)
      } finally {
        if (alive) timer = window.setTimeout(tick, REFRESH_MS)
      }
    }
    tick()

    return () => {
      alive = false
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [symbol])

  if (!available || !book) return null

  const asks = [...(book.asks ?? [])].slice(0, 5).reverse()
  const bids = [...(book.bids ?? [])].slice(0, 5)

  return (
    <div className="order-book">
      <div className="book-title">五档盘口</div>
      {asks.map((level, idx) => (
        <div className="book-row ask" key={`ask-${idx}`}>
          <span className="label">卖{asks.length - idx}</span>
          <span className="price">{formatPrice(level.price)}</span>
          <span>{formatVolume(level.volume)}</span>
        </div>
      ))}
      <div className="book-last">
        <span className="label">最新</span>
        <span className={lastPrice && (lastPrice ?? 0) > 0 ? 'trend-up' : 'trend-flat'}>
          {formatPrice(lastPrice ?? book.asks?.[0]?.price)}
        </span>
      </div>
      {bids.map((level, idx) => (
        <div className="book-row bid" key={`bid-${idx}`}>
          <span className="label">买{idx + 1}</span>
          <span className="price">{formatPrice(level.price)}</span>
          <span>{formatVolume(level.volume)}</span>
        </div>
      ))}
    </div>
  )
}
