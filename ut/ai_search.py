import json
import os
import time
from itertools import chain

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from bson import ObjectId

from ut.aoai import embed
from ut.para import process_list_in_parallel

endpoint_dev = f"https://{os.getenv('SEARCH_SERVICE_NAME_DEV')}.search.windows.net/"
credential_dev = AzureKeyCredential(os.getenv("SEARCH_ADMIN_KEY_DEV"))
srch_dev = SearchIndexClient(endpoint=endpoint_dev, credential=credential_dev)

endpoint_stg = f"https://{os.getenv('SEARCH_SERVICE_NAME_STG')}.search.windows.net/"
credential_stg = AzureKeyCredential(os.getenv("SEARCH_ADMIN_KEY_STG"))
srch_stg = SearchIndexClient(endpoint=endpoint_stg, credential=credential_stg)

endpoint_prd = f"https://{os.getenv('SEARCH_SERVICE_NAME_PRD')}.search.windows.net/"
credential_prd = AzureKeyCredential(os.getenv("SEARCH_ADMIN_KEY_PRD"))
srch_prd = SearchIndexClient(endpoint=endpoint_prd, credential=credential_prd)


def print_stats(client):
  index_names = list(client.list_index_names())
  for index_name in index_names:
    stats = client.get_index_statistics(index_name)
    print(f"Index: {index_name}, Document Count: {stats['document_count']}, Storage Size: {stats['storage_size']}")


def dump_documents(client: SearchIndexClient, index_name):
  output = []
  results = reliably_get_all_data_from(client, index_name)
  for result in results:
    output.append(result)
  output_file = f"dump_{index_name}.json"
  with open(output_file, "w") as f:
    f.write(json.dumps(output, indent=2, ensure_ascii=False))


def copy_index(
  source_client: SearchIndexClient,
  source_index_name,
  dest_client: SearchIndexClient,
  dest_index_name,
  check_vector_field=False,
):
  source_index = source_client.get_index(source_index_name)
  source_index.name = dest_index_name
  dest_client.create_or_update_index(source_index)

  destination_search_client = dest_client.get_search_client(dest_index_name)
  documents = reliably_get_all_data_from(source_client, source_index_name)

  if check_vector_field:
    titles = [doc["Title"] for doc in documents]
    contents = [doc["Content"] for doc in documents]

    titles_vectors = embed(titles)
    contents_vectors = embed(contents)

    updated_docs = []
    for doc, embedded_title, embedded_content in zip(documents, titles_vectors, contents_vectors):
      doc["titleVector"] = embedded_title.tolist()
      doc["contentVector"] = embedded_content.tolist()
      updated_docs.append(doc)
    documents = updated_docs

  results = destination_search_client.upload_documents(documents)

  for result in results:
    print(result)
  print(f"Copied index '{source_index_name}' to '{dest_index_name}'")


def clear_index(client: SearchIndexClient, index_name):
  documents = reliably_get_all_data_from(client, index_name)
  search_client = client.get_search_client(index_name)
  search_client.delete_documents(documents)
  print(f"Cleared all documents from index '{index_name}'")


def update_document_instructions(client: SearchIndexClient, index_name, title, new_instructions):
  search_client = client.get_search_client(index_name)
  results = search_client.search(search_text=f"{title}", select=["*"])

  documents = [result for result in results if result["Title"] == title]
  if not documents:
    print(f"No document found with title: {title}")
    return

  document = documents[0]
  document["Instructions"] = new_instructions
  search_client.upload_documents([document])
  print(f'Updated instructions for document title: {document["Title"]} in index: {index_name}')


def reliably_get_all_data_from(client: SearchIndexClient, index_name, max_retries=30, wait_time=15):
  "This deals with AI Search's unreliable search all call by combining results from multiple searches."
  sc = client.get_search_client(index_name)
  stats = client.get_index_statistics(index_name)
  total_docs = stats["document_count"]

  docs = {}
  for i in range(max_retries):
    fetched_docs = [d for d in sc.search(search_text="*")]
    for doc in fetched_docs:
      id = doc["Index"]
      docs[id] = doc

    if len(docs) == total_docs:
      break

    time.sleep(wait_time)  # sometimes if you dont do this the data will be missing regardless of retry

  if len(docs) != total_docs:
    print(f"warning: fetched {len(docs)} documents, but expected {total_docs}")

  print(f"retried {i+1} times to get all data from {index_name}")
  return list(docs.values())


def get_document_category(qa_data, db):
  group_ids = qa_data.get("group_ids", [])
  if not group_ids:
    return None

  groups = []
  for group_id in group_ids:
    group = db["groups"].find_one({"_id": ObjectId(group_id)})
    groups.append(group["name"])
  return ";".join(groups)


def generate_ai_search_documents(db, qa_data_list):
  documents = []
  titles = [qa_data.get("title") for qa_data in qa_data_list]
  contents = [qa_data.get("answer") for qa_data in qa_data_list]
  title_vectors = embed(titles)
  content_vectors = embed(contents)

  categories = process_list_in_parallel(lambda data: get_document_category(data, db), data=qa_data_list)

  for qa_data, category in zip(qa_data_list, categories):
    ai_search_value = {
      "Index": str(qa_data["_id"]),
      "@search.action": "upload",
      "Title": qa_data["title"],
      "Content": qa_data["answer"],
      "URL": qa_data.get("url"),
      "Instructions": qa_data.get("instruction"),
    }

    if category:
      ai_search_value["Category"] = category
    documents.append(ai_search_value)

  for doc, title_vector, content_vector in zip(documents, title_vectors, content_vectors):
    doc["titleVector"] = title_vector.tolist()
    doc["contentVector"] = content_vector.tolist()

  return documents


def sync_db_to_ai_search(
  db,
  search_index_client,
  connect_page_id,
  batch_size=1000,  # max batch size for Azure Search service is 1000
):
  page_env_var = db["multitenant_page_env_variables"].find_one({"connect_page_id": connect_page_id})
  ai_search_client = search_index_client.get_search_client(page_env_var["SEARCH_INDEX_NAME"])

  qa_data_list = db["qa_data"].find({"connect_page_id": connect_page_id}).to_list(length=None)
  removed_data_list = []
  registered_data_list = []
  for qa_data in qa_data_list:
    if qa_data.get("deleted_at") is not None:
      removed_data_list.append(qa_data)
    else:
      registered_data_list.append(qa_data)

  for i in range(0, len(removed_data_list), batch_size):
    batch = removed_data_list[i : i + batch_size]
    ai_search_client.delete_documents(documents=[{"Index": str(qa_data["_id"])} for qa_data in batch])

  for i in range(0, len(registered_data_list), batch_size):
    batch = registered_data_list[i : i + batch_size]
    documents = generate_ai_search_documents(db, batch)
    ai_search_client.upload_documents(documents)

  ai_search_client.close()
  print("AI Search client closed.")
