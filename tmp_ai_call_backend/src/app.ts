import Fastify, { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify'
import * as WebSocket from 'ws'
import * as dotenv from 'dotenv'
import fastifyFormBody from '@fastify/formbody'
import fastifyWs from '@fastify/websocket'
import { CallSession } from './models'
import { EventPublisher } from './models/EventPublisher'
import { InterruptionController } from './handlers/InterruptionController'
import { AudioForwardingController } from './handlers/AudioForwardingController'

// Load environment variables from .env file
dotenv.config()

// Retrieve the OpenAI API key from environment variables.
const { OPENAI_API_KEY } = process.env

if (!OPENAI_API_KEY) {
  console.error('Missing OpenAI API key. Please set it in the .env file.')
  process.exit(1)
}

// Initialize Fastify
const fastify: FastifyInstance = Fastify()
fastify.register(fastifyFormBody)
fastify.register(fastifyWs)

const PORT = Number(process.env.PORT) || 5050 // Allow dynamic port assignment

// List of Event Types to log to the console. See the OpenAI Realtime API Documentation: https://platform.openai.com/docs/api-reference/realtime
const LOG_EVENT_TYPES = [
  'error',
  'response.content.done',
  'rate_limits.updated',
  'response.done',
  'input_audio_buffer.committed',
  'input_audio_buffer.speech_stopped',
  'input_audio_buffer.speech_started',
  'session.created',
]

// Constants
const SYSTEM_MESSAGE = `You are a helpful and bubbly AI assistant who loves to chat about anything the user is interested about and is prepared to offer them facts. You have a penchant for dad jokes, owl jokes, and rickrolling – subtly. Always stay positive, but work in a joke when appropriate.`
const VOICE = 'alloy'
// Add a constant to control whether the AI speaks first
const AI_SPEAKS_FIRST = false

// Show AI response elapsed timing calculations
function initializeOpenAISession(session: CallSession): void {
  const sessionUpdate = {
    type: 'session.update',
    session: {
      input_audio_format: 'g711_ulaw',
      output_audio_format: 'g711_ulaw',
      voice: VOICE,
      instructions: SYSTEM_MESSAGE,
      temperature: 0.8,
    },
  }

  console.log('Sending OpenAI session update:', JSON.stringify(sessionUpdate))
  session.sendToOpenAi(sessionUpdate)

  if (AI_SPEAKS_FIRST) {
    session.sendToOpenAi({ type: 'response.create' })
  }
}

// Root Route
fastify.get('/', async (request: FastifyRequest, reply: FastifyReply) => {
  reply.send({ message: 'Twilio Media Stream Server is running!' })
})

// Route for Twilio to handle incoming calls
// <Say> punctuation to improve text-to-speech translation
fastify.all('/incoming-call', async (request: FastifyRequest, reply: FastifyReply) => {
  const twimlResponse = `<?xml version="1.0" encoding="UTF-8"?>
  <Response>
    <Connect>
      <Stream url="wss://${request.headers.host}/media-stream" />
    </Connect>
  </Response>`
  reply.type('text/xml').send(twimlResponse)
})

// WebSocket route for media-stream
fastify.register(async (fastify) => {
  fastify.get('/media-stream', { websocket: true }, (twilioWS) => {
    console.log('Client connected')

    const openAiWs = new WebSocket.WebSocket(
      'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
      {
        headers: {
          Authorization: `Bearer ${OPENAI_API_KEY}`,
          'OpenAI-Beta': 'realtime=v1',
        },
      }
    )

    const callSession = new CallSession(openAiWs, twilioWS)
    const eventPublisher = new EventPublisher()

    const audioForwardingHandler = new AudioForwardingController()
    audioForwardingHandler.registerListeners(eventPublisher)

    const interruptionHandler = new InterruptionController()
    interruptionHandler.registerListeners(eventPublisher)

    // Open event for OpenAI WebSocket
    openAiWs.on('open', () => {
      console.log('Connected to the OpenAI Realtime API')
      setTimeout(() => initializeOpenAISession(callSession), 100)
    })

    // Listen for messages from the OpenAI WebSocket.
    openAiWs.on('message', (raw_message: WebSocket.RawData) => {
      try {
        const message = JSON.parse(raw_message.toString())
        const eventType = message.type

        if (LOG_EVENT_TYPES.includes(eventType)) {
          console.log(`Received event: ${eventType}`, message)
        }

        // Publish the event to all registered listeners
        eventPublisher.publish(eventType, message, callSession)
      } catch (error) {
        console.error('Error processing OpenAI message:', error, 'Raw message:', raw_message)
      }
    })

    // Handle incoming messages from Twilio
    twilioWS.on('message', (raw_message: WebSocket.RawData) => {
      try {
        const message = JSON.parse(raw_message.toString())
        const eventType = message.event

        switch (eventType) {
          case 'start':
            callSession.streamSid = message.start.streamSid
            console.log('Incoming stream has started', callSession.streamSid)
            break
          default:
            if (eventType !== 'media' && eventType !== 'mark' && eventType !== 'clear')
              console.log('Received non-media event:', eventType)
            break
        }

        // Publish the event to all registered listeners
        eventPublisher.publish(eventType, message, callSession)
      } catch (error) {
        console.error('Error parsing message:', error, 'Message:', raw_message)
      }
    })

    // Handle connection close
    twilioWS.on('close', () => {
      if (openAiWs.readyState === WebSocket.WebSocket.OPEN) openAiWs.close()
      console.log('Client disconnected.')
    })

    // Handle WebSocket close and errors for OpenAI.
    openAiWs.on('close', () => {
      console.log('Disconnected from the OpenAI Realtime API')
    })

    openAiWs.on('error', (error: Error) => {
      console.error('Error in the OpenAI WebSocket:', error)
    })
  })
})

fastify.listen({ port: PORT }, (err) => {
  if (err) {
    console.error(err)
    process.exit(1)
  }
  console.log(`Server is listening on port ${PORT}`)
})
