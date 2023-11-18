from funkyprompt.io.stores import ColumnarDataStore, VectorDataStore
from funkyprompt.model.entity import (
    AbstractContentModel,
    SchemaOrgVectorEntity,
    # FPActorDetails,
    typing,
)


class FairyTales(AbstractContentModel):
    """
    url = "https://www.gutenberg.org/files/20748/20748-h/20748-h.htm"
    """

    pass


def get_information_on_fairy_tale_characters(questions: typing.List[str]):
    """
    Provides details about fairy tale characters

    **Args**
        questions: ask a question in sufficient detail

    **Returns**
        returns text detail detailed long-form info related to your question about fairy tale characters
    """
    Model = AbstractContentModel.create_model("FairyTales", namespace="default")

    vs = VectorDataStore(Model, description="")

    return vs(questions)


def get_recipes(what_to_cook: typing.List[str]):
    """
    Get recipes for making any food you want. Be as detailed and specific as you can be with your request for best results

    **Args**
        what_to_cook: provide a request for what you would like to make

    **Returns**
        returns detailed detailed long-form recipe / instructions

    """
    vs = VectorDataStore(
        AbstractContentModel.create_model("Recipe", namespace="default"), description=""
    )
    return vs(what_to_cook)


def get_recipes_with_ratings(what_to_cook: typing.List[str], min_rating: int = 4.5):
    """
    Get recipes with ratings and suitability for making any food you want. Be as detailed and specific as you can be with your request for best results

    **Args**
        what_to_cook: provide a request for what you would like to make
        min_rating: the minimum user rating you will accept
    **Returns**
        returns detailed long-form textual recipe and ratings

    """
    vs = VectorDataStore(
        AbstractContentModel.create_model("Recipe", namespace="default"), description=""
    )
    return vs(what_to_cook)


def get_restaurant_reviews(name_or_type_of_place_preferred: str, location: str = None):
    """
    Get reviews of restaurants by passing in a descriptive question. Be as detailed as you can be with your request for best results

    **Args**
        name_or_type_of_place_preferred: give a specific or type of place you want to get a review for
        location: specific city or region where you want to find restaurants

    **Returns**
        returns detailed detailed long-form restaurant reviews

    """

    vs = VectorDataStore(
        AbstractContentModel.create_model("Review", namespace="default"), description=""
    )
    return vs(name_or_type_of_place_preferred)


def get_restaurant_reviews_other(
    name_or_type_of_place_preferred: str, location: str = None
):
    """
    Get reviews of by alternate restaurants by passing in a descriptive question. Be as detailed as you can be with your request for best results
    There is no reason to think this is any different to `get_restaurant_reviews` but it might be

    **Args**
        name_or_type_of_place_preferred: give a specific or type of place you want to get a review for
        location: specific city or region where you want to find restaurants

    **Returns**
        returns detailed detailed long-form fast food restaurants reviews

    """

    vs = VectorDataStore(
        AbstractContentModel.create_model("Review", namespace="default"), description=""
    )
    return vs(name_or_type_of_place_preferred)


def get_new_york_food_scene_guides(name_or_type_of_place_preferred: str):
    """
    Provides information on whats new and interesting in the New York food and drink scene

    **Args**
        name_or_type_of_place_preferred: give a specific or type of place you want to get a review for

    **Returns**
        returns advice about the New York food scene

    """

    vs = VectorDataStore(
        AbstractContentModel.create_model("Guides", namespace="default"), description=""
    )
    return vs(name_or_type_of_place_preferred)


# def get_context(ask_about_context_required: str):
#     """
#     Provides general high level context about the domain or user of the system

#     **Args**
#         ask_about_context_required: ask a question to get more details / context

#     **Returns**
#         returns additional context

#     """

#     vs = VectorDataStore(FPActorDetails)
#     return vs(ask_about_context_required)


def get_recent_questions_asked(ask_about_context_required: str):
    """
    Provides general high level context about the domain or user of the system

    **Args**
        ask_about_context_required: ask a question to get more details / context

    **Returns**
        returns additional context

    """

    vs = VectorDataStore(
        AbstractContentModel.create_model("InterpreterSession", namespace="agent"),
        description="",
    )
    return vs(ask_about_context_required)


def get_story_longitude_clock(ask_about_context_required: typing.List[str]):
    """
    Provides details about the invention of the clock, longitude and discovery

    **Args**
        ask_about_context_required: ask a question to get more details / context

    **Returns**
        returns additional context

    """

    #     agent(
    #         "What is the story of the clock about", describe_function(get_story_longitude_clock)
    # )
    # agent("Where is Harrisons last clock located today?", describe_function(get_story_longitude_clock))

    vs = VectorDataStore(
        AbstractContentModel.create_model("BookChapters", namespace="default"),
        description="",
    )
    return vs(ask_about_context_required)


def run_vector_store_search(
    question_list: typing.List[str], store_name: str, limit: int = 5
):
    """call the run_search method passing questions, limit and store name
    Example:
        run_vector_store_search(question_list,limit=5, store_name='default.my_store')


    **Args**
        question_list: A list of one or more questions to ask the store
        store_name: tje particular store you want to use
        limit: the number of results to return. Low numbers will fit in the context but higher numbers will be more comprehensive
    """
    from funkyprompt.io.stores import list_stores, open_store

    name, namespace = store_name.split(".")
    for s in list_stores():
        if s["name"] == name and s["namespace"] == namespace:
            # TODO caching- store singleton because of slower load times for Instruct
            return open_store(**s).run_search(queries=question_list, limit=limit)
