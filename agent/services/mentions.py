import re

MENTION_PATTERN = re.compile(r"@\[([^\]]+)\]\(([^)]+)\)|@(\S+)")


def parse_doc_names(message: str) -> list[str]:
    names: list[str] = []
    for match in MENTION_PATTERN.finditer(message):
        doc_name = match.group(2) or match.group(3)
        if doc_name and doc_name not in names:
            names.append(doc_name)
    return names
