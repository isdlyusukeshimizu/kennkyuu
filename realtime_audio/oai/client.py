import asyncio
import datetime
import json
import traceback
from collections import defaultdict
from enum import Enum

import websockets
import websockets.protocol
from oai.echo_server import echo_server
from oai.listeners import EventListener

from ut.aoai import openai_key
from ut.aoai import rta_key as aoai_key


class VoiceOption(str, Enum):
  ALLOY = "alloy"  # male, normal
  ASH = "ash"  # male, low voice
  BALLAD = "ballad"  # male, bright
  CORAL = "coral"  # female, normal
  ECHO = "echo"  # male, very clean voice
  SAGE = "sage"  # female, a bit high pitched
  SHIMMER = "shimmer"  # kinda gender neutral, mellow
  VERSE = "verse"  # male, bright


voice = VoiceOption.SAGE


class WebSocketClient:
  class EventDirection(Enum):
    SENT = 0
    RECEIVED = 1

  def __init__(self):  # logger = print
    # self.logger = logger
    self.send_queue = asyncio.Queue()
    self.ws = None
    asyncio.create_task(self._send_loop())
    asyncio.create_task(self._recv_loop())
    self.listeners = defaultdict(list)

  # ============ Events
  def subscribe(self, listener: EventListener, **kwargs):
    self.listeners[listener.event_type].append(lambda message: listener.callback(message, **kwargs))

  async def publish(self, message, direction: EventDirection):
    message = json.loads(message)
    message_event = message["type"]

    # attach metadata
    message["direction"] = str(direction)
    message["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for registered_event, callbacks in self.listeners.items():
      if not message_event.startswith(registered_event):
        continue

      for callback in callbacks:
        try:
          callback(message)
        except Exception as e:
          print(f"Error: {e}, message: ")
          print(json.dumps(message, indent=2))
          traceback.print_exc()

  # ============ Connection
  async def connect(self, uri: str, **kwargs):
    self.ws = await websockets.connect(uri, additional_headers={**kwargs})

  def connected(self):
    return self.ws and not self.ws.protocol.state == websockets.protocol.State.CLOSED

  async def disconnect(self):
    await self.ws.close()
    # self.logger("WebSocketClient: Disconnected")

  # ============ Messages
  async def enqueue(self, message: dict):
    "enqueues a message to be sent"
    # self.logger(f"WebSocketClient: Enqueuing {message}")
    await self.send_queue.put(json.dumps(message))

  async def _send_loop(self):
    while True:
      try:
        # do not crash or block if not connected
        if not self.connected():
          await asyncio.sleep(0.1)
          continue

        message = await self.send_queue.get()
        # self.logger(f"WebSocketClient: Sending {message}")
        await self.ws.send(message)
        self.send_queue.task_done()

        await self.publish(message, WebSocketClient.EventDirection.SENT)
      except Exception:
        # self.logger(f"WebSocketClient: Error: {e} while sending message {message}")
        await asyncio.sleep(0.1)

  async def _recv_loop(self):
    while True:
      try:
        if not self.connected():
          await asyncio.sleep(0.1)
          continue

        message = await self.ws.recv()
        # self.logger(f"WebSocketClient: Received {message}")

        await self.publish(message, WebSocketClient.EventDirection.RECEIVED)
      except Exception:
        # self.logger(f"WebSocketClient: Error {e} while sending message {message}")
        await asyncio.sleep(0.1)


async def connect_aoai():
  client = WebSocketClient()
  await client.connect(
    "wss://openai-chatgpt-o1-preview.openai.azure.com/openai/realtime?api-version=2024-10-01-preview&deployment=gpt-4o-realtime-preview",
    **{"api-key": aoai_key},
  )
  return client


async def connect_openai():
  client = WebSocketClient()
  await client.connect(
    "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17",
    **{
      "Authorization": f"Bearer {openai_key}",
      "OpenAI-Beta": "realtime=v1",
    },
  )
  return client


async def connect_echo():
  asyncio.create_task(echo_server(8765))
  await asyncio.sleep(0.1)

  client = WebSocketClient()
  await client.connect("ws://localhost:8765")
  await asyncio.sleep(0.1)
  return client
