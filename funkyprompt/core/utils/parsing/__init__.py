from . web import scrape_text
import json
from ast import literal_eval
import re
def json_loads(s):
    """we will not work on these objects"""
    if not isinstance(s,str):
        return s
    try:
        return literal_eval(s)
    except:
        try:
            return json.loads(s)
        except:
            """list like {"A", "B", "C"} """
            pattern = r'"(.*?)"'
            l = list(re.findall(pattern, s))
            if len(l):
                return l
    
    return s


def parse_fenced_code_blocks(
    input_string, try_parse=True, select_type="json", first=True, on_error=None
):
    """
    extract code from fenced blocks - will try to parse into python dicts if option set
    json is assumed
    """
    try:
        input_string = input_string.replace("\n", "")
        pattern = r"```(.*?)```|~~~(.*?)~~~"
        matches = re.finditer(pattern, input_string, re.DOTALL)
        code_blocks = []
        for match in matches:
            code_block = match.group(1) if match.group(1) else match.group(2)
            # print(code_block)
            if code_block[: len(select_type)] == select_type:
                code_block = code_block[len(select_type) :]
                code_block.strip()
                if try_parse and select_type == "json":
                    code_block = json.loads(code_block)
                code_blocks.append(code_block)
        return code_blocks if not first and len(code_blocks) > 1 else code_blocks[0]
    except:
        if on_error:
            raise
        # raise
        # FAIL SILENT
        return [] if not first else {}