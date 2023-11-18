"""

we have function signatures for testing stuff
we also have really functions that connect to data stores (run the scripts to populate the data)
"""


from pydantic import BaseModel
import typing


class Person(BaseModel):
    """
    This is a person
    """

    name: typing.Optional[str] = ""
    email: str
    team: typing.Optional[str]

    # @model_validator(mode="after")
    def default_ids(cls, values):
        values["name"] = values.get("name", values.get("email").split("@")[0])
        return values


class Response(BaseModel):
    """
    This is a response
    """

    content: str


def get_persons_favourite_thing_of_type(person: Person, thing_type: str) -> str:
    """
    This function returns the favourite thing of type for a supplied Person

    **Params**
        person: This a complex type that describes the person
        thing_type: The class of thing we are interested in e.g. 'color', 'food' or 'animal'

    **Returns**
        We return structured information on the persons favourite thing

    **Raises**
        Exception

    """
    # hard coded for test questions

    return f"This person {person['name']}'s favourite color is gold, baby!"


def get_persons_action_if_you_know_favourite_type_of_thing(
    type: str, thing: str
) -> str:
    """
    This function returns the favourite type of thing. Supply the type of thing and the thing itself and we give back the action.
    If you are given a thing but not the type you should infer the type (looking at you GPT+)

    **Params**
        type:  the type of thing. For example the word 'color', 'animal' or 'food'
        thing: The thing itself e.g. if the type is 'color' the thing might be 'gold' or if the type is 'animal' the thing will be 'cat'

    **Returns**
        We return structured information on the persons action given favourite thing

    **Raises**
        Exception

    """

    # this was very interesting GPT-4 would NOT accept the answer when the type and thing context was not included
    # this was because of our strategy to review confidence perhaps
    # removing the context to see if there is a way for it to accept would be good to do
    # extra reflection with needed to ask for function review but not repeated calls - the stupidity test is interesting - bang head on wall
    return f"the person's favourite thing when {type=} {thing=} is eating vanilla ice cream surprisingly"


# def get_person_info(person: Person):
#     pass


# def get_favourite_color(person: Person):
#     pass


# def get_favourite_cuisine(person: Person):
#     pass


# def get_favourite(person: Person, thing_type: str):
#     pass


# def get_favourite(animal, thing_type: str):
#     pass


# def get_favourite(animal, thing_type: str):
#     pass


# def get_hobbies(person: Person):
#     pass


# def get_recipes(cuisine: str):
#     pass


# def get_restaurants(cuisine: str, city: str):
#     pass


# def get_restaurants_visited(person: Person):
#     pass
