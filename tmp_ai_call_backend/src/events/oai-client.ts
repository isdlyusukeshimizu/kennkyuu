import { BaseOpenAIEvent, RealtimeItem, Session, FunctionCall, RTVoice } from './oai-common'

// Client-specific event types
export const ClientEventTypes = {
  SESSION_UPDATE: 'session.update',
  INPUT_AUDIO_BUFFER_APPEND: 'input_audio_buffer.append',
  INPUT_AUDIO_BUFFER_COMMIT: 'input_audio_buffer.commit',
  INPUT_AUDIO_BUFFER_CLEAR: 'input_audio_buffer.clear',
  CONVERSATION_ITEM_CREATE: 'conversation.item.create',
  CONVERSATION_ITEM_TRUNCATE: 'conversation.item.truncate',
  CONVERSATION_ITEM_DELETE: 'conversation.item.delete',
  RESPONSE_CREATE: 'response.create',
  RESPONSE_CANCEL: 'response.cancel',
} as const

// Client event type utilities
export type ClientEventType = (typeof ClientEventTypes)[keyof typeof ClientEventTypes]

// Client event interfaces
export interface SessionUpdateEvent extends BaseOpenAIEvent {
  type: 'session.update'
  session: Session
}

export interface InputAudioBufferAppendEvent extends BaseOpenAIEvent {
  type: 'input_audio_buffer.append'
  audio: string
}

export interface InputAudioBufferCommitEvent extends BaseOpenAIEvent {
  type: 'input_audio_buffer.commit'
}

export interface InputAudioBufferClearEvent extends BaseOpenAIEvent {
  type: 'input_audio_buffer.clear'
}

export interface ConversationItemCreateEvent extends BaseOpenAIEvent {
  type: 'conversation.item.create'

  /**
   * If not set, the new item will be appended to the end of the conversation.
   * If set to root, the new item will be added to the beginning of the conversation.
   */
  previous_item_id?: string
  item: RealtimeItem
}

export interface ConversationItemTruncateEvent extends BaseOpenAIEvent {
  type: 'conversation.item.truncate'
  item_id: string
  content_index: 0
  audio_end_ms: number
}

export interface ConversationItemDeleteEvent extends BaseOpenAIEvent {
  type: 'conversation.item.delete'
  item_id: string
}

export interface ResponseCreateEvent extends BaseOpenAIEvent {
  type: 'response.create'
  response?: {
    modalities?: ('text' | 'audio')[]
    instructions?: string
    voice?: RTVoice
    output_audio_format?: 'pcm16' | 'g711_ulaw' | 'g711_alaw'
    tools?: FunctionCall[]
    tool_choice?: 'auto' | 'none' | 'required'
    temperature?: number
    max_response_output_tokens?: number | 'inf'
    /**
     * 'none' to not add response to the conversation
     */
    conversation: 'auto' | 'none'
    metadata?: Record<string, string>
    /**
     * Specify the context for creating the response.
     * `[]` for no context, not including this will use the full conversation.
     */
    input?: RealtimeItem[]
  }
}

export interface ResponseCancelEvent extends BaseOpenAIEvent {
  type: 'response.cancel'
  response_id?: string
}
