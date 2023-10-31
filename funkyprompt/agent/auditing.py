from funkyprompt.ops.entities import AbstractVectorStoreEntry, typing, model_validator
from funkyprompt import __version__
from funkyprompt.io.stores import VectorDataStore


class InterpreterSession(AbstractVectorStoreEntry):
    """
    this is used to audit the session so we can look back at plans
    """

    session_key: typing.Optional[str]
    audited_at: str
    response: str
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
        values[
            "text"
        ] = f"question: {values['question']}\nresponse:{values['response']}"

        if values.get("session_key"):
            values["doc_id"] = values["session_key"]

        # if not values.get("id"):
        #     values["id"] = values["name"]
        # if not values.get("doc_id"):
        #     values["doc_id"] = values["name"]

        return values


def get_audit_store():
    """
    Loads the vector store for the audit data
    """
    return VectorDataStore(InterpreterSession)
