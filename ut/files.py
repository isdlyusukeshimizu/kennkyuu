import re
import urllib.parse

FILE_FORMAT = [
  "csv",
  "pdf",
  "doc",
  "docx",
  "xls",
  "xlsx",
  "ppt",
  "pptx",
]

VIDEO_FORMAT = [
  "mp4",
  "avi",
  "mov",
  "wmv",
  "flv",
  "mkv",
  "m4v",
  "mpg",
  "mpeg",
  "webm",
]

IMAGE_FORMAT = ["jpg", "png", "image"]


def format_citation_info(link, file_name, file_url, type):
  if re.match(r"^.+?\.[a-zA-Z0-9_\-]+$", file_name) is None:
    # Return early if the file name does not match the expected pattern
    return

  file = {}
  PDF_VIEWER_URL = "http://example.com/viewer"  # temporary URL
  # In case of PDF files, convert the link field to PDF viewer link,
  # so that it will open as a new tab when user clicks on
  # In case of other files, keep the link as it is, which will download the file when clicked
  if file_name.endswith(".pdf"):
    parsed_file_name = urllib.parse.quote(link, safe="")
    file["link"] = f"{PDF_VIEWER_URL}?filename={parsed_file_name}"
  else:
    file["link"] = link
  file["name"] = file_name

  # file_url will be the liink to thumbnail image for documents files (pdf, docx, etc.)
  # for other files it will be the same as file["link"]
  file["file_url"] = file_url

  if type != "":
    type = type.lower()
    if len(type.split("/")) > 1:
      file["type"] = type.split("/")[0]
      file["content_type"] = type
      return file
    else:
      format = type

  if format in FILE_FORMAT:
    file["type"] = "file"
    file["content_type"] = f"file/{format}"
  elif format in IMAGE_FORMAT:
    file["type"] = "image"
    file["content_type"] = "image"
  elif format in VIDEO_FORMAT:
    file["type"] = "video"
    file["content_type"] = f"video/{format}"
  else:
    raise TypeError(f"Type of {file_name} not supported: {format}")
  return file
