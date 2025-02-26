import json
import os
import time
from itertools import chain

import numpy as np
import requests

from ut.para import process_list_in_parallel

aoai_key = os.getenv("AOAI_PLAYGROUND_KEY")
aoai_key2 = os.getenv("AOAI_PLAYGROUND2_KEY")
rta_key = os.getenv("AOAI_RTA_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

gpt_url = "https://wevnal-openai-playground2.openai.azure.com/openai/deployments/{deployment_name}/chat/completions?api-version=2024-09-01-preview"
embed_url = "https://wevnal-openai-playground.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-09-01-preview"

embed_dtype = np.float32


def retry_429(fn, *args, depth=0, max_depth=5, **kwargs):
  """
  Retries 429 which happens when we saturate the rate limit.

  This happens a lot more before gpt-4o was released.
  """
  response = fn(*args, **kwargs)

  if response.status_code == 429:
    if "Retry-After" not in response.headers:
      return response

    depth = depth + 1  # prevents infinite retry loop
    if depth > max_depth:
      return response

    # not adding 1 second sometimes result in a 1-second Retry-After
    retry_after = int(response.headers["Retry-After"]) + 1
    print(f"Rate limited, retrying after {retry_after} seconds")
    time.sleep(retry_after)
    return retry_429(fn, *args, depth=depth, max_depth=max_depth, **kwargs)

  return response


def fill_roles(msgs):
  "fill the roles for a list of messages in the order of system, user, assistant, user, assistant... for gpt calls"
  result = []
  while msgs:
    if not result:
      result.append({"role": "system", "content": msgs.pop(0)})
    elif len(result) % 2 == 1:
      result.append({"role": "user", "content": msgs.pop(0)})
    else:
      result.append({"role": "assistant", "content": msgs.pop(0)})
  return result


def gpt_call(system="", deployment_name="gpt-4o", **kwargs):
  """
  single-message call: `gpt_call(system="your_system_message")`

  multiple messages: `gpt_call(messages=fill_roles(["your_system_msg", "user_msg", "assistant_msg" ,... ]))`
  """
  headers = {"Content-Type": "application/json", "api-key": aoai_key2}

  if "temperature" not in kwargs:
    kwargs["temperature"] = 0  # Consistent output is better for programatical use of LLMs
  if system:
    kwargs["messages"] = [{"role": "system", "content": system}]
  payload = json.dumps({**kwargs})  # NB! if messages is in kwargs, it will be unpacked here

  url = gpt_url.format(deployment_name=deployment_name)
  response = retry_429(requests.post, url, headers=headers, data=payload)

  if response.status_code != 200:
    print(response.content)  # sometimes we get 400 from aoai content filter here
    return f"status code: {response.status_code}"
  content = json.loads(response.content)

  try:
    return content["choices"][0]["message"]["content"]
  except Exception:
    return content


def __chunk_texts(texts, doc_count_limit=2000, doc_char_limit=6000, chunk_char_limit=40_000):
  """
  https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/embeddings
  doc_count_limit is 2048 documents from aoai
  doc_char_limit is 8000 tokens from aoai, but len() is faster than tokenizing
  chunk_char_limit depends on the embedding model's deployment in Azure AI Foundry, often ~100k
  We are picking lower numbers to be safe.
  """
  chunks = []

  chunk = []
  chunk_len = 0
  for text in texts:
    text_len = len(text)

    if chunk_len + text_len > chunk_char_limit or len(chunk) >= doc_count_limit:
      chunks.append(chunk)
      chunk = []
      chunk_len = 0

    if text_len > doc_char_limit:
      print(f"Text too long({text_len}) for embedding and was truncated: {text[:100]}...")
      text = text[:doc_char_limit]

    chunk.append(text)
    chunk_len += text_len
  if chunk:
    chunks.append(chunk)

  return chunks


def __impl_embed(texts, dtype=embed_dtype):
  headers = {"Content-Type": "application/json", "api-key": aoai_key}
  payload = json.dumps({"input": texts})

  response = retry_429(requests.post, embed_url, headers=headers, data=payload)
  if response.status_code != 200:
    print(json.dumps(json.loads(response.content), indent=2))
  content = json.loads(response.content)

  embeds_non_blank = [datum["embedding"] for datum in content["data"]]
  return np.array(embeds_non_blank, dtype=dtype)


def embed(texts, dims=1536, dtype=embed_dtype):
  if isinstance(texts, str):
    return embed([texts])[0]  # This behavior is the same as the embedding endpoint

  if not texts:
    return np.zeros((0, dims), dtype=dtype)

  if not any(texts):
    return np.zeros((len(texts), dims), dtype=dtype)

  # Needed because the embedding endpoint does not handle empty strings
  texts_non_empty = [text for text in texts if text]

  chunks = __chunk_texts(texts_non_empty)
  chunk_embs = process_list_in_parallel(__impl_embed, chunks)

  embeds = np.zeros((len(texts), dims), dtype=dtype)
  non_empty_indices = [i for i, text in enumerate(texts) if text]

  for idx, emb in zip(non_empty_indices, chain(*chunk_embs)):
    embeds[idx] = emb

  return embeds


def print_msgs(messages):
  for msg in messages:
    print(msg["role"], ":")
    print(msg["content"])
    print()
