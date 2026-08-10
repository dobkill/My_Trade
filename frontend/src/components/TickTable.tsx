import { useEffect, useRef, useState } from 'react'
import { getTicks } from '../api/marketApi'
import { formatPrice, formatVolume } from '../utils/format'
import type { Tick } from '../types/market'

interface Props {
  symbol: string
  preClose?: number | null
}

const REFRESH_MS = 3000
const MAX_ROWS = 200

/**
 * 成交明细（逐笔）滚动表：每 3 秒拉取当日逐笔，倒序显示最新成交。
 * 买卖方向用红/绿着色（A股：买盘红、卖盘绿、中性灰）。
 */
export function TickTable({ symbol, preClose }: Props) {
  const [ticks, setTicks] = useState<Tick[]>([])
  const [available, setAvailable] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const bodyRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let alive = true
    let timer: number | undefined

    const tick = async () => {
      try {
        const resp = await getTicks(symbol)
        if (!alive) return
        setTicks(resp.data.slice(-MAX_ROWS))
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

  useEffect(() => {
    if (!autoScroll || !bodyRef.current) return
    bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [ticks, autoScroll])

  if (!available) {
    return (
      <section className="tick-table">
        <div className="tick-head">
          <span className="tick-title">成交明细</span>
          <span className="tick-muted">逐笔数据暂不可用</span>
        </div>
      </section>
    )
  }

  return (
    <section className="tick-table">
      <div className="tick-head">
        <span className="tick-title">成交明细</span>
        <label className="tick-autoscroll">
          <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
          自动滚动
        </label>
      </div>
      <div className="tick-row tick-header-row">
        <span>时间</span>
        <span>价格</span>
        <span>量(手)</span>
        <span>方向</span>
      </div>
      <div className="tick-body" ref={bodyRef}>
        {ticks.map((t, idx) => {
          const dir = classifyTick(t, preClose)
          return (
            <div className="tick-row" key={`${t.timestamp}-${idx}`}>
              <span>{formatTime(t.timestamp)}</span>
              <span className={dir.className}>{formatPrice(t.price)}</span>
              <span>{formatVolume(t.volume)}</span>
              <span className={dir.className}>{dir.label}</span>
            </div>
          )
        })}
        {ticks.length === 0 ? <div className="tick-empty">暂无成交</div> : null}
      </div>
    </section>
  )
}

function classifyTick(tick: Tick, preClose?: number | null): { label: string; className: string } {
  const raw = (tick.type ?? '').trim()
  if (raw.includes('买') || raw.includes('B') || raw === 'up') return { label: '买', className: 'trend-up' }
  if (raw.includes('卖') || raw.includes('S') || raw === 'down') return { label: '卖', className: 'trend-down' }
  if (preClose && tick.price > preClose) return { label: '↑', className: 'trend-up' }
  if (preClose && tick.price < preClose) return { label: '↓', className: 'trend-down' }
  return { label: '—', className: 'trend-flat' }
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}
