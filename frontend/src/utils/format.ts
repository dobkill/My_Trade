/** 将成交量/成交额格式化为带单位的可读字符串（A股：手 / 万 / 亿）。 */
export function formatVolume(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  if (value < 1000) return value.toFixed(0)
  if (value < 10000) return `${(value / 1000).toFixed(2)}千`
  if (value < 1_0000_0000) return `${(value / 10000).toFixed(2)}万`
  return `${(value / 1_0000_0000).toFixed(2)}亿`
}

/** 成交额专用，单位元 -> 万/亿。 */
export function formatAmount(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  if (value < 10000) return value.toFixed(0)
  if (value < 1_0000_0000) return `${(value / 10000).toFixed(2)}万`
  return `${(value / 1_0000_0000).toFixed(2)}亿`
}

/** 价格保留两位小数。 */
export function formatPrice(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
}

/** 涨跌幅带百分号，正数加 +。 */
export function formatChangePct(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}
