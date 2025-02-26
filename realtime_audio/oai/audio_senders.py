import asyncio
import base64

import pyaudio
from oai.client import WebSocketClient
from pydub import AudioSegment  # newly added import

pya = pyaudio.PyAudio()


class MicAudioSender:
  def __init__(self, websocket_client: WebSocketClient):
    self.ws = websocket_client
    asyncio.create_task(self.listen_audio())

    self.stream = None

  async def listen_audio(self):
    while True:
      try:
        if not self.stream or self.stream.is_stopped():
          print("MicAudioSender: Stream stopped")
          await asyncio.sleep(0.1)
          continue

        data = await asyncio.to_thread(self.stream.read, 1024)
        encoded = base64.b64encode(data).decode("utf-8")
        event = {
          "type": "input_audio_buffer.append",
          "audio": encoded,
        }
        await self.ws.enqueue(event)
      except Exception as e:
        print("MicAudioSender: Error", e)
        await asyncio.sleep(0.1)

  async def start(self):
    if not self.stream:
      mic_info = pya.get_default_input_device_info()
      self.stream = await asyncio.to_thread(
        pya.open,
        format=pyaudio.paInt16,
        channels=1,
        rate=16_000,
        input=True,
        input_device_index=mic_info["index"],
        frames_per_buffer=1024,
      )
    else:
      self.stream.start()

  def stop(self):
    self.stream.stop_stream()


# design note: this class is a shallow wrapper around the websocket client. does it need to exist?
# send_audio could be just a method.
class FileAudioSender:
  def __init__(self, websocket_client: WebSocketClient):
    self.ws = websocket_client

  async def send_audio(self, file_path: str, commit=True):
    "To send multiple files, turn commit off, then call commit manually."

    # Load audio from the file regardless of its format
    audio = AudioSegment.from_file(file_path)
    file_bytes = audio.raw_data
    # 15MiB chunk size
    chunk_size = 1024 * 1024 * 15

    for i in range(0, len(file_bytes), chunk_size):
      data = file_bytes[i : i + chunk_size]
      encoded = base64.b64encode(data).decode("utf-8")
      event = {
        "type": "input_audio_buffer.append",
        "audio": encoded,
      }
      await self.ws.enqueue(event)
    if commit:
      await self.commit()

  async def commit(self):
    await self.ws.enqueue({"type": "input_audio_buffer.commit"})
