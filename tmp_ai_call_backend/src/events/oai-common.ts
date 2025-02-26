// Type definitions for OpenAI realtime endpoint events - Common Types

import { ClientEventTypes } from './oai-client'
import { ServerEventTypes } from './oai-server'

// Create a union of allowed event type literals
export type OpenAIEventTypes =
  | (typeof ClientEventTypes)[keyof typeof ClientEventTypes]
  | (typeof ServerEventTypes)[keyof typeof ServerEventTypes]

// Base event interface for all OpenAI events
export interface BaseOpenAIEvent {
  type: OpenAIEventTypes
  event_id?: string
}

/**
 * `input_` means from user or dev. Otherwise it's from the AI
 */
export type MessageContent =
  | {
      type: 'text' | 'input_text'
      text: string
    }
  | {
      type: 'audio' | 'input_audio'
      audio: string
      transcript?: string
    }
  | {
      type: 'item_reference' // for response.create
      id: string
    }

export interface BaseRealtimeItem {
  object: 'realtime.item'
  // useless but allowed so item from conversation.item.created could be used
  status?: 'completed' | 'incomplete'
}

export interface MessageItem extends BaseRealtimeItem {
  id?: string
  type: 'message'
  role: 'user' | 'assistant' | 'system'
  content?: MessageContent[]
}

export interface FunctionCallItem extends BaseRealtimeItem {
  id?: string
  type: 'function_call'
  call_id: string
  name: string
  arguments: string
}

export interface FunctionCallOutputItem extends BaseRealtimeItem {
  id?: string
  type: 'function_call_output'
  call_id?: string
  output: string
}

export interface ItemReference extends BaseRealtimeItem {
  id: string // id of an existing item
  type: 'item_reference'
}

export type RealtimeItem = MessageItem | FunctionCallItem | FunctionCallOutputItem | ItemReference

// Function call interface
export interface FunctionCall {
  type: 'function'
  name: string
  description: string
  parameters: {
    type: 'object'
    properties: Record<string, unknown>
    required?: string[]
  }
}

export enum RTVoice {
  ALLOY = 'alloy',
  ASH = 'ash',
  BALLAD = 'ballad',
  CORAL = 'coral',
  ECHO = 'echo',
  SAGE = 'sage',
  SHIMMER = 'shimmer',
  VERSE = 'verse',
}

export enum RTFormat {
  PCM16 = 'pcm16',
  G711_ULAW = 'g711_ulaw',
  G711_ALAW = 'g711_alaw',
}

export interface Session {
  id?: string
  object?: 'realtime.session'
  model?: string
  modalities?: ('text' | 'audio')[]
  instructions?: string
  voice?: RTVoice
  input_audio_format?: RTFormat
  output_audio_format?: RTFormat
  input_audio_transcription?: {
    model: string
  } | null
  turn_detection?: {
    type: 'server_vad'
    threshold: number
    prefix_padding_ms: number
    silence_duration_ms: number
    create_response: boolean
  } | null
  tools?: FunctionCall[]
  tool_choice?: 'auto' | 'none' | 'required'
  temperature?: number
  max_response_output_tokens?: number | 'inf'
  status?: 'in_progress' | 'completed' | 'expired' | 'error'
  timestamp?: number
  expires_at?: number
  client?: {
    os: string
    browser: string
    device: string
    type: string
  }
}
