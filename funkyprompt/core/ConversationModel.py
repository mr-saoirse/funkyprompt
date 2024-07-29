from . import AbstractModel
from funkyprompt.core.fields.annotations import OpenAIEmbeddingField
import typing
from pydantic import BaseModel, Field

CONVERSATION_MODEL_DESCRIPTION = f"""Conversation model tracks the ongoing conversation 
which can involve questions, answers, objectives, entities, knowledge, users, channels and more.
All of this is captured as users interact with agents
"""


class ConversationModel(AbstractModel):
    class Config:
        name: str = "conversation"
        namespace: str = "core"
        description: str = CONVERSATION_MODEL_DESCRIPTION

    user_id: str = Field(
        default="system", description="The user involved in the session"
    )
    objective_node_id: typing.Optional[str] = Field(
        description="The objective node if it exists and is being tracked", default=None
    )
    content: dict | str = OpenAIEmbeddingField(
        description="Structured or unstructured conversation - should normally take the forma of a fragment e.g. question and response"
    )
