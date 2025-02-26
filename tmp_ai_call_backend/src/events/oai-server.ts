import {
  BaseOpenAIEvent,
  RealtimeItem,
  RTVoice,
  Session,
  RTFormat,
  MessageContent,
} from './oai-common'

// Server event types
export const ServerEventTypes = {
  ERROR: 'error',
  SESSION_CREATED: 'session.created',
  SESSION_UPDATED: 'session.updated',
  CONVERSATION_CREATED: 'conversation.created',
  CONVERSATION_ITEM_CREATED: 'conversation.item.created',
  CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
    'conversation.item.input_audio_transcription.completed',
  CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED:
    'conversation.item.input_audio_transcription.failed',
  CONVERSATION_ITEM_TRUNCATED: 'conversation.item.truncated',
  CONVERSATION_ITEM_DELETED: 'conversation.item.deleted',
  INPUT_AUDIO_BUFFER_COMMITTED: 'input_audio_buffer.committed',
  INPUT_AUDIO_BUFFER_CLEARED: 'input_audio_buffer.cleared',
  INPUT_AUDIO_BUFFER_SPEECH_STARTED: 'input_audio_buffer.speech_started',
  INPUT_AUDIO_BUFFER_SPEECH_STOPPED: 'input_audio_buffer.speech_stopped',
  RESPONSE_CREATED: 'response.created',
  RESPONSE_DONE: 'response.done',
  RESPONSE_OUTPUT_ITEM_ADDED: 'response.output_item.added',
  RESPONSE_OUTPUT_ITEM_DONE: 'response.output_item.done',
  RESPONSE_CONTENT_PART_ADDED: 'response.content_part.added',
  RESPONSE_CONTENT_PART_DONE: 'response.content_part.done',
  RESPONSE_TEXT_DELTA: 'response.text.delta',
  RESPONSE_TEXT_DONE: 'response.text.done',
  RESPONSE_AUDIO_TRANSCRIPT_DELTA: 'response.audio_transcript.delta',
  RESPONSE_AUDIO_TRANSCRIPT_DONE: 'response.audio_transcript.done',
  RESPONSE_AUDIO_DELTA: 'response.audio.delta',
  RESPONSE_AUDIO_DONE: 'response.audio.done',
  RESPONSE_FUNCTION_CALL_ARGUMENTS_DELTA: 'response.function_call_arguments.delta',
  RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE: 'response.function_call_arguments.done',
  RATE_LIMITS_UPDATED: 'rate_limits.updated',
} as const

// Server event type utilities
export type ServerEventType = (typeof ServerEventTypes)[keyof typeof ServerEventTypes]

export interface ErrorEvent extends BaseOpenAIEvent {
  type: 'error'
  error: {
    type: string
    code: string | null
    message: string
    param: string | null
    event_id: string | null
  }
}

export interface SessionCreatedEvent extends BaseOpenAIEvent {
  type: 'session.created'
  session: Session
}

export interface SessionUpdatedEvent extends BaseOpenAIEvent {
  type: 'session.updated'
  session: Session
}

export interface ConversationCreatedEvent extends BaseOpenAIEvent {
  type: 'conversation.created'
  conversation: {
    id: string
    object: 'realtime.conversation'
  }
}

export interface ConversationItemCreatedEvent extends BaseOpenAIEvent {
  type: 'conversation.item.created'
  previous_item_id: string
  item: RealtimeItem
}

export interface ConversationItemInputAudioTranscriptionCompletedEvent extends BaseOpenAIEvent {
  type: 'conversation.item.input_audio_transcription.completed'
  item_id: string
  content_index: number
  transcript: string
}

export interface ConversationItemInputAudioTranscriptionFailedEvent extends BaseOpenAIEvent {
  type: 'conversation.item.input_audio_transcription.failed'
  item_id: string
  content_index: number
  error: {
    type: string
    code: string
    message: string
    param: string
  }
}

export interface ConversationItemTruncatedEvent extends BaseOpenAIEvent {
  type: 'conversation.item.truncated'
  item_id: string
  content_index: number
  audio_end_ms: number
}

export interface ConversationItemDeletedEvent extends BaseOpenAIEvent {
  type: 'conversation.item.deleted'
  item_id: string
}

export interface InputAudioBufferCommittedEvent extends BaseOpenAIEvent {
  type: 'input_audio_buffer.committed'
  previous_item_id: string
  item_id: string
}

export interface InputAudioBufferClearedEvent extends BaseOpenAIEvent {
  type: 'input_audio_buffer.cleared'
}

export interface InputAudioBufferSpeechStartedEvent extends BaseOpenAIEvent {
  type: 'input_audio_buffer.speech_started'
  audio_start_ms: number
  item_id: number
}

export interface InputAudioBufferSpeechStoppedEvent extends BaseOpenAIEvent {
  type: 'input_audio_buffer.speech_stopped'
  audio_end_ms: number
  item_id: number
}

export interface Response {
  id: string
  object: 'realtime.response'
  status: 'incomplete' | 'completed' | 'failed' | 'cancelled'
  status_details: {
    type: 'incomplete' | 'completed' | 'failed' | 'cancelled'
    reason:
      | 'turn_detected'
      | 'client_cancelled' // for "cancelled"
      | 'max_output_tokenx'
      | 'content_filter' // for "incomplete"
    error: {
      type: string
      code: string
    }
  }
  output: RealtimeItem[]
  metadata: Record<string, string>
  usage: {
    total_tokens: number
    input_tokens: number
    output_tokens: number
    input_token_details: {
      cached_tokens: number
      text_tokens: number
      audio_tokens: number
    }
    output_token_details: {
      text_tokens: number
      audio_tokens: number
    }
  }
  conversation_id: string | null
  voice: RTVoice
  modalities: ('text' | 'audio')[]
  output_audio_format: RTFormat
  temperature: number
  max_output_tokens: number | 'inf'
}

export interface ResponseCreatedEvent extends BaseOpenAIEvent {
  type: 'response.created'
  response: Response
}

export interface ResponseDoneEvent extends BaseOpenAIEvent {
  type: 'response.done'
  response: Response
}

export interface ResponseOutputItemAddedEvent extends BaseOpenAIEvent {
  type: 'response.output_item.added'
  response_id: string
  output_index: number
  item: RealtimeItem
}

export interface ResponseOutputItemDoneEvent extends BaseOpenAIEvent {
  type: 'response.output_item.done'
  response_id: string
  output_index: number
  item: RealtimeItem
}

export interface ContentEvent extends BaseOpenAIEvent {
  response_id: string
  item_id: string
  output_index: number
  content_index: number
}

export interface ResponseContentPartAddedEvent extends ContentEvent {
  type: 'response.content_part.added'
  part: MessageContent
}

export interface ResponseContentPartDoneEvent extends ContentEvent {
  type: 'response.content_part.done'
  part: MessageContent
}

export interface ResponseTextDeltaEvent extends ContentEvent {
  type: 'response.text.delta'
  delta: string
}

export interface ResponseTextDoneEvent extends ContentEvent {
  type: 'response.text.done'
  text: string
}

export interface ResponseAudioTranscriptDeltaEvent extends ContentEvent {
  type: 'response.audio_transcript.delta'
  delta: string
}

export interface ResponseAudioTranscriptDoneEvent extends ContentEvent {
  type: 'response.audio_transcript.done'
  transcript: string
}

export interface ResponseAudioDeltaEvent extends ContentEvent {
  type: 'response.audio.delta'
  delta: string
}

export interface ResponseAudioDoneEvent extends ContentEvent {
  type: 'response.audio.done'
}

export interface ResponseFunctionCallArgumentsDeltaEvent extends ContentEvent {
  type: 'response.function_call_arguments.delta'
  delta: string
}

export interface ResponseFunctionCallArgumentsDoneEvent extends ContentEvent {
  type: 'response.function_call_arguments.done'
  arguments: string
}

export interface RateLimitsUpdatedEvent extends BaseOpenAIEvent {
  type: 'rate_limits.updated'
  rate_limits: Array<{
    name: 'requests' | 'tokens'
    limit: number
    remaining: number
    reset_seconds: number
  }>
}
