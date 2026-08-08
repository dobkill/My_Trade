import { useEffect, useState, useTransition } from 'react'
import { searchSymbols } from '../api/marketApi'
import type { StockSymbol } from '../types/market'

interface Props {
  onSelect: (symbol: StockSymbol) => void
  onAdd: (symbol: StockSymbol) => void
  isWatched: (symbol: string) => boolean
}

export function StockSearch({ onSelect, onAdd, isWatched }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StockSymbol[]>([])
  const [isPending, startTransition] = useTransition()
  const [error, setError] = useState('')

  useEffect(() => {
    const keyword = query.trim()
    if (!keyword) {
      setResults([])
      setError('')
      return
    }
    const timer = window.setTimeout(() => {
      startTransition(async () => {
        try {
          setResults(await searchSymbols(keyword))
          setError('')
        } catch (err) {
          setError(err instanceof Error ? err.message : '搜索失败')
        }
      })
    }, 220)
    return () => window.clearTimeout(timer)
  }, [query])

  return (
    <div className="stock-search">
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="搜索代码 / 名称，例如 600519 或 贵州茅台"
      />
      {isPending ? <span className="search-loading">搜索中</span> : null}
      {(results.length > 0 || error) && (
        <div className="search-results">
          {error ? <div className="search-error">{error}</div> : null}
          {results.map((item) => {
            const watched = isWatched(item.symbol)
            return (
              <div key={item.symbol} className="search-result-row">
                <button
                  className="search-result-main"
                  type="button"
                  onClick={() => {
                    onSelect(item)
                    setQuery('')
                    setResults([])
                  }}
                >
                  <strong>{item.code}</strong>
                  <span>{item.name}</span>
                  <small>{item.market}</small>
                </button>
                <button
                  className="search-result-add"
                  type="button"
                  title={watched ? '已在自选' : '加入自选'}
                  disabled={watched}
                  onClick={() => {
                    onAdd(item)
                    onSelect(item)
                    setQuery('')
                    setResults([])
                  }}
                >
                  {watched ? '已' : '+'}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
