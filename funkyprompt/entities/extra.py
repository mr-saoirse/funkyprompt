from funkyprompt.core import AbstractContentModel
from funkyprompt.core.AbstractModel import add_graph_paths

from funkyprompt.core.utils.parsing.web import get_soup
url='https://paulgraham.com/'
local_url='/Users/sirsh/Downloads/Essays.html'

class Grahams(AbstractContentModel):
    """
    Using this as an opinionated page parse example
    This just extends abstract entity but it parses content in a particular way
    
    """
    class Config:
        name: str = 'grahams'
        namespace:str = 'public'
        description: str = f"""Your job is to do a three part analysis following the Guidelines. 
The first part is via a vector search, the second is via a key value lookup on documents and the third step is via a second vector search.
Please provide sectioned response for each of these. There is an `advise_next_steps` function that you can call at each stage to get guidance. you must use it!!

You can search a dataset with essays, chunked into fragments with links between them.
Each hyperlink is an entity you can lookup - for example if there is a part of an essay  `Some Title - Part 1` you can look this up with an entity search. It is convenient to lookup multiple at a time.
You can also lookup graph paths to find related material.

## Required stages

stage 1: Your job is to do a multi-hop or deep dive on the user's question. You should probe with an initial vector search on multiple questions to get some context.
stage 2: You should then use this to plan your argument. You will retrieve some content that provides context as well as hyperlinks to other content.
stage 3: You should use vector searches to ask more questions AND you should use entity lookup to check out the linked documents.

  
## Guidelines

1. Be comprehensive in your analysis and provide a rich answer touching on ALL of the users points and questions. 
2. To prove you have done this, you should **add entity references** AND you should quote the author in quotations. 
3. You should state if the data were found on the first or subsequent vector search or by entity lookup.
4. You must use all modes of search to answer the question properly. 
5. Do not ask the user for permission to use functions and tools to do deep searches.


    """
    
    
    @classmethod
    def advise_next_steps(cls, stage: int, context:str=None):
        """
        If you pass in the stage, i will remind you what to do next
        
        **Args**
            stage: (int) specify what stage you are at 1,2 or 3
            context: provide a comment about what you know and dont know at this stage (briefly)
        """
        print(f"{stage=}, {context=}")
        if stage == 1:
            return {'next steps': "You should ask multiple questions to do your initial vector search" }
        if stage == 2:
            return {'next steps': "You should extract the other pages and linked graph paths to do lookup entity on key - this will provide more content for you to use" }
        if stage == 3:
            return {'next steps': "You should know know do a specific vector search using the discovered information and the remaining details the user is curious about" }
        
        
          
    @staticmethod
    def _get_essays():
        """
        iterate over the essays
        """
        
        
        for data in Grahams.__extract_links(get_soup(url=local_url)):
            yield data
        
    @staticmethod
    def __extract_links(soup, ):
        """
        load the page and make it markdown chunks with links
        produces a collection of one or more markdown chunks
        if there are more than one, its a title page followed by segments
        """
        links = {}
        for a_tag in soup.find_all('a', href=True):
            if a_tag.text != '' and 'http' not in a_tag['href'] and 'rss.html' not in a_tag['href']:
                links[a_tag['href']] = a_tag.text
 
        print(links)
        
        for link, title in links.items():
            """visit and parse the html"""
            link = f"{url}/{link}"
            content = get_soup(link)
            data =  Grahams.__html_to_markdown(title , str(content))
            """Now we can create entries from this"""
            """we always have a first page and sometimes have parts"""
            yield Grahams(name=title, content=data[0], graph_paths=add_graph_paths(data[0]))
            if len(data) > 0:
                for i, record in enumerate(data[1:]):
                    yield Grahams(name=f"{title} - Part {i+1}", 
                                  content=record, 
                                  graph_paths=add_graph_paths(record))
            
            
        
    @staticmethod
    def __html_to_markdown(title, html_content):
        """
        get markdown chunks and provide some link structure
        """
        import html2text
        def split_text_by_newlines(text, max_chunk_size=5000):
            lines = text.split('\n')
            chunks = []
            current_chunk = []
            current_chunk_size = 0
            for line in lines:
                line_size = len(line) + 1 
                if current_chunk_size + line_size > max_chunk_size:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_chunk_size = 0
                current_chunk.append(line)
                current_chunk_size += line_size
            if current_chunk:
                chunks.append('\n'.join(current_chunk))

            return chunks

        def generate_markdown_links(title, num_parts, headless=False):
            markdown = f"# {title}\n\n" if not headless else ""
            for i in range(1, num_parts + 1):
                markdown += f" - [{title} - Part {i}](#link-part-{i})\n"
            return markdown

        """generates markdown chunks no bigger than 5000 characters"""
        converter = html2text.HTML2Text()
        converter.ignore_links = False  
        converter.ignore_images = True 
        converter.ignore_emphasis = False 
        #remove the translation links at the end of the grahams
        markdown = converter.handle(html_content)#.split('\n--- ')[0]
        all_ =  split_text_by_newlines(markdown)
        n = len(all_)
        title_page = generate_markdown_links(title, n)

        if n == 1:
            return markdown
        
        for i in range(len(all_)):
            all_[i] =  f'### {title} - part {i+1}\n\n' + all_[i] + f"\n\n### Links to other parts\n {generate_markdown_links(title, n, headless=True)}"

        return [title_page] + all_