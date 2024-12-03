import re
from typing import Any


def add_prefix(string, prefix):
    if not string.startswith(prefix):
        string = prefix + string
    return string


def str_to_filters(str_filter: str | None) -> dict[str, Any]:
    if not str_filter:
        return {}

    conditions = re.split(r"\s+and\s+", str_filter)

    filters = {}
    for condition in conditions:
        # Use regex to match key, operator, and value
        match = re.match(r'(\w+)\s+(eq)\s+"([^"]*)"', condition)
        if match:
            key, op, value = match.groups()
            if op == "eq" and key != "workspace_id":
                filters[key] = value

    return filters


def dict_to_md(data: dict[str, Any]) -> str:
    md_lines = []
    for key, value in data.items():
        md_lines.append(f"**{key}**: {value}")
    return "\n".join(md_lines)
