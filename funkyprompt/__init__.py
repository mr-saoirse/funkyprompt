from enum import Enum


class LanguageModelProviders(Enum):

    openai = "openai"


import typing
from funkyprompt.core.agents import CallingContext
from funkyprompt.core import AbstractModel
from funkyprompt import entities


def run(
    questions: str | typing.List[str],
    context: CallingContext = None,
    model: AbstractModel = None,
):
    """entry point into the runner for convenience
    - direct questions can be asked butthen the simple `ask` method would suffice
    - the runner allows for function calling in the executor loop
    - override the default basic model with your own
    """
    from funkyprompt.core.agents import Runner

    r = Runner(model)
    return r(questions)


def ask(question, context=None, **kwargs):
    """simple model entry point
    You can ask a question just to test the basic machinery with optional streaming

    Examples
        ```python
        import funkyprompt
        from funkyprompt.core.agents import CallingContext

        a = funkyprompt.ask("what is a funkyprompt agent",
                        context = CallingContext(streaming_callback=lambda s : print(s, end='')))

        ```

        or more simply

        ```python
        funkyprompt.ask('what is the capital of ireland')
        ```

        or using different models;


    """

    from funkyprompt.services import language_model_client_from_context

    model = language_model_client_from_context()
    return model(question, context=context, **kwargs)
