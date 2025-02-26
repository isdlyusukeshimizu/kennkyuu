import asyncio

import websockets


async def echo_server(port):
  "This is for testing the websocket client."

  async def echo(ws):
    async for message in ws:
      print(f"Websocket server Received: {message}")
      await ws.send(message)
      print(f"Websocket server Sent: {message}")

  print("WebSocket server starting")
  async with websockets.serve(echo, "localhost", port):
    print("WebSocket server started")
    await asyncio.Future()
    print("WebSocket server finished")
