from funkyprompt.io.stores import ColumnarDataStore, VectorDataStore
from funkyprompt.ops.entities import AbstractVectorStoreEntry


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
        text details related to your question
    """
    vs = VectorDataStore(FairyTales)

    return vs(question)


def get_recipes(what_to_cook: str):
    """
    Get recipes for making any food you want. Be as detailed and specific as you can be with your request for best results

    **Args**
        what_to_cook: procide a request for what you would like to make

    **Returns**
        returns recipe / instructions

    """
    vs = VectorDataStore(AbstractVectorStoreEntry.create_model("Recipe"))
    return vs(what_to_cook)


def get_restaurant_reviews(name_or_type_of_place: str, location: str = None):
    """
    Get reviews by passing in a descriptive question. Be as detailed as you can be with your request for best results

    **Args**
        name_or_type_of_place: give a specific or type of place you want to get a review for
        location: specific city or region where you want to find restaurants

    **Returns**
        returns restaurant reviews

    """

    vs = VectorDataStore(AbstractVectorStoreEntry.create_model("Review"))
    return vs(name_or_type_of_place)
