import { CallSession } from '../models/CallSession'
import { EventPublisher } from '../models/EventPublisher'
import * as WebSocket from 'ws'
import { EventListener } from '../models/EventListener'

export class AudioForwardingController {
  forwardAudioToTwilio: EventListener = {
    eventType: 'response.audio.delta',
    callback: function (message: Record<string, unknown>, session: CallSession): void {
      if (!message.delta) return
      const audioDelta = {
        event: 'media',
        streamSid: session.streamSid,
        media: { payload: message.delta },
      }
      session.sendToTwilio(audioDelta)
    },
  }

  forwardAudioToOpenAI: EventListener = {
    eventType: 'media',
    callback: function (message: Record<string, unknown>, session: CallSession): void {
      if (session.openAiWs.readyState !== WebSocket.WebSocket.OPEN) return
      const media = message.media as Record<string, unknown>
      const audioAppend = {
        type: 'input_audio_buffer.append',
        audio: media.payload,
      }
      session.sendToOpenAi(audioAppend)
    },
  }

  // Register all event listeners
  registerListeners(eventPublisher: EventPublisher): void {
    eventPublisher.subscribe(this.forwardAudioToTwilio)
    eventPublisher.subscribe(this.forwardAudioToOpenAI)
  }
}
