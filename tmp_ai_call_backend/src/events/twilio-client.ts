// Client-specific event types
export const TwilioClientEventTypes = {
  MEDIA: 'media',
  MARK: 'mark',
  CLEAR: 'clear',
} as const

// Client event type utilities
export type TwilioClientEventType =
  (typeof TwilioClientEventTypes)[keyof typeof TwilioClientEventTypes]

// Sends base64 µ-law audio to Twilio, must match 8kHz mono format
export interface TwilioClientMediaEvent {
  event: "media"
  media: {
    payload: string
  }
  streamSid?: string
}

// Places a named marker in the stream that will trigger a server mark event when that position is reached
export interface TwilioClientMarkEvent {
  event: "mark"
  mark: {
    name: string
  }
  streamSid?: string
}

// Immediately clears buffered audio data to reduce latency or prepare for stream changes
export interface TwilioClientClearEvent {
  event: "clear"
  streamSid?: string
}
