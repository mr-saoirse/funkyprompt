#!/usr/local/bin/python3
import typer
import typing
from funkyprompt import logger

app = typer.Typer()


@app.command("test")
def run_method(
    prompt: typing.Optional[bool] = typer.Option(False, "--prompt", "-p"),
):
    logger.info(f"Hello World Eunseo")


if __name__ == "__main__":
    app()
