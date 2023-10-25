import re
import json


def parse_fenced_code_blocks(input_string, try_parse=True, select_type="python"):
    """
    extract code from fenced blocks - will try to parse into python dicts if option set
    """
    pattern = r"```(.*?)```|~~~(.*?)~~~"
    matches = re.finditer(pattern, input_string, re.DOTALL)
    code_blocks = []
    for match in matches:
        code_block = match.group(1) if match.group(1) else match.group(2)
        if code_block[: len(select_type)] == select_type:
            code_block = code_block[len(select_type) :]
        code_block.strip()
        if try_parse and select_type == "json":
            code_block = json.loads(code_block)
        code_blocks.append(code_block)
    return code_blocks


def split_string_with_quotes(string):
    pattern = r'"([^"]*)"'
    quoted_substrings = re.findall(pattern, string)
    placeholder = "<<<<>>>>"
    modified_string = re.sub(pattern, placeholder, string)
    split_parts = modified_string.split()
    result = []
    for part in split_parts:
        if placeholder in part:
            # Replace the placeholder with the quoted substring
            part = part.replace(placeholder, quoted_substrings.pop(0))
        result.append(part)
