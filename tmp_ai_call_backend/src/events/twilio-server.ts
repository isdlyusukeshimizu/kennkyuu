// Server-specific event types
export const TwilioServerEventTypes = {
  CONNECTED: 'connected',
  START: 'start',
  MEDIA: 'media',
  STOP: 'stop',
  DTMF: 'dtmf',
  MARK: 'mark'
} as const

// Server event type utilities
export type TwilioServerEventType =
  (typeof TwilioServerEventTypes)[keyof typeof TwilioServerEventTypes]

// Fixed 8kHz mono µ-law format required for all audio
type MediaFormat = {
  encoding: "audio/x-mulaw"
  sampleRate: 8000
  channels: 1
}

// Initial WebSocket event that verifies protocol compatibility before any streaming can begin
export interface TwilioConnectedEvent {
  event: "connected"
  protocol: string
  version: string
}

// After connection, configures stream with audio format and track settings for the call session
export interface TwilioStartEvent {
  event: "start"
  sequenceNumber: string
  start: {
    streamSid: string
    accountSid: string
    callSid: string
    tracks: ("inbound" | "outbound")[]
    customParameters?: Record<string, string>
    mediaFormat: MediaFormat
  }
  streamSid?: string
}

// Delivers timestamped audio chunks in sequence, carrying base64-encoded µ-law audio for inbound/outbound tracks
export interface TwilioMediaEvent {
  event: "media"
  sequenceNumber: string
  media: {
    track: "inbound" | "outbound"
    chunk: string
    timestamp: string
    payload: string
  }
  streamSid?: string
}

// Final event in stream lifecycle, contains identifiers needed for logging
export interface TwilioStopEvent {
  event: "stop"
  sequenceNumber: string
  stop: {
    accountSid: string
    callSid: string
  }
  streamSid?: string
}

// Phone keypad events from caller, track is always inbound_track regardless of stream config
export interface TwilioDTMFEvent {
  event: "dtmf"
  sequenceNumber: string
  dtmf: {
    track: "inbound_track"
    digit: string
  }
  streamSid?: string
}

// Notifies when a named marker is reached in the stream, enabling precise audio-to-event synchronization
export interface TwilioMarkEvent {
  event: "mark"
  sequenceNumber: string
  mark: {
    name: string
  }
  streamSid?: string
}
