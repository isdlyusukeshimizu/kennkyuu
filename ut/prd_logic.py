# This is a set of reimplemented production logic that is meant to be more readable
# it does not guarantee to produce the same results, only something close

import re
from collections import defaultdict

import mistune
import tiktoken
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import QueryType, VectorizedQuery
from bs4 import BeautifulSoup
from bson import ObjectId
from jinja2 import Environment, FileSystemLoader

from ut.db import TenantVariables
from ut.files import format_citation_info

enc = tiktoken.encoding_for_model("gpt-4o")
env = Environment(loader=FileSystemLoader("ut/prompts"))
sys_tmpl = env.get_template("system.jinja2")


def search(client: SearchIndexClient, index_name, vector, keywords, k_nearest_neighbors=80, top_n=3):
  "This is the default search used in production."
  search_client = client.get_search_client(index_name)

  vector_query = VectorizedQuery(vector=vector, k_nearest_neighbors=k_nearest_neighbors, fields="titleVector")
  results = search_client.search(
    search_text=keywords,
    vector_queries=[vector_query],
    query_type=QueryType.SEMANTIC,
    semantic_configuration_name="semantic-search-config",
    top=top_n,
  )

  results = [result for result in results]
  return results


def split_instructions(raw: str) -> list[str]:
  """
  Parse a raw str possibly containing multiple instructions into its parts.
  Lines starting with two empty spaces will be considered part of a multiline instruction.
  """
  instructions = []
  if not raw:
    return instructions

  current_instruction = ""
  for line in raw.split("\n"):
    if line.startswith("  "):  # continue the existing multiline instruction
      current_instruction += f"\n{line}"
    else:  # the start of a new instruction
      if current_instruction:
        instructions.append(current_instruction)
      current_instruction = line
  if current_instruction:
    instructions.append(current_instruction)
  return instructions


def limit_documents(documents, token_limit=2000, encoder=enc):
  out_documents = []

  tokens_left = token_limit  # Loop Invariant
  for doc in documents:
    title_tokens = len(encoder.encode(doc["Title"]))
    content_tokens = len(encoder.encode(doc["Content"]))
    doc_tokens = title_tokens + content_tokens

    if tokens_left >= doc_tokens:  # Can fit the whole document
      out_documents.append(doc)
      tokens_left -= doc_tokens  # Update Loop Invariant
    elif tokens_left > title_tokens:  # Can fit some content
      usable_tokens = tokens_left - title_tokens
      # removing the last character in case we were in the middle of a multi-token sequence
      usable_content = encoder.decode(encoder.encode(doc["Content"])[:usable_tokens])[:-1]
      doc["Content"] = usable_content
      out_documents.append(doc)
      spent_tokens = title_tokens + len(encoder.encode(usable_content))
      tokens_left -= spent_tokens  # Update Loop Invariant
      break
    else:  # not enough tokens left to include even the title
      break

  return out_documents


def assemble_msgs(var: TenantVariables, docs, usr_msg):
  docs = limit_documents(docs)

  data_instructions = defaultdict(list)
  for doc in docs:
    instructions = split_instructions(doc["Instructions"])
    for instruction in instructions:
      data_instructions[instruction].append(doc["Title"])

  sys = sys_tmpl.render(main_instructions=var.prompt_system, data_instructions=data_instructions, docs=docs)
  msgs = [
    {"role": "system", "content": sys},
    {"role": "user", "content": usr_msg},
  ]
  return msgs


def validate_url(answer: str) -> str:
  """
  Validate and format URLs contained in the answer.
  """
  regex = re.compile(
    r"""
      (                                   # Capture the entire URL
          (
              (                           # Capture the scheme
                  [A-Za-z]{3,9}           # Scheme (e.g., http, https, ftp)
                  :(?:\/\/)?              # :// (optional)
              )
              (?:[-;.:&=\+\$,\w]+@)?      # Optional user info (e.g., user:pass@)
              [A-Za-z0-9.-]+              # Hostname (e.g., example.com or 192.168.0.1)
              (:[0-9]{1,5})?              # Optional port (e.g., :8080)
              |                           # OR
              (?:www.|[-;.:&=\+\$,\w]+@)  # Alternative host (e.g., www.example.com or user@)
              [A-Za-z0-9.-]+              # Hostname (e.g., example.com or 192.168.0.1)
          )
          (                               # Capture the path, query, and fragment
              (\/(?:[\+~@%\/.\w\-_])*)?   # Path (e.g., /path/to/resource)
              (\?(?:[-\+=&;%@.\w_])*)?    # Query (e.g., ?key=value)
              (\#(?:[.\-~\!\/\\\w])*)?    # Fragment (e.g., #section-1)
          )?
      )
  """,
    re.VERBOSE | re.ASCII,
  )

  urls = regex.finditer(answer)
  new_answer = ""
  previous_end = 0
  for item in urls:
    url = item.group()
    url_start = item.start()
    url_end = item.end()
    # Check if the url is already formatted
    formatted_links = [f"href={url}", f'href="{url}"', f"{url}</a>"]
    if url.startswith("http") and all(lnk not in answer for lnk in formatted_links):
      url = url.strip(".")
      link_text = url

      # Concate current formatted url to end of previous answer
      new_answer += (
        answer[previous_end:url_start] + f"<a href={url} target=_blank rel=noopener noreferrer>{link_text}</a>"
      )
      previous_end = url_end
  new_answer += answer[previous_end:]
  return new_answer


def replace_with_tel_url(match) -> str:
  phone_number = match.group(0)
  normalized_phone_number = phone_number
  for char in "()- ":
    normalized_phone_number = normalized_phone_number.replace(char, "")

  if len(normalized_phone_number) < 9:
    return phone_number

  return f'<a href="tel:{normalized_phone_number}">{phone_number}</a>'


def replace_phone_number(input_text) -> str:
  regex_phone_number = r"\(?\d{1,4}\)?[-\s]\d{2,4}[-\s]\d{2,4}"
  return re.sub(regex_phone_number, replace_with_tel_url, input_text)


def replace_email(input_text: str) -> str:
  regex = r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"
  emails = re.findall(regex, input_text)
  emails = list(dict.fromkeys(emails))
  for mail_address in emails:
    html_tag = f"""<a href = "mailto: {mail_address}">{mail_address}</a>"""
    input_text = input_text.replace(mail_address, html_tag)
  return input_text


def join_strings_exclude_consecutive_lists(string_list):
  """Function to fix newline spacings between list tags.
  <ol> and <ul> tags usually have extra padding inbuilt into the html tags, therefore
  we need to remove \n characters for list items or items after them.
  """
  result = []
  for i, string in enumerate(string_list):
    if i == 0:
      result.append(string)
    else:
      if string.strip().startswith(("<ol", "<ul")) and result[-1].strip().endswith(("</ol>", "</ul>")):
        result.append(string)
      elif result[-1].strip().endswith(("</ol>", "</ul>")):
        result.append(string)
      else:
        result.append("\n" + string)
  return "\n".join(result)


def convert_markdown(text: str) -> str:
  """
  Convert markdown and HTML content in a given text to cleaned HTML.

  Args:
      text (str): The input text containing markdown and/or HTML content.

  Returns:
      str: The processed HTML string.
  """

  cleaned_sections = []
  for section in text.split("\n\n"):
    # Parse HTML elements with BeautifulSoup
    clean_section = str(BeautifulSoup(section, "html.parser"))
    # Convert each section to HTML using mistune parser
    clean_section = mistune.html(clean_section)
    # Remove unnecessary characters in cleaned text
    cleaned_html = (
      clean_section.replace("\n", "")
      .replace("<p>", "")
      .replace("</p>", "")
      .replace("&gt;", "")  # BS4 parser converts blockquote markdown to &gt;
    )
    cleaned_sections.append(cleaned_html)

  cleaned = join_strings_exclude_consecutive_lists(cleaned_sections)

  return cleaned


def process_attachments(qa_data) -> list:
  """
  Process attachments from the QA data and return a lis of formattedd files.
  """
  attachments = []
  if qa_data and "attachments" in qa_data:
    for attachment in qa_data["attachments"]:
      _file = format_citation_info(
        link=attachment.get("file_path", ""),
        file_name=attachment.get("file_real_name", ""),
        file_url=attachment.get("file_thumbnail", attachment.get("file_path", "")),
        type=("image" if attachment.get("file_thumbnail") else attachment.get("file_type", "")),
      )
      if _file:
        attachments.append(_file)

  return attachments


def reindex_citation(response, pattern):
  """Replace citation placeholders in the response with their corresponding indices.

  Ex. If response string contains placeholders 情報1, 情報2, & 情報3,
  and response only cites source 2 (i.e.情報2), the loop will replace it with 1."""

  match = re.findall(pattern, response)
  matches = list(dict.fromkeys(match))
  for idx, match in enumerate(matches, 1):
    infono = f"情報{match}"
    response = response.replace(infono, str(idx))
  return response


def validate_source(knowledge_base, answer, db, var: TenantVariables, show_default_footer: bool = True):
  """Validate the source of the generated answer, then return the formatted answer with citations and attachments."""
  pattern = r"(?<=\情報)[0-9]+"
  match = re.findall(pattern, answer)
  matches = list(dict.fromkeys(match))
  attached_files = []
  references = []

  valid_citations = {}
  for match in matches:
    # Convert citation number to zero-based index
    cite_idx = int(match) - 1
    # Check if the citation index is within the knowledge base
    # If not, remove invalid citations from the response message
    if cite_idx < len(knowledge_base):
      valid_citations[match] = cite_idx
    else:
      answer = answer.replace(f"情報{match}", "")

  if not valid_citations:
    return answer, attached_files, references

  citations = []
  for match, cite_no in valid_citations.items():
    document = knowledge_base[cite_no]
    index = document.get("Index", "")

    # Process attachments from the QA data and return a list of formatted files
    qa_data = db["qa_data"].find_one({"connect_page_id": var.connect_page_id, "_id": ObjectId(index)})

    if qa_data is None:
      answer = answer.replace(f"[情報{match}]", "")
      print(f"Referenced QA data not found for index: {index}")
      continue

    attached_files.extend(process_attachments(qa_data))

    # Format the citation URL to viewable link to be displayed in the answer
    url = document.get("URL", "")
    question = qa_data.get("question", "").strip()
    references.append(document)
    if url:
      citation_desc = f"<a href={url} target=_blank rel=noopener noreferrer>{question}</a>"
    elif show_default_footer:
      citation_desc = "学習データを参照して回答しています"
    else:
      answer = answer.replace(f"[情報{match}]", "")
      continue
    cite = f"[情報{match}] {citation_desc}"
    citations.append(cite)

  # Reindex the citations in the response
  if citations:
    answer = "\n".join([answer, "========"] + citations)
    answer = reindex_citation(answer, pattern)

  return answer, attached_files, references


def response_post_processing(
  response_text, var: TenantVariables, docs, db, is_convert_markdown=True, show_default_footer=True
):
  """
  Integrate all the post-processing functions to validate the response text and return the final answer.
  """
  if is_convert_markdown:
    response_text = convert_markdown(response_text)
  response_text = validate_url(response_text)
  response_text = replace_phone_number(response_text)
  response_text = replace_email(response_text)

  answer_text, answer_files, answer_references = validate_source(
    knowledge_base=docs, answer=response_text, db=db, var=var, show_default_footer=show_default_footer
  )

  return answer_text, answer_files, answer_references
