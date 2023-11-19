from pydantic import Field, BaseModel, create_model, model_validator
import typing


class EventBase(BaseModel):
    # the unique event id
    id: str
    # the conversation session id
    session_id: str
    # the user name
    username: str
    # and event timestamp
    unix_timestamp: int


class DataPointRetrieval(BaseModel):
    # the name  / id of the data point
    name: str
    # for vector stores the distance or weight
    distance: str = 0


class SearchEvent(EventBase):
    # the list of (name,distance) records probed for the question
    data_points: typing.List[DataPointRetrieval] = []
    # the question that triggered the retrieval
    context: str
    # the unique function name that was used for query often this is the name of a store
    unique_function_name: str
    # when an agent calls a function in funkyprompt it should supply confidence
    invocation_confidence: float = None
