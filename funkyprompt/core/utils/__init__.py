from . import dates, env
from loguru import logger
import os
from glob import glob
import json
from ast import literal_eval
import traceback

os.environ["LOGURU_LEVEL"] = "DEBUG"

def ingest_files(directory, name, namespace='public',provider=None):
    """
    a very lazy file ingester
    """
    from funkyprompt.core import AbstractContentModel
    from tqdm import tqdm
    from funkyprompt.services import entity_store
    
    M = AbstractContentModel.create_model(name=name, namespace=namespace)
    try:
        M._register()
    except:
        pass
    provider = provider or entity_store
    store = provider(M)
    
    records= []
    for file in tqdm(glob(f"{directory.rstrip('/')}/*.*")):
        with open(file) as f:
            data = f.read()
            """todo this is a temp hack because we have not thought out how we want to deal with entity names for graphs"""
            file = file.split('/')[-1].replace(' ','').replace(',','').split('.')[0]
            
            if len(data):
                records.append(M(name=file, content=data))
    store.update_records(records)

    

def help(question:str, raw_search:bool=False, provider=None):
    """
    ask a question about the codebase
    """
    from funkyprompt.services.models import language_model_client_from_context
    from funkyprompt.services import entity_store
    from funkyprompt.core import AbstractContentModel
    from funkyprompt.core.agents import CallingContext, LanguageModel, MessageStack
    
    lm_client: LanguageModel = language_model_client_from_context(None)
    
    class CodebaseHelpModel(AbstractContentModel):
        class Config:
            name: str = 'codebase'
            namespace: str = 'core'
            description: str = f"Please answer questions about the funkyprompt codebase using the search results you are provided"
            
    provider = provider or entity_store
    result =  provider(CodebaseHelpModel).ask(question)
    
    if raw_search:
        return result
    
    messages= MessageStack.from_q_and_a(question, result)
    
    #return messages

    response = lm_client(messages=messages, functions=None, context=None)
       
    return response

def index_codebase(include_api_json=True, provider = None):
    """
    add all the code into a vector store in a crude sort of way
    """
    
    from glob import glob
    from funkyprompt.services import entity_store
    from funkyprompt.core import AbstractContentModel
    from funkyprompt.core.utils.env import get_repo_root

    provider = provider or entity_store
    def split_string_into_chunks(string, chunk_size=20000):
        """simple chunker"""
        return [string[i : i + chunk_size] for i in range(0, len(string), chunk_size)]

    R = get_repo_root()
    """by using the abstract model which is an entity we are saying the name is unique when adding records
       think about this - its also a problem that the name can be a path or anything
       but the graph node expect some reasonably friendly names without funny characters
       
       TODO: decide what to do and make graph names regex safe
       Another factor is if we want to default to vector search / tabular search or allow entities
       In this case the entity model would not make sense so maybe the right superclass helps here
    """
    M = AbstractContentModel.create_model(name='codebase', namespace='core')
    
    py_files = glob(f"{R}/**/*.py", recursive=True)
    readme_files = glob(f"{R}/**/*.md", recursive=True)
    yaml_files = glob(f"{R}/**/*.yaml", recursive=True)
    records = []

    for file_path in yaml_files:
        with open(file_path, "r") as f:
            f = f.read()
            f = f"""
            ```yaml
            # {file_path}
            {f}
            ```"""

            records.append(M(name=file_path, content=f))
    # Print the list of .py files
    for file_path in py_files:
        with open(file_path, "r") as f:
            f = f.read()
            for i, f in enumerate(split_string_into_chunks(f)):
                f = f"""
                This is a python file
                
                ```python
                #{file_path}
                {f}
                ```"""
                name = file_path if i == 0 else f"{file_path}_{i}"
                records.append(M(name=name, content=f))

    for file_path in readme_files:
        with open(file_path, "r") as f:
            f = f.read()
            records.append(M(name=file_path, content=f))

    hidden_files = []
    for root, dirs, files in os.walk(R):
        # Filter out files that start with a dot
        hidden_files.extend(
            [os.path.join(root, f) for f in files if f.startswith(".") and ".md" in f]
        )

    for file_path in hidden_files:
        with open(file_path, "r") as f:
            f = f.read()
            records.append(M(name=file_path, content=f))

    """
    add records to the store 
    """

    provider(M).update_records(records)
    
    logger.info(f'Done - added {len(records)} records')

     
def coerce_list(o):
    """simple coerce"""
    if isinstance(o,list):
        return o
    if isinstance(o,str):
        try:
            return literal_eval(o)
        except:
            return o.split(',')
        
    raise ValueError(o)
        
def coerce_json(o):
    """simple coerce"""
    if isinstance(o,dict):
        return o
    if isinstance(o,str):
        try:
            return json.loads(o)
        except:
            return literal_eval(o)
        
    raise ValueError(f"{o} must be a string or parseable to json but got {type(o)} that we can not parse")
            