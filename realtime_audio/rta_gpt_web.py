import asyncio
import base64
import json
import os
import traceback
from datetime import datetime
from enum import Enum

import aiofiles
import websockets
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from pytz import timezone
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, VoiceResponse

from ut.aoai import openai_key
from ut.aoai import rta_key as aoai_key

provider = "openai"  # "azure" "openai"

acc_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(acc_sid, auth_token)


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

system_msg = """
あなたは日本のウェブナル(wevnal)コールセンターのオペレーターです。
以下の接客手順に従って、お客様の受け付けをしてください。
ただ、もしお客様の回答が少し接客手順と違う場合、無理に手順通りに進めず、
お客様の言葉に合わせて、臨機応変に対応してください。

あなたは接客に慣れているオペレーターです。
やや早く話してください。
ただ、数字や情報の確認をとるときに、ややゆっくりで、区切りを意識しながら話してください。
また、その場の雰囲気を考えて、お客さんに寄り添った感情で話してください。
例えば、お客様が困っている時や、悲しいときに、同情の気持ちを持って話してください。
お客様から怒りを感じるとき、お客様の感情を理解し、優しく対応してください。
ただ、感情を持っても、手順やルールを違反したりしないでください。

また、あなたは解約の受付を対応するオペレーターです。
解約理由に応じて、次回発送のスキップや、お届け頻度の変更を提案することができます。
ただし、お客様が新規注文や、返品などのサービスを要求する場合、あなたが解約の受付のみを対応できると伝えてください。
また、注文時に登録の電話番号がお客様の現在の番号と違う場合、受付はできません。
あなたができることは、要望の受付のみで、実際の手続きを進めることができません。

お客様がそうさせない限り、お客様からの情報を復唱しないでください。

あなたはあらゆる言語を理解でき、流暢に話せます。
お客様が日本語以外の言葉を話したときに、必ずお客様が話す言葉で対応してください。
If interacting in a non-Japanese language, start by using the standard accent or dialect familiar to the user.
どの言語でも、数字を読むよきに、1桁づつ発音してください。
日本語の数字の発音：
  0: ゼロ
  1: イチ
  2: ニ
  3: サン
  4: ヨン
  5: ゴ
  6: ロク
  7: ナナ
  8: ハチ
  9: キュウ

==========

概要：
お客様の電話番号、解約する商品名と解約の理由を確認してください。

接客手順:
  最初から挨拶を行なう: 
    「お電話ありがとうございます。
    株式会社ウェブナルのAI電話アシスタントです。
    本日はどのようなご用件でお電話いただけましたでしょうか。」

  お客様の要件が解約である場合、続けてください。
  もし解約の商品がわからない場合、お客様に商品名を尋ねてください。
    「かしこまりました。
    では、ご解約されたい商品を教えていただけますでしょうか。」

  商品がわかったら、お客様の電話番号を確認してください。
    「ありがとうございます。
    ご注文時にご登録いただいた電話番号は、現在お使いの電話番号で、下4桁が「xxxx」でよろしいでしょうか。」

  電話番号も商品名もわかったら、解約の理由を尋ねてください。
    「ありがとうございます。
    もし差しつかえなければ、ご解約されたい理由をおうかがいできますか？」

理由ごとの対応：
  お客様の解約理由が、注文した商品が余っている・使い切れない場合、定期便の一旦中止や、期間の延長を提案してみてください。
    「承知いたしました。
    ご注文した商品が余っているのでしたら、
    次回のお届けをスキップしたり、
    お届け頻度を変更することも可能ですが、
    ご希望されますか？」

  定期便のスキップとして進める場合、変更の要望を承ったことを伝えてください。
    「承知いたしました。
    では次の定期便の発送を延期させるご要望をうけたまわりました。
    次回の発送日が近い場合は、
    延期できない可能性もございますので、
    その点ご了承ください。」

  お届け頻度の変更を希望する場合、それについて案内してください。
    「かしこまりました。
    お届け頻度を30日間から60日間に変更することもできますが、
    変更をご希望されますか？」

  周期の変更として進める場合、変更の要望を承ったことを伝えてください。
    「承知いたしました。
    お届け頻度の変更のご要望をうけたまわりました。
    引き続きのご愛顧の程宜しくお願いします。
    ご連絡ありがとうございました。」

  解約理由が提示した理由ケース以外の場合、解約として進めてください。
  お客様が解約以外の提案を受け入れない場合も、解約として進めてください。

  解約として進める場合、要望を承ったことを伝えてください。
    「承知いたしました。
    解約のご要望をうけたまわりました。
    これまでご利用いただき、
    誠にありがとうございました。
    またの機会がございましたら、
    是非ご利用ください。
    ご連絡ありがとうございました。」

もしお客様の解約理由や電話番号を間違えた場合、お客様に一回再確認してください。
それでも間違った場合、営業時間内に再度お電話いただくように伝えてください。
  「大変申し訳ございませんが、
  このAI電話アシスタントでの対応が難しいので、
  お手数ですが、
  平日9時から19時の間にカスタマーサポートまでお電話をお願いいたします。」

最後に、丁寧に電話を終わらせてください。"""

logged_events = {
  "response.content.done",
  "rate_limits.updated",
  "response.done",
  "input_audio_buffer.committed",
  "input_audio_buffer.speech_started",
  "input_audio_buffer.speech_stopped",
  "session.created",
}

app = FastAPI()


def connect_aoai():
  return websockets.connect(
    "wss://openai-chatgpt-o1-preview.openai.azure.com/openai/realtime?api-version=2024-10-01-preview&deployment=gpt-4o-realtime-preview",
    additional_headers={"api-key": aoai_key},
  )


def connect_openai():
  return websockets.connect(
    "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17",
    additional_headers={
      "Authorization": f"Bearer {openai_key}",
      "OpenAI-Beta": "realtime=v1",
    },
  )


connect = {"azure": connect_aoai, "openai": connect_aoai}[provider]


async def init_session(ws, ai_first=True):
  session_update = {
    "type": "session.update",
    "session": {
      "input_audio_format": "g711_ulaw",
      "output_audio_format": "g711_ulaw",
      "voice": voice,
      "instructions": system_msg,
      "temperature": 0.75,
      # "input_audio_transcription": {"model": "whisper-1"},
      "tool_choice": "auto",
      "tools": [
        {
          "type": "function",
          "name": "end_conversation",
          "description": "hung up the call. only do this at the end of the conversation.",
        },
        {
          "type": "function",
          "name": "conversation_language",
          "description": "identify the language of the user is using. do not call this before the user starts to speak."
          "do this once, after the user spoke for a few seconds, or when the user changed the language they speak in.",
          "parameters": {
            "type": "object",
            "properties": {
              "language": {
                "type": "string",
                "description": "the name of the language the user is speaking.",
              }
            },
            "required": ["language"],
          },
        },
      ],
    },
  }
  print("sending session update:", json.dumps(session_update, ensure_ascii=False))
  await ws.send(json.dumps(session_update))

  if ai_first:
    await ws.send(json.dumps({"type": "response.create"}))


async def log_event(sid, event, source):
  async with aiofiles.open(f"events_log_{sid}.jsonl", mode="a") as log_file:
    event["meta"] = {"from": source, "timestamp": str(datetime.now(tz=timezone("Asia/Tokyo")))}
    log_entry = json.dumps(event, ensure_ascii=False)
    await log_file.write(log_entry + "\n")


class InterruptionHandler:
  def __init__(self):
    self.latest_media_timestamp = 0
    self.last_assistant_item = None
    self.mark_queue = []
    self.response_start_timestamp_twilio = None

  async def interrupt_response_on_caller_speech(self, event_type, message, ws_aoai, ws_twilio, stream_sid):
    if event_type != "input_audio_buffer.speech_started":
      return

    if self.mark_queue and self.response_start_timestamp_twilio:
      elapsed_time = int(self.latest_media_timestamp) - int(self.response_start_timestamp_twilio)
      if self.last_assistant_item:
        truncate_event = {
          "type": "conversation.item.truncate",
          "item_id": self.last_assistant_item,
          "content_index": 0,
          "audio_end_ms": elapsed_time,
        }
        await ws_aoai.send(json.dumps(truncate_event))

      clear_event = {
        "event": "clear",
        "streamSid": stream_sid,
      }
      await ws_twilio.send_json(clear_event)

      self.mark_queue = []
      self.last_assistant_item = None
      self.response_start_timestamp_twilio = None

  async def send_response_part_mark(self, event_type, message, ws_twilio, stream_sid):
    if event_type != "response.audio.delta" or not message.get("delta"):
      return
    if stream_sid:
      mark_event = {
        "event": "mark",
        "streamSid": stream_sid,
        "mark": {"name": "responsePart"},
      }
      await ws_twilio.send_json(mark_event)
      self.mark_queue.append("responsePart")

  def capture_response_start_and_item_id(self, event_type, message):
    if event_type != "response.audio.delta" or not message.get("delta"):
      return

    if self.response_start_timestamp_twilio is None:
      self.response_start_timestamp_twilio = self.latest_media_timestamp

    if message.get("item_id"):
      self.last_assistant_item = message["item_id"]

  def update_latest_media_timestamp(self, event_type, message):
    if event_type != "media":
      return
    self.latest_media_timestamp = message["media"]["timestamp"]

  def reset_timestamps(self, event_type):
    if event_type != "start":
      return
    self.response_start_timestamp_twilio = None
    self.latest_media_timestamp = 0

  def process_mark_queue_on_received_mark(self, event_type):
    if event_type != "mark":
      return
    if self.mark_queue:
      self.mark_queue.pop(0)


@app.get("/", response_class=JSONResponse)
async def read_root():
  return {"message": "RTA Twilio is running."}


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
  response = VoiceResponse()
  host = request.url.hostname
  connect = Connect()
  connect.stream(url=f"wss://{host}/media-stream")
  response.append(connect)
  return HTMLResponse(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(ws_twilio: WebSocket):
  print("client connected")
  await ws_twilio.accept()

  async with connect() as ws_aoai:
    try:
      await init_session(ws_aoai)
    except Exception as e:
      print(f"error initializing: {e}")
      traceback.print_exc()
      async for message in ws_aoai:
        print(f"received: {message}")
      return

    stream_sid = None
    interruption_handler = InterruptionHandler()

    async def on_twilio_event():
      nonlocal stream_sid
      try:
        async for message in ws_twilio.iter_text():
          data = json.loads(message)

          event = data["event"]
          if event == "start":
            stream_sid = data["start"]["streamSid"]
            print(f"stream started: {stream_sid}")
            call = client.calls.get(data["start"]["callSid"]).fetch()
            caller_number = call.from_formatted
            caller_number = " ".join(caller_number)
            print(f"caller: {str(caller_number)}")
            update = {
              "type": "conversation.item.create",
              "previous_item_id": "root",
              "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": f"お客さんの電話番号: {caller_number}"}],
              },
            }
            await ws_aoai.send(json.dumps(update))
            await log_event(stream_sid, data, "twilio")
            await ws_aoai.send(json.dumps({"type": "response.create"}))  # assistant speaks first
          elif event == "media" and ws_aoai.state == websockets.protocol.State.OPEN:
            audio_append = {
              "type": "input_audio_buffer.append",
              "audio": data["media"]["payload"],
            }
            await ws_aoai.send(json.dumps(audio_append))
          elif event == "stop":  # call ended
            await ws_aoai.close()
            return

          if data["event"] != "media":
            await log_event(stream_sid, data, "twilio")

          interruption_handler.update_latest_media_timestamp(event, data)
          interruption_handler.reset_timestamps(event)

      except WebSocketDisconnect:
        print("client disconnected")
        if ws_aoai.state == websockets.protocol.State.OPEN:
          await ws_aoai.close()

    async def on_aoai_event():
      nonlocal stream_sid
      try:
        async for message in ws_aoai:
          response = json.loads(message)
          await log_event(stream_sid, response, "aoai")
          event = response["type"]

          if event in logged_events:
            print(f"aoai event: {json.dumps(response, ensure_ascii=False, indent=2)}")

          if event == "response.audio.delta" and response.get("delta"):
            audio_payload = base64.b64encode(base64.b64decode(response["delta"])).decode("utf-8")
            audio_delta = {"event": "media", "streamSid": stream_sid, "media": {"payload": audio_payload}}
            await ws_twilio.send_json(audio_delta)

          interruption_handler.capture_response_start_and_item_id(event, response)
          await interruption_handler.interrupt_response_on_caller_speech(
            event, response, ws_aoai, ws_twilio, stream_sid
          )
          await interruption_handler.send_response_part_mark(event, response, ws_twilio, stream_sid)
          interruption_handler.process_mark_queue_on_received_mark(event)

          if event == "response.done":
            for output in response["response"]["output"]:
              if output["type"] == "function_call" and output["name"] == "conversation_language":
                print(f"=================== Func call ===================  {output['arguments']}")
                language = output["arguments"]
                language = json.loads(language)
                await ws_aoai.send(
                  json.dumps(
                    {
                      "type": "conversation.item.create",
                      "previous_item_id": "root",
                      "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": f"お客さんの言語: {language['language']}"}],
                      },
                    }
                  )
                )

                # this is a hack. for some reason /realtime tends to halt at this point
                await ws_aoai.send(json.dumps({"type": "response.create"}))

      except Exception as e:
        print(f"error sending: {e}")
        traceback.print_exc()

    await asyncio.gather(on_twilio_event(), on_aoai_event())
