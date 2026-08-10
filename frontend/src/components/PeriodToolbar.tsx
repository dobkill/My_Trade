import type { AdjustKey, PeriodKey } from '../types/market'

interface Props {
  period: PeriodKey | 'time'
  adjust: AdjustKey
  onPeriod: (period: PeriodKey | 'time') => void
  onAdjust: (adjust: AdjustKey) => void
}

const periods: Array<{ key: PeriodKey | 'time'; label: string }> = [
  { key: 'time', label: '分时' },
  { key: '1m', label: '1m' },
  { key: '5m', label: '5m' },
  { key: '15m', label: '15m' },
  { key: '30m', label: '30m' },
  { key: '60m', label: '60m' },
  { key: '1d', label: '日' },
  { key: '1w', label: '周' },
  { key: '1M', label: '月' }
]

export function PeriodToolbar({ period, adjust, onPeriod, onAdjust }: Props) {
  return (
    <div className="period-toolbar">
      <div className="period-buttons">
        {periods.map((item) => (
          <button key={item.key} className={period === item.key ? 'active' : ''} type="button" onClick={() => onPeriod(item.key)}>
            {item.label}
          </button>
        ))}
      </div>
      <select value={adjust} onChange={(event) => onAdjust(event.target.value as AdjustKey)}>
        <option value="none">不复权</option>
        <option value="qfq">前复权</option>
        <option value="hfq">后复权</option>
      </select>
    </div>
  )
}
