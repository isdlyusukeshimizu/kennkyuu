from time import sleep

import gspread
import pandas as pd
from tqdm import tqdm

gc = gspread.service_account(filename="botchan-ai-research-fb605.json")
reserved_sheet = "gspread"


def get_sheet_by_name(ss, sheet_name):
  try:
    return ss.worksheet(sheet_name)
  except gspread.WorksheetNotFound:
    ss.add_worksheet(sheet_name, 1000, 100)
    return ss.worksheet(sheet_name)


def get_as_dataframe(ws):
  rows = ws.get_all_values()
  df = pd.DataFrame(rows[1:], columns=rows[0])
  return df


def set_with_dataframe(ws, df):
  # Normalizes the dataframe for writing into Google Sheets.
  df = df.fillna("")
  df = df.map(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else x)

  existing_data = ws.get_all_values()
  new_data = [df.columns.tolist()] + df.values.tolist()

  try:
    ws.clear()
    ws.update(values=new_data)
  except Exception as e:
    print(f"Failed to update worksheet {ws.title}. Restoring previous data. Error: {e}")
    ws.update(values=existing_data)


def set_ss_with_dataframe(ss, ws_df, clear=False):
  "set the spreadsheet with a dataframe per sheet"
  if clear:
    # Google sheets does not allow deleting the last sheet
    # So we create one if not exists
    get_sheet_by_name(ss, reserved_sheet)
    for ws in ss.worksheets():
      if ws.title != reserved_sheet:
        ss.del_worksheet(ws)

  for name, df in tqdm(ws_df.items()):
    ws = get_sheet_by_name(ss, name)
    set_with_dataframe(ws, df)
    sleep(5)
