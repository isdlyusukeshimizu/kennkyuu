import datetime
import json


class EventListener:
  """
  callbacks can make assumptions about the event it handles.
  example:
    by setting event type to response.done,
    you can assume the message is in the format of a response.done event.
  """

  def __init__(self, event_type, callback):
    "event_type will be matched as a prefix"
    self.event_type = event_type
    self.callback = callback


def _log(msg: dict, blacklist=[], whitelist=[], format=True):
  "event filtering can be done with either a blacklist or a whitelist"

  event = msg["type"]
  if blacklist and event not in blacklist:
    print(json.dumps(msg, indent=2) if format else msg)
    return

  if event in whitelist:
    print(json.dumps(msg, indent=2) if format else msg)


def get_transcripts(msg: dict):
  for output in msg["response"]["output"]:
    for content in output["content"]:
      yield content["transcript"]


def _print_transcripts(msg: dict):
  # This is ideal but sometimes server send empty outputs.
  # print(datetime.datetime.now().strftime("%H:%M:%S"), "  ", msg["response"]["output"][0]["content"][0]["transcript"])

  for transcript in get_transcripts(msg):
    print(datetime.datetime.now().strftime("%H:%M:%S.%f"), "  ", transcript)


def _capture_transcripts(msg: dict, captured):
  for transcript in get_transcripts(msg):
    captured.append(transcript)


print_transcripts = EventListener("response.done", _print_transcripts)
log = EventListener("", _log)
capture = EventListener("response.done", _capture_transcripts)
