import { useEffect, useState, useTransition } from 'react'
import { searchSymbols } from '../api/marketApi'
import type { StockSymbol } from '../types/market'

interface Props {
  onSelect: (symbol: StockSymbol) => void
}

export function StockSearch({ onSelect }: Props) {
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
          {results.map((item) => (
            <button
              key={item.symbol}
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
          ))}
        </div>
      )}
    </div>
  )
}
