def add_text(text: str):
  return {
    "type": "conversation.item.create",
    "item": {
      "type": "message",
      "role": "user",
      "content": [{"type": "input_text", "text": text}],
    },
  }


# asks the model to generate a response when automatic VAD is off.
# this will use the full context of the conversation
# but we can also configure the event to use selected context.
generate_response = {"type": "response.create"}


def append_audio(encoded: str):
  """
  The audio should be encoded in base64 in the session's format.
  See https://platform.openai.com/docs/api-reference/realtime-server-events/session/created#realtime-server-events/session/created-session
  """
  return {
    "type": "input_audio_buffer.append",
    "audio": encoded,
  }
