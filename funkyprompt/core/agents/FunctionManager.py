"""IRONY - there are no functions only types as organizers of functions
- if you want to be functional, you can add your functions to a static type that holds and explains them
- this is better than having a large list of functions but also reduces to single function types 

For this reason, the type registry is the data behind the function manager 
"""

from funkyprompt.core import AbstractModel
from funkyprompt.core.agents import (
    CallingContext,
    MessageStack,
    LanguageModel,
    Plan,
)
from ..functions import Function
import typing
from funkyprompt.core.utils.openapi import Cache


def unqual(d):
    if  isinstance(d,list):
        d = {item:None for item in d}

    return d
class FunctionManager:
    """The function manager is used to plan and search over functions.
    It can also do the basic serialization faff to make functions in their various formats callable.
    The benefit of function managers are as follows;
    - formatting of available functions to send to LLM
    - searching and planning over functions
    - loading functions into the runtime so they can actually be called
    - generally supporting a dynamic function loading, planning and execution pattern
    """

    def __init__(self):
        """some options such as models or data stores to use for function loading"""
        self._functions = {}

    def __getitem__(self, key):
        return self._functions.get(key)

    def __setitem__(self, key, value):
        self._functions[key] = value


    def register(self, model: AbstractModel, qualify_function: bool=False)->typing.List[Function]:
        """register the functions of the model.
        When registration is done, the functions are added to the stack of functions a runner can use.
        we could also add type information but normally this is retrieved with new entities of that type anyway.
        We should consider a two-stage registration i.e. add the functions but dont necessarily make them visible until they are activated.
        But this only matters at scale when we have very many entities so we can postpone this for now (TODO: delayed function activate)

        Args:
            model (AbstractModel): a model that describes the resources and objectives of an agent
        """
        if not model:
            return
        added_functions = []
        for f in model.get_class_and_instance_methods():
            """if the functions need to be qualified by the model we can do that"""
            alias = None if not qualify_function else f"{model.get_model_namespace()}_{model.get_model_name()}_{f.__name}"
            added_functions.append(self.add_function(f,alias=alias))
        return added_functions

    def add_function(self, f: typing.Callable | "Function", alias:str=None):
        """A callable function or Function type can be added to available functions.
        The callable is a python instance function that can be wrapped in a Function type
        or the Function can type can be added directly.
        Function types provide a reference to the actual callable function but also metadata.

        Args:
            f (typing.Callable|Function): the callable function or function descriptor to add to available functions
        """

        if not isinstance(f, Function) and callable(f):
            f = Function.from_callable(f,alias=alias)

        self[f.name] = f

        return f

    # may add tenacity retries for formatting
    def plan(self, question: str, context: CallingContext = None, strict: bool = False):
        """Given a question, use the known functions to construct a function calling plan (DAG)

        Args:
            question (str): any prompt/question
            context (CallingContext, optional): calling context may be used e.g. to choose the underlying model
        """

        """determine the model from context or default"""
        from funkyprompt.services.models import language_model_client_from_context

        lm_client: LanguageModel = language_model_client_from_context(context)

        """there are no functions in this context as we want a direct response from context"""
        functions = None

        # example not just of response model but add functions/prompts with the model
        """we can structure the messages from the question and typed model"""
        messages = MessageStack(
            question=question, model=Plan, language_model_provider=context.model if context else None
        )
        
        if not context:
            context = CallingContext(prefer_json=True)
    

        response = lm_client(messages=messages, functions=functions, context=context)
        if strict:
            response: Plan = Plan.model_validate_json(response)

        return response

    def add_functions_by_name(self, function_names: dict):
        """functions loaded by name can be added to the runtime. When plans or searches or run, the agent must ask to activate the functions.
       
        Activation means
        1. adding the function to the stack of callable functions in the language model context
        2. adding the function to the runtime so it can be called by the Runner

        Args:
            function_names (dict): provide a map of the function and the entity it belongs to. if the function is prefixed with a verb such as get or post, please retain it in the name
        """
        from funkyprompt.entities import load_entities
        
        function_names = unqual(function_names)
        
        """this will become smarter and faster"""
        entities = load_entities()
        entities = {e.get_model_fullname():e for e in entities}
 
        for f, entity_name in function_names.items():
            #temp hack - we want to have multiple ways to add functions - this is a universal api naming thing
            if ":" in f: ##api types - not sure how to distinguish in future yet
                F = Cache.resolve_endpoint(f)
                F = Function.from_openapi_endpoint(F)
                self.add_function(F)
            else: #entity function
                """remove any qualification"""
                if not entity_name:
                    entity_name =  '.'.join(f.split('.')[:-1])
    
                alias = str(f).replace('.','_')
                f = f.replace(f"{entity_name}", '').lstrip('_').lstrip('.')
                
                entity = entities.get(entity_name)
                if entity is None:
                    raise Exception(f"The entity {entity_name} does not exist or cannot be loaded from {entities}")
                self.add_function(getattr(entity,f), alias=alias)
                print('added', alias)
            
        """only return the ones we add successfully"""
        return function_names

    def reset_functions(self):
        """hard reset on what we know about"""
        self.functions = {}

    def search(self, question: str, limit: int = None, context: CallingContext = None):
        """search a deep function registry (API). The plan could be used to hold many functions in an in-memory/in-context registry.
        This as cost implications as the model must keep all functions in the context.
        On the other hand, a vector search can load functions that might be interesting but it may not be accurate or optimal

        Args:
            question (str): a query/prompt to search functions (using a vector search over function embeddings)
            limit: (int): a limit of functions returned for consideration
            context (CallingContext, optional): context may provide options
        """
        from funkyprompt.services import entity_store

        return entity_store(Function).ask(question)

    @property
    def functions(self) -> typing.Dict[str, Function]:
        """provides a map of functions"""
        return self._functions

""""""