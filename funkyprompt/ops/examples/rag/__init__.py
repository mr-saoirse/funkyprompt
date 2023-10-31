from funkyprompt.io.stores import ColumnarDataStore, VectorDataStore
from funkyprompt.ops.entities import (
    AbstractVectorStoreEntry,
    SchemaOrgVectorEntity,
    FPActorDetails,
)


class FairyTales(AbstractVectorStoreEntry):
    """
    url = "https://www.gutenberg.org/files/20748/20748-h/20748-h.htm"
    """

    pass


def get_information_on_fairy_tale_characters(question: str):
    """
    Provides details about fairy take characters

    **Args**
        question: ask a question in sufficient detail

    **Returns**
        returns text detail detailed long-form info related to your question about fairy tale characters
    """
    vs = VectorDataStore(FairyTales)

    return vs(question)


def get_recipes(what_to_cook: str):
    """
    Get recipes for making any food you want. Be as detailed and specific as you can be with your request for best results

    **Args**
        what_to_cook: provide a request for what you would like to make

    **Returns**
        returns detailed detailed long-form recipe / instructions

    """
    vs = VectorDataStore(AbstractVectorStoreEntry.create_model("Recipe"))
    return vs(what_to_cook)


def get_recipes_with_ratings(what_to_cook: str, min_rating: int = 4.5):
    """
    Get recipes with ratings and suitability for making any food you want. Be as detailed and specific as you can be with your request for best results

    **Args**
        what_to_cook: provide a request for what you would like to make
        min_rating: the minimum user rating you will accept
    **Returns**
        returns detailed long-form textual recipe and ratings

    """
    vs = VectorDataStore(AbstractVectorStoreEntry.create_model("Recipe"))
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

    vs = VectorDataStore(AbstractVectorStoreEntry.create_model("Review"))
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

    vs = VectorDataStore(AbstractVectorStoreEntry.create_model("Review"))
    return vs(name_or_type_of_place_preferred)


def get_new_your_food_scene_guides(name_or_type_of_place_preferred: str):
    """
    Provides information on whats new and interesting in the New York food and drink scene

    **Args**
        name_or_type_of_place_preferred: give a specific or type of place you want to get a review for

    **Returns**
        returns advice about the New York food scene

    """

    vs = VectorDataStore(AbstractVectorStoreEntry.create_model("Guides"))
    return vs(name_or_type_of_place_preferred)


def get_context(ask_about_context_required: str):
    """
    Provides general high level context about the domain or user of the system

    **Args**
        ask_about_context_required: ask a question to get more details / context

    **Returns**
        returns additional context

    """

    vs = VectorDataStore(FPActorDetails)
    return vs(ask_about_context_required)


# store("The Story of the creation of the Clock")
def get_story_longitude_clock(ask_about_context_required: str):
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

    vs = VectorDataStore(AbstractVectorStoreEntry.create_model("BookChapters"))
    return vs(ask_about_context_required)
