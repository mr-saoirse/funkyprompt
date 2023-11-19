from . import examples


def preprompt(prompt):
    """
    #we do this because we are treating things as modular and not because we cannot change the prompt of f
    @chat.preprompt("More stuff 1")
    @chat.preprompt("More stuff 2")
    @chat.session
    def f(a: str):
        \"""
        im gonna do great
        \"""
        return a
    g = chat.preprompt("Stuff added to the prompt 3")(f)
    g?


    """

    def decorator(f):
        f.__doc__ = f"{prompt}\n{f.__doc__}"
        return f

    return decorator
