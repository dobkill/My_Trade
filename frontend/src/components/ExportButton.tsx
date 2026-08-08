import { exportUrl } from '../api/marketApi'
import type { AdjustKey, PeriodKey } from '../types/market'

interface Props {
  symbol: string
  period: PeriodKey
  adjust: AdjustKey
}

export function ExportButton({ symbol, period, adjust }: Props) {
  return (
    <div className="export-buttons">
      <a href={exportUrl(symbol, period, adjust, 'csv')}>导出 CSV</a>
      <a href={exportUrl(symbol, period, adjust, 'parquet')}>导出 Parquet</a>
    </div>
  )
}
