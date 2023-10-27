#!/usr/local/bin/python3

"""
various entry points are provide for local testing and cloud contexts
- ask the agent something
- ingest data from different places
- run  various code support tools e.g. building types, crud, diagrams etc.
- serve the app
- scheduler the functions to run
- receive workflow runner requests to load ops

"""
import typer
import typing
from funkyprompt import logger
from funkyprompt.io.tools import downloader, fs
from funkyprompt import agent
from funkyprompt import ops
from funkyprompt.agent import tasks

app = typer.Typer()

loader_app = typer.Typer()
app.add_typer(loader_app, name="ingest")

k8s_app = typer.Typer()
app.add_typer(k8s_app, name="k8s", help="Use the spider to ingest data into the system")

agent_app = typer.Typer()
app.add_typer(
    agent_app, name="agent", help="Use the agent to ask questions in different ways"
)


# diagram/design and types app


@agent_app.command("interpret")
def query(
    question: typing.Optional[str] = typer.Option(None, "--query", "-q"),
):
    """
    run a query against the agent using the interpreter loop
    """

    # same as agent query but
    response = agent(question)
    logger.info(response)


@agent_app.command("ask")
def query(
    question: typing.Optional[str] = typer.Option(None, "--query", "-q"),
):
    """
    run a query against the agent using the direct ask - this is simply more low level that the interpret
    """

    # same as agent query but
    response = agent.ask(question)
    logger.info(response)


"""

     LOADERS: for ingesting test data

"""


@loader_app.command("init")
def ingest_type(
    source_uri: str = typer.Option(None, "--url", "-u"),
    name: str = typer.Option(None, "--name", "-n"),
    namespace: str = typer.Option("default", "--namespace", "-n"),
    prompt: str = typer.Option(None, "--prompt", "-p"),
):
    """
    initialize a schema using some sample remote data
    """
    tasks.generate_type_sample(
        source_uri=source_uri, name=name, namespace=namespace, prompt=prompt
    )


@loader_app.command("page")
def ingest_page(
    url: str = typer.Option(None, "--url", "-u"),
    store_name: str = typer.Option(None, "--name", "-n"),
):
    """
    ingest a page at url into a named store...

    """
    pass


@loader_app.command("entity")
def ingest_type(
    entity_type: str = typer.Option(None, "--name", "-n"),
    url_prefix: str = typer.Option(None, "--prefix", "-p"),
    limit: str = typer.Option(100, "--limit", "-l"),
    save: bool = typer.Option(False, "--save", "-s"),
):
    """
    TODO: doc strings
    add either the uri or the type
    if you specify the uri and it is typed
    ingest data into a schema of type [entity_type] up to a [limit]
    we scrape a configured entity from a url and we can filter the site on the give [url_prefix] if given
    if the save option is set, we write to a vector store using convention
    otherwise we write to the terminal
    """
    from funkyprompt.io.tools.downloader import site_map_from_sample_url, crawl

    entity_type = fs.load_type(entity_type)
    sample_url = entity_type.Config.sample_url
    site_map = site_map_from_sample_url(sample_url)

    """
    Here we crawl in batches up to some limit
    The batches are either printed out to shell or we can save them to the vector store with the embedding
    """
    for batch in crawl(
        site_map=site_map,
        prefix=url_prefix,
        limit=limit,
        entity_type=entity_type,
        batch_size=50,
    ):
        for record in batch:
            logger.info(record)


"""

      Main App and entry points

"""


@app.command("run")
def run_workflow_method(
    name: str = typer.Option(None, "--name", "-n"),
    method: typing.Optional[str] = typer.Option(None, "--method", "-m"),
    value: typing.Optional[str] = typer.Option(None, "--value", "-v"),
    is_test: typing.Optional[bool] = typer.Option(False, "--test", "-t"),
):
    logger.info(f"Invoke -> {name=} {method=} {value=}")

    """
    This is designed to run with workflows 
    
    Run the specific module - unit test we can always load them and we get correct request
    Also output something for the workflow output parameters below
    
    to test the workflows and not worry about real handlers you can pass -t in the workflow
    """
    import json
    from funkyprompt.ops.utils.inspector import load_op

    with open("/tmp/out", "w") as f:
        if is_test:
            dummy_message = {"message": "dummy", "memory": "1Gi"}
            data = (
                [dummy_message, dummy_message]
                if method == "generator"
                else dummy_message
            )
            logger.debug(f"Dumping {data}")
        else:
            fn = load_op(name, method)
            data = fn(value)

        json.dump(data, f)

        return data or []


@app.command("serve")
def serve_app(
    port: typing.Optional[int] = typer.Option(False, "--port", "-p"),
    voice_interface_enabled: typing.Optional[bool] = typer.Option(
        False, "--voice", "-v"
    ),
):
    """
    Serve in instance of funkyprompt on the specified port
    """
    from funkyprompt.app import app
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port or 8008)


@app.command("scheduler")
def scheduler_start():
    from funkyprompt.ops.deployment.scheduler import start_scheduler

    logger.info(f"Starting scheduler")
    _ = start_scheduler()


if __name__ == "__main__":
    app()
