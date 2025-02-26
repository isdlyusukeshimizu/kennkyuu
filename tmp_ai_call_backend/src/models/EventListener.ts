import { CallSession } from './CallSession'

export interface EventListener {
  eventType: string
  callback: (message: Record<string, unknown>, session: CallSession) => void
}
