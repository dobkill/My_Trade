import { useEffect } from 'react'
import type { StockSymbol } from '../types/market'

interface Options {
  watchList: StockSymbol[]
  active: StockSymbol
  onSelect: (symbol: StockSymbol) => void
  /** 删除当前选中的画线，由 ChartPanel 通过 ref 暴露 */
  onDeleteOverlay?: () => void
}

/**
 * 全局键盘快捷键：
 * - ↑/↓ 或 PageUp/PageDown：在自选股列表中切换
 * - Delete/Backspace：删除当前选中的画线（委托给 ChartPanel）
 *
 * 仅在输入框/搜索框未聚焦时响应，避免与文本输入冲突。
 */
export function useHotkeys({ watchList, active, onSelect, onDeleteOverlay }: Options) {
  useEffect(() => {
    if (watchList.length === 0) return

    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target) {
        const tag = target.tagName
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable) {
          return
        }
      }

      const move = (delta: number) => {
        const currentIndex = watchList.findIndex((item) => item.symbol === active.symbol)
        const nextIndex = (currentIndex + delta + watchList.length) % watchList.length
        const next = watchList[nextIndex]
        if (next) {
          event.preventDefault()
          onSelect(next)
        }
      }

      switch (event.key) {
        case 'ArrowUp':
        case 'PageUp':
          move(-1)
          break
        case 'ArrowDown':
        case 'PageDown':
          move(1)
          break
        case 'Delete':
        case 'Backspace':
          if (onDeleteOverlay) {
            event.preventDefault()
            onDeleteOverlay()
          }
          break
        default:
          break
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [watchList, active.symbol, onSelect, onDeleteOverlay])
}
