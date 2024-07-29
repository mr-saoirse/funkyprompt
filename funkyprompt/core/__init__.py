from funkyprompt.core.AbstractModel import AbstractModel, AbstractEntity, Field, typing
from funkyprompt.core.ConversationModel import ConversationModel
from funkyprompt.core.fields.annotations import OpenAIEmbeddingField


def load_entities() -> typing.List[AbstractEntity]:
    from funkyprompt.core.types.inspection import get_classes

    entities = get_classes(AbstractEntity)

    def _not_private(e):
        """we treat entities that are prefixed with _ as hidden entities"""
        return (
            e.__name__[:1] != "_"
            and not getattr(e.Config, "is_hidden", False)
            and e.__name__ != "AbstractEntity"
        )

    entities = [e for e in entities if hasattr(e, "Config")]
    entities = [e for e in entities if _not_private(e)]

    return entities


from funkyprompt.core.utils import logger
