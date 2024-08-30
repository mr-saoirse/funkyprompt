"""
A simple markdown structure agent spec
Agents are structured in markdown as follows

```
# Agent Name
Agent description here....

## Structured Response Types
### TypeA
[TABLE STRUCTURE: Field | Description | Type]

### TypeB
[TABLE STRUCTURE: Field | Description | Type]

## Functions
[Function Name A](http://api/endpoint)
[Function Name B](http://api/endpoint)
```

The function API endpoint is currently expected to expose openapi.json to describe the function and register it

"""
import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, HttpUrl

class FunctionLinks(BaseModel):
    url: HttpUrl | str
    description: Optional[str]
    name: Optional[str]
    
class SchemaTables(BaseModel):
    name: str
    rows: List[List[str]]
    
class MarkdownAgent(BaseModel):
    """
    A markdown agent can be parsed from block format or markdown format    
    """
    name: str
    description: Optional[str]
    """the """
    structured_response_types: List[SchemaTables] = []
    """the list of named functions"""
    function_links: List[FunctionLinks] = []
    """block data is the block element format e.g. editorjs"""
    block_data: Optional[List[dict]] = []
    """agent can be parsed from the particular markdown format(s)"""
    markdown: Optional[str] = None
    
    
    @classmethod
    def parse_markdown_to_agent_spec(cls, markdown: str ) -> "MarkdownAgent":
        """
        parse markdown to agent spec
        """
        name_match = re.search(r"^# (.+)", markdown, re.MULTILINE)
        name = name_match.group(1).strip() if name_match else ""

        waiting = False
        desc = []
        for s in markdown.splitlines():
            if s.strip() == f'# {name}':
                waiting = True
            elif waiting:
                if "# Structured Response Types" in s:
                    break
                desc.append(s)
                
        description = "\n".join(desc)

        tables_map = parse_markdown_tables(markdown)
        tables = []

        for table_name, rows in tables_map.items():
            tables.append(SchemaTables(name=table_name.strip(), rows=rows))

        function_links = []
        functions_section = re.search(r"## Available Functions\n\n(.+)", markdown, re.DOTALL)
        if functions_section:
            functions_content = functions_section.group(1).strip()
            function_matches = re.findall(r"#### (.+?)\n\n(.+?)\n\n_(https?://[^\s]+)_", functions_content, re.DOTALL)
            for match in function_matches:
                function_name = match[0].strip()
                function_description = match[1].strip()
                function_url = match[2].strip()
                function_links.append(FunctionLinks(name=function_name, description=function_description, url=function_url))

        return MarkdownAgent(name=name, description=description, structured_response_types=tables, function_links=function_links,markdown=markdown)

    
    @classmethod  
    def parse_editor_blocks_to_agent_spec(cls, blocks: List[Dict[str, Any]]) -> "MarkdownAgent":
        """
        block data from editor.js is parsed and can then be rendered as a div
        """
        name = None
        description = None
        tables = []
        links = []
        current_table_name = None
        for block in blocks:
            block_type = block.get('type')
            block_data = block.get('data', {})
            if block_type == 'header':
                level = block_data.get('level')
                text = block_data.get('text', '')
                if level == 1:
                    name = text
                elif level == 3:
                    current_table_name = text
                else:
                    current_table_name = None

            elif block_type == 'paragraph':
                description = block_data.get('text', '')

            elif block_type == 'table' and current_table_name:
                content = block_data.get('content', [])
                if content:
                    table_rows = content[1:]  # Exclude the title row
                    tables.append(SchemaTables(name=current_table_name, rows=table_rows))

            elif block_type == 'linkTool':
                link_data = block_data.get('link')
                meta = block_data.get('meta', {})
                title = meta.get('title', '')
                link = FunctionLinks(url=link_data, description=meta.get('description', ''), name=title)
                links.append(link)

        return cls(name=name, description=description, tables=tables, function_links=links, block_data=blocks)
    
    
    
def split_markdown_by_h1(markdown_content):
    """split markdown containing multiple agents split by H1 titles"""
    lines = markdown_content.splitlines()
    sections = {}
    current_section = ""
    last_section_name = None
    for line in lines:
        if line.startswith("# "): 
            last_section_name = line.lstrip('#').strip()
            if current_section.strip():
                sections[last_section_name] = current_section.strip()
                current_section = ""
            
        current_section += line + "\n"
    if current_section.strip():
        sections[last_section_name] = current_section.strip()
    return sections


def parse_markdown_tables(markdown, table_section_header='Structured Response Types'):
    """parse headed markdown tables"""
    d = {}
    activated = False
    counter = 0
    name = None
    for t in markdown.splitlines(): 
        if t.strip()[:3] == "## ":
            activated =  table_section_header in t
            if not activated:
                name = None
        if t.strip()[:4] == '### ':
            name = t.strip()[4:]
            counter = 0
            d[name] = []
        if activated and name and len(t.split('|'))> 1 :
            counter += 1
            if counter  > 2:
                d[name].append([c.strip() for c in t.split('|')])

    return d


def search_markdown_agents(search='http://0.0.0.0:4001/'):
    """
    given a web based directory of agents, read the search results and parse them into agent spec
    this is a convenience to read directly from the markdown format but more efficient to load in ways that dont require parsing
    """
    import requests
    import html2text
    h = html2text.HTML2Text()
    data = requests.get(search)
    md = h.handle(data.content.decode())
    return split_markdown_by_h1(md)