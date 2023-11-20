import pytest


@pytest.mark.slow
def test_ingest_schema_org():
    from funkyprompt.model.entity import SchemaOrgVectorEntity
    from funkyprompt.io.tools.ingestion import get_page_json_ld_data

    url = "https://www.maangchi.com/recipe/tongbaechu-kimchi"
    data = get_page_json_ld_data(url)
    RecipeType = SchemaOrgVectorEntity.create_model_from_schema("Recipe", data)
    recipe = RecipeType(**data)

    content = recipe.content

    assert (
        content and len(content) > 1
    ), "The content could not be parsed or not mapped to the correct interface attribute"
