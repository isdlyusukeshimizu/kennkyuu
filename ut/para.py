import concurrent.futures
import math
import os

from tqdm import tqdm


def _impl_process_in_parallel(fn, data, chunking=False, max_workers=os.cpu_count(), **kwargs):
  """
  This algorithm submits a new task only when an old one finishes.
  Submitting all tasks at once has no clean way to stop midway.

  There are 3 phases:
  1. Submit the first batch of tasks, so each thread gets some tasks to work on.
  2. Sor each task finished, submit a new task, unless all tasks are submitted.
  """
  executor = concurrent.futures.ThreadPoolExecutor(max_workers)

  submitted = {executor.submit(fn, item, **kwargs): i for i, item in enumerate(data[:max_workers])}
  completed = 0
  total = len(data)
  while completed < total:
    completed_future = next(iter(concurrent.futures.as_completed(submitted)))
    input_index = submitted.pop(completed_future)
    result = completed_future.result()
    completed += 1
    yield input_index, result

    unsubmitted = total - completed - len(submitted)
    if unsubmitted > 0:
      next_index = completed + len(submitted)
      next_input = data[next_index]
      submitted[executor.submit(fn, next_input, **kwargs)] = next_index

  executor.shutdown()


def process_chunks_in_parallel(fn, data, max_workers=os.cpu_count(), **kwargs):
  "Use this when `fn` takes a list of data. `data` will be chunked evenly."
  chunk_size = math.ceil(len(data) / max_workers)
  chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

  iter = _impl_process_in_parallel(fn, chunks, max_workers=max_workers, **kwargs)
  bar = tqdm(total=len(data))
  result = {}
  for idx, chunk_result in iter:
    result[idx] = chunk_result
    bar.update(len(chunk_result))

  stacked_results = []
  for i in range(len(chunks)):
    stacked_results.extend(result[i])

  return stacked_results


def process_list_in_parallel(fn, data, **kwargs):
  iter = _impl_process_in_parallel(fn, data, **kwargs)
  result = [[k, v] for k, v in tqdm(iter, total=len(data))]
  result.sort(key=lambda x: x[0])
  return [v for k, v in result]
