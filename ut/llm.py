from collections.abc import Callable
from typing import Any

from jinja2 import Template
from pydantic import BaseModel


def assemble_replace(template, **kwargs):
  for k, v in kwargs.items():
    template = template.replace(f"{{{k}}}", str(v))
  return template


def assemble_jinja(template, **kwargs):
  return Template(template).render(**kwargs)


class Parser(BaseModel):
  parse: Callable[[str], Any]
  default: Any

  def __call__(self, text):
    try:
      return self.parse(text)
    except Exception as e:
      print(f"Failed to parse '{text}': {e}")
      return self.default
