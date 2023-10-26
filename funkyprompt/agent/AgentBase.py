from typing import Any
import openai
from funkyprompt import logger
import typing
import json

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

    PLAN = """
    Prompt should not be about questions only about the interpreter logic and interfaces
    Answer users question
    Return values including files and structured types
    Use built in functions
    """

    def __init__(cls, modules, **kwargs):
        """
        modules are used to inspect functions including functions that do deep searches of other modules and data

        """
        # add function revision and pruning as an option
        cls._built_in_functions = []

    def invoke(cls, name, args):
        """
        here we parse and audit stuff using Pydantic types
        """
        pass

    def revise_functions(cls, context):
        """ """
        pass

    def prune_messages(cls, new_messages):
        """ """
        pass

    def ask(cls, question: str):
        """
        this is a direct request rather than the interpreter mode
        """
        plan = f""" Answer the users question as asked  """

        messages = [
            {"role": "system", "content": plan},
            {"role": "user", "content": question},
        ]

        response = openai.ChatCompletion.create(
            model=DEFAULT_MODEL,
            messages=messages,
        )

        # audit response, tokens etc.

        return response["choices"][0]["message"]

    def run(
        cls, question: str, initial_functions: typing.List[object], limit: int = 10
    ) -> dict:
        """ """
        cls._messages = [
            {"role": "system", "content": cls.PLAN},
            {"role": "user", "content": question},
        ]

        functions = cls._built_in_functions + initial_functions
        for _ in range(limit):
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=cls._messages,
                # helper that inspects functions and makes the open ai spec
                functions=functions,
                function_call="auto",
            )

            response_message = response["choices"][0]["message"]

            function_call = response_message.get("function_call")

            if function_call:
                name = function_call["name"]
                args = function_call["arguments"]
                function_response = cls._invoke(name, args)
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
        cls, question: str, initial_functions: typing.List[object], limit: int = 10
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
