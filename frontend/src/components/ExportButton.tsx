import { useState } from 'react'
import { exportUrl } from '../api/marketApi'
import type { AdjustKey, PeriodKey } from '../types/market'

interface Props {
  symbol: string
  period: PeriodKey
  adjust: AdjustKey
}

export function ExportButton({ symbol, period, adjust }: Props) {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const rangeInvalid = Boolean(startDate && endDate && startDate > endDate)
  const options = { startDate, endDate }

  return (
    <div className="export-panel">
      <div className="export-range">
        <label>
          <span>开始</span>
          <input type="date" value={startDate} max={endDate || undefined} onChange={(event) => setStartDate(event.target.value)} />
        </label>
        <label>
          <span>结束</span>
          <input type="date" value={endDate} min={startDate || undefined} onChange={(event) => setEndDate(event.target.value)} />
        </label>
      </div>
      <div className="export-buttons">
        <ExportLink disabled={rangeInvalid} href={exportUrl(symbol, period, adjust, 'csv', { ...options, profile: 'raw' })}>
          原始 CSV
        </ExportLink>
        <ExportLink disabled={rangeInvalid} href={exportUrl(symbol, period, adjust, 'csv', { ...options, profile: 'ai' })}>
          AI CSV
        </ExportLink>
        <ExportLink disabled={rangeInvalid} href={exportUrl(symbol, period, adjust, 'parquet', { ...options, profile: 'raw' })}>
          Parquet
        </ExportLink>
      </div>
    </div>
  )
}

function ExportLink({ disabled, href, children }: { disabled: boolean; href: string; children: string }) {
  return (
    <a
      aria-disabled={disabled}
      className={disabled ? 'disabled' : undefined}
      href={disabled ? undefined : href}
      onClick={(event) => {
        if (disabled) event.preventDefault()
      }}
    >
      {children}
    </a>
  )
}
