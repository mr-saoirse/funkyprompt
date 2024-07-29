from funkyprompt.core.agents import CallingContext
from funkyprompt.core.agents import MessageStack
import typing


class LanguageModelBase:

    def __call__(
        self,
        messages: str | typing.List[dict] | MessageStack,
        context: CallingContext = None,
        functions: typing.Optional[dict] = None,
        **kwargs
    ):
        """the callable is a lightly more opinionated version of run for convenience
        but users of run should remain close to what the model needs
        """
        from funkyprompt.core.agents import DefaultAgentCore

        context = context or CallingContext()
        if isinstance(messages, str):
            """simple convenience cheat"""
            messages = MessageStack(question=messages, model=DefaultAgentCore)
        if isinstance(messages, MessageStack):
            messages = messages.model_dump()

        self._messages = messages
        self._functions = functions

        return self.run(messages=messages, context=context, functions=functions)


from .gpt import GptModel


def language_model_client_from_context(
    context: CallingContext = None, with_retries: int = 0
):
    """The model is loaded from the context.
    Retries are used sparingly for some system contexts that require robustness
    e.g. in formatting issues for structured responses

    This context is passed on every invocation anyway so this narrows it down to an api provider or client
    - open ai
    - llama
    - gemini
    - claude

    Within each of these providers the context can choose a model size/version
    """
    context = context or CallingContext()

    """default"""
    return GptModel()
