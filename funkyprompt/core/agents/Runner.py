"""
The runner can call the LLM in a loop and manage the stack of messages and functions
Function calling and streaming is handled
Open telemetry is used to publish metrics which a collector could manage
If this goes above 200 lines of codes we have failed!
"""

from funkyprompt.core import AbstractModel
from funkyprompt.services.models import language_model_client_from_context
from funkyprompt.core import utils
from funkyprompt.core.agents import (
    CallingContext,
    DefaultAgentCore,
    LanguageModel,
)

from funkyprompt.core import ConversationModel
from funkyprompt.services import entity_store
from . import MessageStack
from . import FunctionCall, FunctionManager, Function
import typing
import traceback

class Runner:
    """Runners are simple objects that provide the interface between types and language models
    The message setup is the only function that plays with natural language.
    While almost all of the "prompting" is pushed out to types and functions,
    This setup function is the one function you can play with to make sure the comms are right with the LLM.
    For example it is here we inject plans and questions and other hints for how to run things.
    But by design, the critical guidance should be abstracted by Types and Functions.
    Beyond this, the rest is routine;
    - import type metadata and functions from the model which controls most everything
    - run an executor loop sending context to the LLM
    - implement the invocation and message setup methods to manage the function and message stack

    Under the hood the function manager handles actual function loading and searching
    """

    def __init__(self, model: AbstractModel = None):
        """
        A model is passed in or the default is used
        The reason why this is passed in is to supply a minimal set of functions
        If the model has no functions simple Q&A can still be exchanged with LLMs.
        More general the model can provide a structured response format.
        This is powerful because the model is a Pydantic annotated type but can be realized as a json response
        """
        self.model = model or DefaultAgentCore()
        self._function_manager = FunctionManager()
        self.initialize()
        
    def __repr__(self):
        return f"Runner({(self.model.get_model_fullname())})"

    def initialize(self):
        """register the functions and other metadata from the model"""

        self._context = None
        """register the model's functions which can include function search"""
        self._function_manager.register(self.model)
        """the basic bootstrapping means asking for help, entities(types) or functions"""
        self._function_manager.add_function(self.lookup_entity)
        self._function_manager.add_function(self.help)
        self._function_manager.add_function(self.activate_functions_by_name)
        """more complex things will happen from here when we traverse what comes back"""
    
    def activate_functions_by_name(self, function_names: str|typing.List[str]):
        """
        If you encounter a full name of a function, you can activate it here.
        Once you activate it, it will be ready for use. 
        Supply one or more function names

        Args:
            function_names: one or more function names
        """
        
        from funkyprompt.entities.nodes import Project
        
        self._function_manager.add_function(Project.upsert_entity)
        
        """the function manage can activate the functions"""
        
        return {
            'status': f"Re: the functions {function_names}, now ready for use. please go ahead and invoke."
        }
        
    def lookup_entity(self, key:str):
        """lookup entity by one or more keys
        
        Args:
            key: one or more keys to use to lookup the entity or entities 
        """
        
        from funkyprompt.services import entity_store

        """todo test different parameter inputs e.g. comma separated"""
        entities =  entity_store(self.model).get_nodes_by_name(key)
        
        """register entity functions if needed and wait for the agent to ask to activate them
           we are not being efficient here by checking if we already have this entity (TODO:)
        """
        for e in entities:
            self._function_manager.register(e)
        
        """
        when we return the entities, its better to return them with metadata 
        (as opposed to just fetching the record data only)
        """
        return AbstractModel.describe_models(entities)

    def help(self, questions: str | typing.List[str]):
        """if you are stuck ask for help with very detailed questions to help the planner find resources for you.

        Args:
            question (str): provide detailed questions to guide the planner
        """

        utils.logger.debug(f"help/{questions=}")

        try:
            plan = self._function_manager.plan(questions)
        except:
            return {"message": "planning pending - i suggest you use world knowledge"}

        """describe the plan context e.g. its a plan but you need to request the functions and do the thing -> update message stack"""

        return plan

    def invoke(self, function_call: FunctionCall):
        """Invoke function(s) and parse results into messages

        Args:
            function_call (FunctionCall): the payload send from an LLM to call a function
        """
        f = self._function_manager[function_call.name]
        
        if not f:
            message = f"attempting to load function {function_call.name} which is not activated - please activate it"
            utils.logger.warning(message)
            data = MessageStack.format_function_response_error(
                function_call.name, ValueError(message), self._context
            )
        else:

            try:
                """try call the function - assumes its some sort of json thing that comes back"""
                data = f(**function_call.arguments) or {}
                data = MessageStack.format_function_response_data(
                    function_call.name, data, self._context
                )
                """if there is an error, how you format the message matters - some generic ones are added
                its important to make sure the format coincides with the language model being used in context
                """
            except TypeError as tex:
                utils.logger.warning(f"Error calling function {tex}")
                data = MessageStack.format_function_response_type_error(
                    function_call.name, tex, self._context
                )
            except Exception as ex:
                utils.logger.warning(f"Error calling function {traceback.format_exc()}")
                data = MessageStack.format_function_response_error(
                    function_call.name, ex, self._context
                )

        """update messages with data if we can or add error messages to notify the language model"""
        self.messages.add(data)

    @property
    def functions(self) -> typing.Dict[str, Function]:
        """provide access to the function manager's functions"""
        return self._function_manager.functions

    def run(self, question: str, context: CallingContext, limit: int = None):
        """
        Ask a question to kick of the agent loop
        """

        """setup all the bits before running the loop"""
        lm_client: LanguageModel = language_model_client_from_context(context)
        self._context = context
        self.messages = MessageStack(
            model=self.model,
            question=question,
            current_date=utils.dates.now(),
            function_names=self.functions.keys(),
            language_model_provider=context.model,
        )

        """run the agent loop to completion"""
        for _ in range(limit or context.max_iterations):
            response = None
            function_descriptions = [f.to_json_spec() for f in self.functions.values()]
            """call the model with messages and function + our system context"""
            response = lm_client(
                messages=self.messages.model_dump(),
                context=context,
                functions=function_descriptions,
            )
            if isinstance(response, FunctionCall):
                """call one or more functions and update messages"""
                self.invoke(response)
                continue
            if response is not None:
                # marks the fact that we have unfinished business
                break

        """fire telemetry"""

        """log questions to store unless disabled"""

        self.dump(question, response, context)
        
        """queue entity extraction and consider observer
           response = observer(response)
        """

        return response

    def dump(self, questions: str, response: str, context: CallingContext):
        """dumps the messages and context to stores
        if the session is a typed objective this is updated in a slowly changing dimension
        generally audit all transactions unless disabled
        """
        from uuid import uuid4

        default_id = str(uuid4())

        """for any pydantic response"""
        if hasattr(response, "model_dump_json"):
            """dumpy state"""
            response = response.model_dump_json()

        entity_store(ConversationModel).update_records(
            ConversationModel(
                id=default_id,
                user_id=context.username or "system",
                objective_node_id=context.session_id,
                content={"question": questions, "response": response},
            )
        )


    def __call__(
        self, question: str, context: CallingContext = None, limit: int = None
    ):
        """
        Ask a question to kick of the agent loop
        """
        context = context or CallingContext()
        return self.run(question, context, limit=limit)

    def explain(cls, data:dict|typing.List[dict]):
        """
        it is often convenient to run the runner directly on data which uses this standard recipe
        """
        
        import json 
        P = f"please explain the following data according to your guidelines - ```{json.dumps(data)}``` and respond in a json format - use the model provided"
        return cls(P)
        
"""
#TODO: general test e.g. call a function with limit=1, it doesnt loop and confirm the result and therefore we might not get behaviour expected
generally we want to ensure consistent output    

the response should always be JSON but revert to a simple form {response=}
"""
