from typing import Any
import openai
from funkyprompt import logger
import typing
import json


class AgentBase:
    """
    we are completely functional except for how the interpreter works
    some functions such as checking session history are still functional
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
