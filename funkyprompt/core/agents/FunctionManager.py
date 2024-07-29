from funkyprompt.core import AbstractModel
from funkyprompt.core.agents import (
    CallingContext,
    MessageStack,
    LanguageModel,
    Plan,
)
from ..functions import Function
import typing


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

    def register(self, model: AbstractModel, include_function_search: bool = False):
        """register the functions of the model
        When registration is done, the functions are added to the stack of functions a runner can use

        Args:
            model (AbstractModel): a model that describes the resources and objectives of an agent
            include_function_search (bool, optional): this allows for dynamic function loading via a help command
        """
        for f in model.get_class_and_instance_methods():
            self.add_function(f)

    def add_function(self, f: typing.Callable | "Function"):
        """A callable function or Function type can be added to available functions.
        The callable is a python instance function that can be wrapped in a Function type
        or the Function can type can be added directly.
        Function types provide a reference to the actual callable function but also metadata.

        Args:
            f (typing.Callable|Function): the callable function or function descriptor to add to available functions
        """

        if not isinstance(f, Function) and callable(f):
            f = Function.from_callable(f)

        self[f.name] = f

        return f

    # may add tenacity retries for formatting
    def plan(self, question: str, context: CallingContext = None):
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
            question, model=Plan, language_model_provider=context.model
        )

        response: Plan = Plan.model_validate_json(
            lm_client(messages=messages, functions=functions, context=context)
        )

        return response

    def add_functions_by_name(self, function_names: str | typing.List[str]):
        """functions by named can be added to the runtime
        When plans or searches or run, the agent must ask to activate the functions.

        Activation means
        1. adding the function to the stack of callable functions in the language model context
        2. adding the function to the runtime so it can be called by the Runner

        Args:
            function_names (str | typing.List[str]): provide one or functions as a list
        """
        pass

    def reset_functions(self):
        """hard reset on what we know about"""
        self.functions = {}

    def search(self, question: str, limit: int = None, context: CallingContext = None):
        """search a deep function registry. The plan could be used to hold many functions in an in-memory/in-context registry.
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
