import { EventListener } from './EventListener'
import { CallSession } from './CallSession'

export class EventPublisher {
  private listeners: Map<string, EventListener[]> = new Map()

  subscribe(listener: EventListener): void {
    const listeners = this.listeners.get(listener.eventType) || []
    listeners.push(listener)
    this.listeners.set(listener.eventType, listeners)
  }

  // Publish an event to all registered listeners
  publish(eventType: string, message: Record<string, unknown>, session: CallSession): void {
    // Find all listeners that match the event type (prefix match)
    Array.from(this.listeners.entries()).forEach(([registeredType, listeners]) => {
      if (!eventType.startsWith(registeredType)) return

      // Call each listener's callback
      listeners.forEach((listener) => {
        try {
          listener.callback(message, session)
        } catch (error) {
          console.error(`Error in listener callback: ${error}`)
        }
      })
    })
  }
}
