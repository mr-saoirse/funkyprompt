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
import base64
import hashlib
from bs4 import BeautifulSoup
import html2text
import os
import markdown
import requests

class FunctionLinks(BaseModel):
    url: HttpUrl | str
    description: Optional[str]
    name: Optional[str]
    
class SchemaTables(BaseModel):
    name: str
    rows: List[List[str]]
    
    def to_json_schema(cls):
        """return something like a json schema but we may use python type annotations in some case for now for types"""
        fields = {}
        for row in cls.rows:
            fields[row[1]] = {
                'type': row[2],
                'description': row[3]
            }
        return {'entity': cls.name, 'fields':  fields}
    
    
def unfence_markdown(md_text: str) -> str:
    """
    Remove fenced code blocks (``` or ~~~) from markdown text or returns the text as is
    Args:
        md_text (str): Markdown text containing fenced code blocks.
    Returns:
        str: Markdown text without the fence markers.
    """
    pattern = r'```[\w-]*\n([\s\S]+?)\n```'
    
    unfenced_text = "\n".join(re.findall(pattern, md_text.lstrip()))
    
    return unfenced_text or md_text

class MarkdownAgent(BaseModel):
    """
    A markdown agent can be parsed from block format or markdown format    
    there are certain generic extensions we can add related to crud (upsert, search, get|status, graph_paths) - they may depend on choosing a base type
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
    def build(cls, goals:str, openapi_spec_uri:str):
        """"""
        import funkyprompt
        
        spec = requests.get(openapi_spec_uri)
       
        q = f"""
        I will supply you with an openapi json for an API {openapi_spec_uri} and I will provide a list of tasks id like to be able to perform. 
        Please provide the links essential functions that can be used in a special format but only add functions that are absolutely necessary to the task and explain WHY it is used. 
        If the user asks for one specific function, only add one specific function. Do not guess that other functions might be useful.
        Construct a unique url of the form [verb:endpoint)](https://domain.com/prefix/docs#/[Tag]/operationid) in a bulleted list for the essential functions. 
        - You must use the format verb separated by colon and the name since we use this later to map the function.
        - If the user provides a literal name, use it in place of the [Name Here] below, exactly as they provide it otherwise choose a suitable name
        
        The overall output structure is shown below. Add an agent name and description, structure output types in tables and links for each of the functions used
        Do not add any additional commentary.

        ---------
        ### API OpenAPI.json spec
        ```json
        {spec.json()}
        ```

        ### Goals
        ```
        {goals}
        ```
        ---------


        # [Name Here] (based on what the user asks to call the agent or entity. Do not keep `entity` or `agent` or `manager` in the name as its assumed)
        agent description here... detail description of what the agent can do. Please write it in the format of a prompt telling the large language model what to do

        ## Structured Response Types
        ### Type name
        output a markdown table(s) format showing the field name, types and descriptions for anything that describes the core entity being discussed. Omit if ensure of what the core entity is.
        When creating types please use Python type annotations such as `Optional[List[str]]` etc.
        For example if the core purpose of the agent is to describe some entity, you could create a table showing name, description, and other attributes of the entity. If the agent is generic and not related to an entity you can omit this

        ## Available Functions
        - list of essential functions (only) generated as url along with a description of what the function is essential to the task e.g. - [name](url) : how to use it for the given task
        ```

        """ 

        
        return unfence_markdown(funkyprompt.ask(q))

    
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
        functions_section = re.search(r"## Available Functions\n(.+)", markdown, re.DOTALL)
        if functions_section:
            functions_content = functions_section.group(1).strip()
            function_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)\s*:\s*(.+)', functions_content)
            for function_name, function_url, function_description in function_matches:
                function_links.append(FunctionLinks(name=function_name, description=function_description.lstrip(), url=function_url))

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
    last_section_name = None
    for line in lines:
        """only one header is allowed in this simple scheme"""
        if line.startswith("# "): 
            last_section_name = line.lstrip('#').strip()
            sections[last_section_name] = line + '\n'
        else:
            sections[last_section_name] += line + '\n'
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


def search_markdown_agents(search='http://0.0.0.0:4001/', preview:bool = None):
    """
    given a web based directory of agents, read the search results and parse them into agent spec
    this is a convenience to read directly from the markdown format but more efficient to load in ways that dont require parsing
    """
    import requests
    import html2text
    h = html2text.HTML2Text()
    data = requests.get(search)
    md = h.handle(data.content.decode())
    if preview:
        return md
    return split_markdown_by_h1(md)


def process_html(id:str, html_content:str, output_dir:str="./data/pages"):
    """
    given html content, convert it to markdown applying our conventions for documents
    - extract base 64 images and replace them with images with hash file content
    - verify any / links 
    - clean out system elements
    
    Args:
        id: a document id
        html_content: the content from the editor
        output_dir where to save files and images, actually we will store in a database
    """

    
    soup = BeautifulSoup(html_content, 'html.parser')
    base64_pattern = re.compile(r'data:image/(?P<format>png|jpeg|jpg|gif);base64,(?P<data>[^"]+)')
    
    for img_tag in soup.find_all('img', src=True):
        src = img_tag['src']
        match = base64_pattern.match(src)
        if match:
            img_format = match.group('format')
            img_data = match.group('data')
            img_bytes = base64.b64decode(img_data)

            md5_hash = hashlib.md5(img_bytes).hexdigest()
            file_extension = img_format if img_format in ['png', 'jpeg', 'jpg', 'gif'] else 'png'
            file_name = f"{md5_hash}.{file_extension}"
            
            """url locally to resource but we can rewrite this later"""
            file_path = os.path.join(output_dir, file_name)
            
            """could check if it exists already"""
            with open(file_path, 'wb') as img_file:
                img_file.write(img_bytes)
    
            img_tag['src'] = file_path.lstrip('.')
            #consider if we need to do anything for magic links /
    
    data = html2text.HTML2Text().handle(str(soup))    
    
    with open(f"{output_dir}/{id}.md", 'w') as f:
        f.write(data)
        
    return data

def extract_local_ref_links(markdown_text:str):
    """
    this is used to extra local relative links which are used in funkyprompt as tags/backlinks 
    """
    link_pattern = re.compile(r'\[([^\]]+)\]\((?!http|https|www)([^)]+)\)')
    matches = link_pattern.findall(markdown_text)
    lset = set()
    for match in matches:
        """we can categorize them """
        _ = match[0]  
        link_url = match[1]  
        lset |= {link_url}
    return lset

def markdown_to_html(html:str, add_root_div: bool = True, **options):
    """
    produce a markdown document in a parent div container
    """
    
    return f"<div>{markdown.markdown(html)}</div>"