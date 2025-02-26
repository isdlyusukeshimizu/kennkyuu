import * as WebSocket from 'ws'

// Helper function to send JSON stringified data through WebSocket
export const sendJson = (ws: WebSocket.WebSocket, data: object) => {
  ws.send(JSON.stringify(data))
}

// Session class to encapsulate WebSocket connections and streamId.
export class CallSession {
  openAiWs: WebSocket.WebSocket
  twilioWs: WebSocket.WebSocket
  streamSid: string

  constructor(openAiWs: WebSocket.WebSocket, twilioWs: WebSocket.WebSocket, streamSid: string = '') {
    this.openAiWs = openAiWs
    this.twilioWs = twilioWs
    this.streamSid = streamSid
  }

  // Send a message to the OpenAI WebSocket
  sendToOpenAi(data: object): void {
    sendJson(this.openAiWs, data)
  }

  // Send a message to the Twilio WebSocket
  sendToTwilio(data: object): void {
    sendJson(this.twilioWs, data)
  }
}
