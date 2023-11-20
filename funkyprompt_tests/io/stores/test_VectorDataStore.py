import pytest


@pytest.mark.slow
# mark also requires key or memory or instruct etc installed
def test_vector_store_create_and_query():
    from funkyprompt.model import AbstractContentModel
    from funkyprompt.io import VectorDataStore

    Model = AbstractContentModel.create_model("test-vector-store", "test")
    store = VectorDataStore(
        Model, description="A store set up for the purpose of testing only"
    )

    record = Model(name="test_record", content="This is a test")

    # this test could fail if we are dealing with schema migrations but thats ok
    store.add(record)

    # this uses embedding tokens or a slow model
    records = store("this is a test")

    assert len(records) > 0, "We did not create and retrieve a record"
