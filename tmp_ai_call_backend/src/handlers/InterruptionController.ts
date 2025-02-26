import { CallSession } from '../models/CallSession'
import { EventPublisher } from '../models/EventPublisher'
import { EventListener } from '../models/EventListener'

const SHOW_TIMING_MATH = false

export class InterruptionController {
  private latestMediaTimestamp: number = 0
  private lastAssistantItem: string | null = null
  private markQueue: string[] = []
  private responseStartTimestampTwilio: number | null = null

  // Interrupt the AI response when the caller's speech is detected.
  interruptResponseOnCallerSpeech: EventListener = {
    eventType: 'input_audio_buffer.speech_started',
    callback: (message: Record<string, unknown>, session: CallSession): void => {
      if (this.markQueue.length > 0 && this.responseStartTimestampTwilio != null) {
        const elapsedTime = this.latestMediaTimestamp - this.responseStartTimestampTwilio

        if (SHOW_TIMING_MATH)
          console.log(
            `Calculating elapsed time for truncation: ${this.latestMediaTimestamp} - ${this.responseStartTimestampTwilio} = ${elapsedTime}ms`
          )

        if (this.lastAssistantItem) {
          const truncateEvent = {
            type: 'conversation.item.truncate',
            item_id: this.lastAssistantItem,
            content_index: 0,
            audio_end_ms: elapsedTime,
          }
          if (SHOW_TIMING_MATH)
            console.log('Sending truncation event:', JSON.stringify(truncateEvent))
          session.sendToOpenAi(truncateEvent)
        }

        session.sendToTwilio({
          event: 'clear',
          streamSid: session.streamSid,
        })

        // Reset state.
        this.markQueue = []
        this.lastAssistantItem = null
        this.responseStartTimestampTwilio = null
      }
    },
  }

  // Send a mark event for response chunks.
  sendResponsePartMark: EventListener = {
    eventType: 'response.audio.delta',
    callback: (message: Record<string, unknown>, session: CallSession): void => {
      if (!message.delta) return
      if (session.streamSid) {
        const markEvent = {
          event: 'mark',
          streamSid: session.streamSid,
          mark: { name: 'responsePart' },
        }
        session.sendToTwilio(markEvent)
        this.markQueue.push('responsePart')
      }
    },
  }

  // Capture the timestamp for the start of the response and store the assistant's item ID.
  captureResponseStartAndItemId: EventListener = {
    eventType: 'response.audio.delta',
    callback: (message: Record<string, unknown>, session: CallSession): void => {
      if (!message.delta) return

      if (!this.responseStartTimestampTwilio) {
        this.responseStartTimestampTwilio = this.latestMediaTimestamp
        if (SHOW_TIMING_MATH)
          console.log(
            `Setting start timestamp for new response: ${this.responseStartTimestampTwilio}ms`
          )
      }

      if (message.item_id) {
        this.lastAssistantItem = message.item_id as string
      }
    },
  }

  // Update the latest media timestamp.
  updateLatestMediaTimestamp: EventListener = {
    eventType: 'media',
    callback: (message: Record<string, unknown>, session: CallSession): void => {
      const media = message.media as Record<string, unknown>
      this.latestMediaTimestamp = media.timestamp as number
      if (SHOW_TIMING_MATH)
        console.log(`Received media message with timestamp: ${this.latestMediaTimestamp}ms`)
    },
  }

  // Reset timestamps when a new stream starts.
  resetTimestamps: EventListener = {
    eventType: 'start',
    callback: (message: Record<string, unknown>, session: CallSession): void => {
      this.responseStartTimestampTwilio = null
      this.latestMediaTimestamp = 0
    },
  }

  processMarkQueueOnReceivedMark: EventListener = {
    eventType: 'mark',
    callback: (message: Record<string, unknown>, session: CallSession): void => {
      if (this.markQueue.length > 0) {
        this.markQueue.shift()
      }
    },
  }

  // Register all event listeners
  registerListeners(eventPublisher: EventPublisher): void {
    eventPublisher.subscribe(this.interruptResponseOnCallerSpeech)
    eventPublisher.subscribe(this.sendResponsePartMark)
    eventPublisher.subscribe(this.captureResponseStartAndItemId)
    eventPublisher.subscribe(this.updateLatestMediaTimestamp)
    eventPublisher.subscribe(this.resetTimestamps)
    eventPublisher.subscribe(this.processMarkQueueOnReceivedMark)
  }
}
