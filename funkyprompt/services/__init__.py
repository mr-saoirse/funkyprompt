from funkyprompt.services.models import language_model_client_from_context
from funkyprompt.core import AbstractEntity
from .data.postgres import PostgresService


def entity_store(model: AbstractEntity):
    """returns the configured store for the entity"""
    return PostgresService(model)
