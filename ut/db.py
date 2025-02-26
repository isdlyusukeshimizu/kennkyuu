import os

from pydantic import BaseModel
from pymongo import MongoClient, database

uri_prd = os.getenv("CONNECTION_STRING_PRD")
client_prd = MongoClient(uri_prd, readPreference="secondary")
db_prd = client_prd["botchan_aifaq"]

uri_prd_write = os.getenv("CONNECTION_STRING_PRD_WRITE")
client_prd_write = MongoClient(uri_prd_write)
db_prd_write = client_prd_write["botchan_aifaq"]

uri_stg = os.getenv("CONNECTION_STRING_STG")
client_stg = MongoClient(uri_stg)
db_stg = client_stg["botchan_aifaq_STG"]
db_dev = client_stg["botchan_aifaq_DEV"]

os.system("brew services start mongodb-community")
client_local = MongoClient("localhost", 27018)
db_local = client_local["botchan_aifaq"]


def get_tenants_from_whitelist(db, whitelist):
  "whitelist contains a list of either tenant_id or tenant_name"
  return list(
    db["tenants"].find(
      {
        "$or": [
          {"connect_page_id": {"$in": whitelist}},
          {"name": {"$in": whitelist}},
        ]
      }
    )
  )


def tenant_name(tenant):
  return f"{tenant['name']} > {tenant['directory_name']}"


class TenantVariables(BaseModel):
  name: str
  connect_page_id: str
  index_name: str
  prompt_system: str
  prompt_keyword: str
  bot_config: dict = None


def get_tenant_variables(db, connect_page_id) -> TenantVariables:
  """
  Retrieve tenant variables for prototyping based on the connect_page_id.

  Args:
      db (MongoClient): The MongoDB client instance to use for querying.
      connect_page_id (str): The connect page ID of the tenant.

  Returns:
      TenantVariables: An instance of TenantVariables containing tenant details.

  Raises:
      ValueError: If no tenants are found or required data is missing in the database.
  """
  tenants = get_tenants_from_whitelist(db, [connect_page_id])
  if not tenants:
    raise ValueError(f"No tenants found for connect_page_id: {connect_page_id}")
  name = tenant_name(tenants[0])
  env_var = db["multitenant_page_env_variables"].find_one({"connect_page_id": connect_page_id})
  page_msg = db["multitenant_page_messages"].find_one({"connect_page_id": connect_page_id})

  if not all([name, env_var, page_msg]):
    raise ValueError(f"{connect_page_id} not found in db")

  return TenantVariables(
    name=name,
    connect_page_id=connect_page_id,
    index_name=env_var["SEARCH_INDEX_NAME"],
    prompt_system=page_msg["system_message_prompt"],
    prompt_keyword=page_msg["query_generation_prompt"],
  )
