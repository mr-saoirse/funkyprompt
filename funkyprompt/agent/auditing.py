from funkyprompt.model.entity import AbstractContentModel, typing, model_validator
from funkyprompt import __version__
from funkyprompt.io.stores import VectorDataStore


class InterpreterSessionRecord(AbstractContentModel):
    """
    this is used to audit the session so we can look back at plans
    """

    session_key: typing.Optional[str]
    audited_at: str
    question: str
    messages: str
    plan: str

    attention_comments: typing.Optional[str] = ""
    function_usage_graph: typing.Optional[str] = ""
    # 0 is unrated - only positive and negative values off zero are valid
    response_agents_confidence: typing.Optional[float] = 0
    response_users_confidence: typing.Optional[float] = 0
    code_build: typing.Optional[str] = __version__

    # extracted files??

    @model_validator(mode="before")
    def default_vals(cls, values):
        if values.get("session_key"):
            values["document"] = values["session_key"]

        return values


def get_audit_store():
    """
    Loads the vector store for the audit data
    """
    return VectorDataStore(InterpreterSessionRecord)
