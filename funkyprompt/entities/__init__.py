"""generic types are sample everyday objects
-- project
-- person
-- org
-- task
-- book
-- topic
-- idea/scrapbook

each of these can define [relations] to other things
and we can also generate "aggregates" as separate concepts e.g. daily snapshots -> could go to duck or postgres

"""

from enum import Enum


class GenericEntityTypes(Enum):
    TOPIC = "topic"
    PROJECT = "project"


from funkyprompt.entities.nodes import *


from funkyprompt.core.types.inspection import get_classes
from funkyprompt.core import AbstractEntity
from funkyprompt.core import load_entities as load_core_entities


def load_entities(include_core: bool = True) -> typing.List[AbstractEntity]:
    """
    Load entities including the core ones optionally
    if funkyprompt is used as a library we can register entities from
    - registering/importing a package of entities
    - dynamic entities in a database
    """
    entities = get_classes(AbstractEntity, package="funkyprompt.entities")
    """
    add core entities
    """
    if include_core:
        entities += load_core_entities()
    return entities


def resolve(
    entity_model_name: str, entity_model_namespace: str = "public", **kwargs
) -> AbstractEntity:
    """resolve entity given the name and namespace
    the default is public for generic type entities that we store in funkyprompt
    """
    match = f"{entity_model_namespace}.{entity_model_name}"
    for e in load_entities():
        if e.get_model_fullname() == match:
            return e
