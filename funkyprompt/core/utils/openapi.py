"""
Parsing tools for openapi schema to create a function representation (callable)
"""
import requests
import typing
from urllib.parse import urlparse
from pydantic import BaseModel
import os

DEFAULT_API_HOME = os.environ.get('FP_API')
 
def _format_parameters(d):
    d.update(d["schema"])
    d["description"] = d.get("description", d.get("title", ""))
    # TODO we can pop the required from here and put them into a required list up one level
    return {k: v for k, v in d.items() if k in ["description", "type", 'name']}

class ApiCache:
    def __init__(self, apis:dict=None):
        """
        the idea here is to add API roots and their openapijson and keys
        it can be assumed there is one default domain and API key
        the default API will have a single bearer token that can be used and https:// scheme is assumed for api
        """
        
        """we unmap any domain api specs"""
        
        self._cache_json = {
           DEFAULT_API_HOME : requests.get(f'https://{DEFAULT_API_HOME}/openapi.json').json()
        }
        self._token_keys = {
           DEFAULT_API_HOME :  'FP_API_KEY'
        }
        
    @staticmethod
    def get_function_by_id(spec:dict, oid:str):
        """"""
        for key, value in spec['paths'].items():
            for verb, data in value.items():
                if data.get('operationId') == oid:
                    return key, dict(value)
        
    @staticmethod
    def get_function_by_name_and_verb(spec: dict, name:str, verb:str=None):
        """a function endpoint name can be used and the verb should be added to qualify (assumed get)
        as a short hand, we may allow the format verb:/endpoint 
        """
        if ':' in name:
            verb = name.split(':')[0]
            name = name.split(':')[-1]
            """force prefix just in case"""
            name = f"/{name.lstrip('/')}"
            
        verb = verb or 'get'
        for key, value in spec['paths'].items():
            for _verb, data in value.items():
                if key == name and _verb == verb:
                    return key, dict(value)
        
    
    def resolve_endpoint(self, endpoint_uri:str, api_root:str=None)-> "ApiEndpoint":
        """
        provide a more convenient format if the domain is known based on verbs and endpoints
        domain prefix should be schema://domain.com/prefix where the api lives. prefix can be blank if the api is at the root - it should be the openapi.json home
        """
        
        #resolve default domain for the system
        try:
            api_root = api_root or f"https://{DEFAULT_API_HOME}"
            parsed_uri = urlparse(api_root)
            domain_key = api_root.replace(f"{parsed_uri.scheme}://",'')
            openapi_json = self._cache_json[domain_key]      
            token_env_key = self._token_keys[domain_key]
            """if we know the endpoint, it includes the prefix"""
            api_root = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
            
            endpoint, function_spec = self.get_function_by_name_and_verb(openapi_json, endpoint_uri)
            for verb, data in function_spec.items():
                """we only care about one if id is trusted"""
                parameters = [_format_parameters(p) for p in data.get('parameters',[])]
                operation_id = data.get('operation_id')
                """construct some sort of uri for now - we dont need it for calling"""
                return ApiEndpoint(uri=f"{api_root}/{verb}/{endpoint.lstrip('/')}", 
                        endpoint=endpoint,
                        api_root=api_root, 
                        operation_id=operation_id, 
                        #fragment=function_spec, 
                        verb=verb, 
                        #convention - could add verb and or could try to make universally unique but maybe the runner should alias
                        name=data.get('summary','NO NAME').lower().replace(' ', '_'),
                        token_env_key=token_env_key,
                        parameters=parameters,
                        description = data.get('description',''))
        except:
            import traceback
            from funkyprompt.core.utils import logger
            logger.warning(traceback.format_exc())
            raise
            
    def resolve(self, uri)-> "ApiEndpoint":
        """
        """
  
        uri_prefix, operation_id = uri.rsplit('/', 1)  
        parsed_uri = urlparse(uri_prefix)
        domain = parsed_uri.netloc.rstrip('/')  
        """not sure what is a general convention for this"""
        path_root = parsed_uri.path.lstrip('/').split('/')[0]     
        prefix = f"{domain}/{path_root}"
        openapi_json = self._cache_json[prefix]      
        token_env_key = self._token_keys[prefix]
        
        endpoint, function_spec = self.get_function_by_id(openapi_json,operation_id)
         
        for verb, data in function_spec.items():
            """we only care about one if id is trusted"""
            parameters = [_format_parameters(p) for p in data.get('parameters',[])]
       
            return ApiEndpoint(uri=uri, 
                    endpoint=endpoint,
                    api_root=f"{parsed_uri.scheme}://{domain}", 
                    operation_id=operation_id, 
                    #fragment=function_spec, 
                    verb=verb, 
                    #convention - could add verb and or could try to make universally unique but maybe the runner should alias
                    name=data.get('summary','NO NAME').lower().replace(' ', '_'),
                    token_env_key=token_env_key,
                    parameters=parameters,
                    description = data.get('description',''))
        
Cache = ApiCache()

class ApiEndpoint(BaseModel):
    """we use these to resolve to something callable"""
    uri:  typing.Optional[str]
    endpoint:  typing.Optional[str]
    operation_id:  typing.Optional[str]
    api_root: typing.Optional[str]
    token_env_key: typing.Optional[str] = None
    fragment: typing.Optional[dict] = None
    
    """a local caller would need to know these things"""
    
    name: str
    description:str
    parameters: typing.List[dict]
    verb: str
     
    @classmethod
    def from_endpoint(cls, uri):
        """
        """
        return Cache.resolve(uri)
    
    def _call__(self, *args, data=None, return_raw_response:bool=False, **kwargs):
        return self.invoke(*args, data=data, return_raw_response=return_raw_response, **kwargs)
    
    def invoke(self, *args, data=None, return_raw_response:bool=False, **kwargs):
        """call the endpoint assuming json output for now"""
        
        """the response does not have to be json - just for testing"""
        
        headers = { } #"Content-type": "application/json"
        if self.token_env_key:
            headers["Authorization"] =  f"Bearer {os.environ.get(self.token_env_key)}"
        
        f = getattr(requests, self.verb)

        """rewrite the url with the kwargs"""
        endpoint = self.endpoint.format_map(kwargs)
        endpoint = f"{self.api_root.rstrip('/')}/{endpoint.lstrip('/')}"

        """f is verbified - we just need the endpoint. data is optional, kwargs are used properly"""
        response = f(
            endpoint,
            headers=headers,
            params=kwargs,
            data=data,
        )

        try:
            response.raise_for_status()

            if return_raw_response:
                return response
        
            """otherwise we try to be clever"""
            t = response.headers.get('Content-Type')
            if 'json' in t:
                return  response.json()
            if t[:5] == 'image':
                from PIL import Image
                from io import BytesIO
                return Image.open(BytesIO(response.content))
            return response.content
                        
            
        except Exception as ex:
            return {
                "data": response.json(),
                "type": response.headers.get("Content-Type"),
                "status": response.status_code,
                "requested_endpoint": endpoint,
                "info": self.model_dump(),
                "exception" : repr(ex)
            }



