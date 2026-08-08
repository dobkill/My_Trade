import type { HealthResponse, RealtimeStatus } from '../types/market'

interface Props {
  health?: HealthResponse | null
  realtime: RealtimeStatus
}

const statusText: Record<RealtimeStatus['state'], string> = {
  realtime: '实时',
  delayed: '延迟',
  closed: '市场休市',
  reconnecting: '重连中'
}

export function ConnectionStatus({ health, realtime }: Props) {
  const provider = realtime.provider || health?.active_provider || '检测中'
  return (
    <div className="connection-status">
      <span>行情源：{provider.toUpperCase()}</span>
      <span className={`dot ${realtime.state}`} />
      <span>{statusText[realtime.state]}</span>
    </div>
  )
}
