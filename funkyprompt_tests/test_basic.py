import funkyprompt


def test_imports():
    from funkyprompt.model import AbstractContentModel, AbstractModel
    from funkyprompt.agent import AgentBase
    from funkyprompt.io import VectorDataStore, ColumnarDataStore
    from funkyprompt.model import func, entity

    assert 1 == 1, "weird"
