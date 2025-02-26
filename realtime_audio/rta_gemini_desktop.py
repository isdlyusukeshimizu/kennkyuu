import argparse
import asyncio
import traceback

import pyaudio
from google import genai

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
MODEL = "models/gemini-2.0-flash-exp"

client = genai.Client(http_options={"api_version": "v1alpha"})

sys_msg = """
あなたはコールセンターのオペレーターとして、お客様の電話を受けることになりました。以下の指示に従って、お客様の注文を受け付けてください。

コールセンター名: ウェブナルコールセンター
オペレーター名: 田中 太郎
商品名：ウェブなるケーキ
価額：500円
定期割引：50円

1. お客様からの電話を受けたら、以下の挨拶を行う：
   「お電話ありがとうございます！[コールセンター名]の[オペレーター名]と申します。本日はどのようなご用件でお電話いただけましたでしょうか？」

2. お客様が注文を希望する場合、以下のように応答する：
   「ありがとうございます！かしこまりました。それでは、ご注文を進めるにあたり、お名前とご連絡先をお伺いしてもよろしいでしょうか？」

3. お客様の名前を聞いたら、漢字の確認を行う：
   「ありがとうございます！[お客様の名前]様ですね。漢字について確認させていただいてもよろしいでしょうか？」

4. お客様の名前の漢字を確認したら、再度確認する：
   「ありがとうございます！[お客様の名前の漢字の説明]で[お客様の名前]様ですね。こちらでお間違いないでしょうか？」

5. お客様の電話番号を聞く：
   「ありがとうございます！続いて、ご連絡先の電話番号をお伺いしてもよろしいでしょうか？」

6. お客様の電話番号を確認する：
   「[お客様の電話番号]ですね。こちらでお間違いないでしょうか？」

7. お客様の住所を聞く：
   「ありがとうございます！次にご住所をお伺いできますでしょうか？」

8. お客様の住所を確認する：
   「[お客様の住所]ですね。こちらでお間違いないでしょうか？」

9. お客様のメールアドレスを聞く：
   「ありがとうございます！最後にメールアドレスを教えていただけますか？」

10. お客様のメールアドレスを確認する：
    「[お客様のメールアドレス]ですね。スペルは[お客様のメールアドレスのスペル]でお間違いないでしょうか？」

11. 定期コースの案内を行う：
    「ありがとうございます！最後に、[商品名]は単品購入だけでなく、定期コースもご用意しております。こちらのコースにご加入いただくと、毎月[定期割引]がお得にお届けできるほか、初回割引も適用されますが、いかがでしょうか？」

12. お客様が定期コースを希望する場合、最終確認を行う：
    「ありがとうございます！それでは、定期コースで手続きさせていただきます。最終確認です。お名前は[お客様の名前]様、お電話番号は[お客様の電話番号]、ご住所は[お客様の住所]、メールアドレスは[お客様のメールアドレス]、定期コースご希望で間違いないでしょうか？」

13. 手続き完了の案内を行う：
    「ありがとうございます！それでは手続き完了です。本日はご注文ありがとうございました。商品到着をどうぞお楽しみにしてください！」
"""

CONFIG = {"generation_config": {"response_modalities": ["AUDIO"]}, "system_instructions": sys_msg}

pya = pyaudio.PyAudio()


class AudioLoop:
  def __init__(self):
    self.audio_in_queue = None
    self.out_queue = None

    self.session = None

    self.send_text_task = None
    self.receive_audio_task = None
    self.play_audio_task = None

  async def send_realtime(self):
    while True:
      msg = await self.out_queue.get()
      await self.session.send(msg)

  async def listen_audio(self):
    mic_info = pya.get_default_input_device_info()
    self.audio_stream = await asyncio.to_thread(
      pya.open,
      format=FORMAT,
      channels=CHANNELS,
      rate=SEND_SAMPLE_RATE,
      input=True,
      input_device_index=mic_info["index"],
      frames_per_buffer=CHUNK_SIZE,
    )
    if __debug__:
      kwargs = {"exception_on_overflow": False}
    else:
      kwargs = {}
    while True:
      data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
      await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

  async def receive_audio(self):
    "Background task to reads from the websocket and write pcm chunks to the output queue"
    while True:
      turn = self.session.receive()
      async for response in turn:
        if data := response.data:
          self.audio_in_queue.put_nowait(data)
          continue
        if text := response.text:
          print(text, end="")

      # If you interrupt the model, it sends a turn_complete.
      # For interruptions to work, we need to stop playback.
      # So empty out the audio queue because it may have loaded
      # much more audio than has played yet.
      while not self.audio_in_queue.empty():
        self.audio_in_queue.get_nowait()

  async def play_audio(self):
    stream = await asyncio.to_thread(
      pya.open,
      format=FORMAT,
      channels=CHANNELS,
      rate=RECEIVE_SAMPLE_RATE,
      output=True,
    )
    while True:
      bytestream = await self.audio_in_queue.get()
      await asyncio.to_thread(stream.write, bytestream)

  async def run(self):
    try:
      async with (
        client.aio.live.connect(model=MODEL, config=CONFIG) as session,
        asyncio.TaskGroup() as tg,
      ):
        self.session = session

        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue(maxsize=5)

        tg.create_task(self.send_realtime())
        tg.create_task(self.listen_audio())
        tg.create_task(self.receive_audio())
        tg.create_task(self.play_audio())

        await tg.__aexit__(None, None, None)

        raise asyncio.CancelledError("User requested exit")

    except asyncio.CancelledError:
      pass
    except ExceptionGroup as EG:
      traceback.print_exception(EG)
      self.audio_stream.close()


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  args = parser.parse_args()
  main = AudioLoop()
  asyncio.run(main.run())
