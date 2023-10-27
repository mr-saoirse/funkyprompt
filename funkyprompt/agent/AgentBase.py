from typing import Any
import openai
from funkyprompt import logger
import typing
import json
from funkyprompt.io.tools.fs import save_file_collection
from funkyprompt.ops import examples as built_in_modules
from funkyprompt.ops.utils.inspector import (
    describe_function,
    list_function_signatures,
    FunctionDescription,
)

DEFAULT_MODEL = "gpt-4"


class AgentBase:
    """
    we are completely functional except for how the interpreter works
    some functions such as checking session history are still functional
    examples of things this should be able to do
    - Look for or take in functions and answer any question with no extra prompting and nudging. Examples based on ops we have
        - A special case is generating types and saving them
    - we should be able to run a planning prompt where the agent switches into saying what it would do e.g. rating functions, graph building, planning
    - we should be able to construct complex execution flows e.g.
      - parallel function calls
      - saving compiled new functions i.e. motifs that are often used
      - asking the user for more input
      - evolution of specialists

    All of this is made possible by making sure the agent trusts the details in the functions and follows the plan and returns the right formats
    The return format can be itself a function e.g. save files or report (structured) answer

    If it turns out we need to branch into specialist agents we can do so by overriding the default prompt but we are trying to avoid that on principle
    """

    #          You are evaluated on your ability to properly nest objects and name parameters when calling functions.

    PLAN = """  You are an intelligent entity that uses the supplied functions to answer questions.
                
                1. When using functions, you MUST pass all required arguments with their proper names
                2. The function descriptions might have some Pydantic object types, which will be described in the function descriptions, allowing you to use nested types as parameters. 
                3. Note that if the question is unambiguous and the answer to the question is a well-known fact, you can answer it directly.
                4. Lets use all functions that we can until we find the answer
                """

    def __init__(cls, modules, **kwargs):
        """
        modules are used to inspect functions including functions that do deep searches of other modules and data

        """
        # add function revision and pruning as an option
        cls._built_in_functions = [describe_function(save_file_collection)]
        cls._built_in_functions += [describe_function(cls.available_function_search)]

    def invoke(cls, fn: typing.Callable, args: typing.Union[str, dict]):
        """
        here we parse and audit stuff using Pydantic types
        """

        args = json.loads(args) if isinstance(args, str) else args

        # the LLM should give us this context but we remove it from the function call
        for sys_field in ["__confidence__", "__parameter_choices__"]:
            if sys_field in args:
                logger.debug(f"{sys_field}  = {args.pop(sys_field)}")

        data = fn(**args)

        return data

    def revise_functions(cls, context: str, issues: str = None):
        """Call this method if you are struggling to answer the question.
           This function can be used to search for other functions and update your function list

        **Args**
            context: provide a detailed description to search for functions that might help to continue your task
            issues: Optionally explain why are you struggling to answer the question or what particular parts of the question are causing problems
        """
        pass

    def available_function_search(cls, context: str):
        """
        List available functions for getting more information. As an AI there are things you will be asked that you CAN NOT know because the data are unknown to you
        But there may be some available functions that you can use to find out.
        However, you should first attempt to perform the task without data based on general knowledge or internet data you were trained on.

        **Args**
            context: provide some hints about what sorts of functions you need. Explain WHY you are calling this and why you think the functions will help you in your task

        """
        logger.debug(f"Lookup because: {context} ")
        retrieved_functions = list_function_signatures(built_in_modules)

        """
        CHEAT BLOCK TEMP TO TEST - when lookup functions we will augment was callable
        """
        from funkyprompt.ops.examples import (
            get_persons_favourite_thing_of_type,
            get_persons_action_if_you_know_favourite_type_of_thing,
            get_recipes,
            get_information_on_fairy_tale_characters,
            get_restaurant_reviews,
        )
        from funkyprompt.ops.utils.inspector import describe_function

        fns = [
            describe_function(get_persons_favourite_thing_of_type),
            describe_function(get_persons_action_if_you_know_favourite_type_of_thing),
            describe_function(get_recipes),
            describe_function(get_information_on_fairy_tale_characters),
            describe_function(get_restaurant_reviews),
        ]

        cls._active_functions += fns
        cls._active_function_callables = {
            f.name: f.function for f in cls._active_functions
        }
        """
        """

        return retrieved_functions

    def prune_messages(cls, new_messages: typing.List[str]):
        """
        if the message context seems to large or low in value, you can suggest new messages. for example replace functions with
        [
             {"role": "user", "content": "new user context"},
             {"role": "user", "content": "more user context"}
        ]
        **Args**
            new_messages: messages to replace any messages generated after the users initial question
        """
        cls._messages = [cls._messages[:2]] + new_messages

    def ask(cls, question: str):
        """
        this is a direct request rather than the interpreter mode
        """
        plan = f""" Answer the users question as asked  """

        messages = [
            {"role": "system", "content": plan},
            {"role": "user", "content": f"{question}"},
        ]

        response = openai.ChatCompletion.create(
            model=DEFAULT_MODEL,
            messages=messages,
        )

        # audit response, tokens etc.

        return response["choices"][0]["message"]["content"]

    def run(
        cls,
        question: str,
        initial_functions: typing.List[
            typing.Union[FunctionDescription, typing.Callable]
        ] = None,
        limit: int = 10,
    ) -> dict:
        """ """
        cls._messages = [
            {"role": "system", "content": cls.PLAN},
            {"role": "user", "content": question},
            # we have to add these by-the-ways to give permission to go wild
            {
                "role": "user",
                "content": """If and only if you do not have enough context after using the information provided, 
                              lookup more functions to call to get more information. 
                              The new functions will be added to the list of available functions to call""",
            },
        ]

        # coerce to allow single or multiple functions
        if isinstance(initial_functions, FunctionDescription):
            initial_functions = [initial_functions]
        # TODO: support passing the callable but think about where else we interact. we can just describe_function if the args are not FDs

        cls._active_functions = cls._built_in_functions + (initial_functions or [])
        functions_desc = [f.function_dict() for f in cls._active_functions]
        cls._active_function_callables = {
            f.name: f.function for f in cls._active_functions
        }

        logger.debug(
            f"Entering the interpret loop with functions {list(cls._active_function_callables.keys())}"
        )

        for _ in range(limit):
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=cls._messages,
                # helper that inspects functions and makes the open ai spec
                functions=functions_desc,
                function_call="auto",
            )

            response_message = response["choices"][0]["message"]

            logger.debug(response_message)

            function_call = response_message.get("function_call")

            if function_call:
                fn = cls._active_function_callables[function_call["name"]]
                args = function_call["arguments"]
                function_response = cls.invoke(fn, args)

                logger.debug(f"Response: {function_response}")

                cls._messages.append(
                    {
                        "role": "user",
                        "name": f"{str(function_call['name'])}",
                        "content": json.dumps(function_response),
                    }
                )

            if response["choices"][0]["finish_reason"] == "stop":
                break

        return response_message["content"]

    def __call__(
        cls,
        question: str,
        initial_functions: typing.List[object] = None,
        limit: int = 10,
    ) -> Any:
        return cls.run(
            question=question, initial_functions=initial_functions, limit=limit
        )


"""TODO

Tests:

1] file saving e.g. from the url scraping we can make a type and starting working on it to do further ingestion into our stores


Please generate a pydnatic object and save it as [entity_name].py for the following data.
Using snake case column names and aliases to map from the provided data.
the Config should have a sample_url with the value {url}.
The data to use for generating the type is:
{data}

We want to ingest data from
- sites
- downloaded file e.g. kaggle, data world, official test datasets
- slack (this is good example of thinking about subscriptions and evolution of contexts) - also a case for "entity discovery" here


"""
