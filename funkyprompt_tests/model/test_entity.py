import pytest


def test_test():
    assert 1 == 1, "weird"


def test_entity_attributes():
    from funkyprompt.model import AbstractModel

    Model = AbstractModel.create_model(name="test", namespace="test")
    assert Model.__fullname__ == f"test/test"


def test_create_model_from_pyarrow_schmea():
    """
    we want to test sufficient types are supported - currently some types are handled but certainly not all
    """
    import polars as pl
    from datetime import datetime
    from funkyprompt.model import AbstractModel

    # Sample data
    data = {
        "type": ["A", "B", "C"],
        "string_col": ["hello", "world", "polars"],
        "int_col": [10, 20, 30],
        "datetime_col": [
            datetime(2023, 1, 1),
            datetime(2023, 2, 2),
            datetime(2023, 3, 3),
        ],
        "bool_col": [True, False, True],
        "list_col": [["a", "b", "c"], ["x", "y", "z"], ["p", "q", "r"]],
        "float_col": [1.5, 2.5, 3.5],
    }

    # Create a Polars DataFrame
    schema = pl.DataFrame(data).to_arrow().schema

    Model = AbstractModel.create_model_from_pyarrow(
        name="test", py_arrow_schema=schema, namespace="test"
    )

    # for now good enough that types dont below up
    assert Model is not None, "Failed to construct the model form the PyArrow schema"
