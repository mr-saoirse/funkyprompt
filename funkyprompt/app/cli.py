"""
simple cli
"""

import typer
import funkyprompt
from funkyprompt.core.agents import CallingContext
import typing

app = typer.Typer()


@app.command("ask")
def ask(query: typing.Optional[str] = typer.Option(None, "--query", "-q"),
        model: typing.Optional[str] = typer.Option(None, "--model", "-m")
        ):
    """
    run a query
    """

    # todo proper loader by name - this assumes default namespace and instruct embedding
    def callback(s):
        print(s, end="")

    query = query or "tell the user welcome to funkyprompt - run ask -q your question"
    response = funkyprompt.ask(query, context=CallingContext(response_callback=callback))
    
    print(response)