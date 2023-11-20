from funkyprompt.model.entity import AbstractContentModel, typing, model_validator
from funkyprompt.io.stores import VectorDataStore
from funkyprompt import __version__
from base64 import b64encode, b64decode
import zlib


def compress_string(regular_string):
    """
    this is used as a pair of function to compress a string but to base 64 bytes that we can move around
    example Json -> dumps -> compression -> base 64 encoded -> send
    """
    return b64encode(zlib.compress(regular_string.encode())).decode("utf-8")


def decompress_string(base_64_encoded_compressed):
    """
    other part of a pair; base 64 over the wire and then decompress it
    example receive base 64 encoded string that has been compressed, unpack it e.g. something we can load into json
    """
    return zlib.decompress(b64decode(base_64_encoded_compressed)).decode()


class InterpreterSessionRecord(AbstractContentModel):
    """
    this is used to audit the session so we can look back at plans
    """

    # a unique session, attempting to answering some question
    session_key: typing.Optional[str]
    # audit date
    audited_at: str
    # original question
    question: str
    # dump of messages
    messages: str
    # the plan for the agent as per code base
    plan: str
    # experimental: store some idea of what the agent is attending to which we sometime given in planning
    attention_comments: typing.Optional[str] = ""
    # TODO: some understanding of functions used - may leave this to OTEL trace
    function_usage_graph: typing.Optional[str] = ""
    # 0 is unrated - only positive and negative values off zero are valid
    response_agents_confidence: typing.Optional[float] = 0
    # a user confidence if given - usually not
    response_users_confidence: typing.Optional[float] = 0
    # library build
    code_build: typing.Optional[str] = __version__

    @model_validator(mode="before")
    def default_vals(cls, values):
        if values.get("session_key"):
            values["document"] = values["session_key"]

        return values


def get_audit_store():
    """
    Loads the vector store for the audit data
    """
    return VectorDataStore(
        InterpreterSessionRecord, description="Store for auditing events"
    )
