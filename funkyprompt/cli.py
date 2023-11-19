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
import funkyprompt
from funkyprompt import logger
from funkyprompt.io.tools import fs
from funkyprompt import agent
from funkyprompt.agent.planning import PlanningAgent

app = typer.Typer()

# loader_app = typer.Typer()
# app.add_typer(loader_app, name="ingest")

# test schema migration: does lance allow saving things that are not in schema?? in any case do the migration of new vars before or after

data_app = typer.Typer()
app.add_typer(data_app, name="data", help="interact with rag stores [add|query|entity]")

data_add_app = typer.Typer()
app.add_typer(data_add_app, name="data_add", help="add data modes [webpage|pdf|site]")

# k8s_app = typer.Typer()
# app.add_typer(k8s_app, name="k8s", help="Use the spider to ingest data into the system")

agent_app = typer.Typer()
app.add_typer(
    agent_app,
    name="agent",
    help="Use the agent to ask questions in different ways [ask|interpret]",
)


runner_app = typer.Typer()
app.add_typer(
    runner_app, name="run", help="run funkyprompt processes [api|scheduler|function]"
)

# diagram/design and types app


@data_app.command("query")
def query_store(
    query: typing.Optional[str] = typer.Option(None, "--query", "-q"),
    store: typing.Optional[str] = typer.Option(None, "--store-name", "-n"),
):
    """
    run a query against the store
    """
    from funkyprompt.model import InstructEmbeddingContentModel
    from funkyprompt.io.stores import VectorDataStore

    # todo proper loader by name - this assumes default namespace and instruct embedding
    Model = InstructEmbeddingContentModel.create_model(name=store)
    agent = VectorDataStore(Model).as_agent()
    result = agent(query)
    logger.info(result)


@agent_app.command("summarize")
def query_store(
    question: typing.Optional[str] = typer.Option(
        "id like a general summary", "--question", "-q"
    ),
    file_or_data: typing.Optional[str] = typer.Option(None, "--data", "-d"),
):
    """
    run a query against the store
    """
    # check is file or uri - assume uri for now
    from funkyprompt.io.tools.ingestion import _ingest_web_page

    data = _ingest_web_page(file_or_data)
    result = agent.summarize(question=question, data=data)
    logger.info(result)


@agent_app.command("interpret")
def query(
    question: typing.Optional[str] = typer.Option(None, "--query", "-q"),
    session_key: typing.Optional[str] = typer.Option(None, "--session_key", "-k"),
):
    """
    run a query against the agent using the interpreter loop
    """

    # same as agent query but
    response = agent(question, session_key=session_key)
    logger.info(response)


@agent_app.command("ask")
def query(
    question: typing.Optional[str] = typer.Option(None, "--query", "-q"),
):
    """
    run a query against the agent using the direct ask
    """

    # same as agent query but
    response = agent.ask(question)
    logger.info(response)


@agent_app.command("plan")
def plan(
    question: typing.Optional[str] = typer.Option(None, "--query", "-q"),
    session_key: typing.Optional[str] = typer.Option(None, "--session_key", "-k"),
):
    """
    describe a plan to use functions to solve the question without asking it
    """
    pagent = PlanningAgent()
    logger.debug(pagent.PLAN)
    logger.debug("------------")
    # same as agent query but
    response = pagent.run(question, session_key=session_key)
    logger.info(response)


"""

     LOADERS: for ingesting test data

"""


@data_app.command("entity")
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
    from funkyprompt.io.tools.ingestion import site_map_from_sample_url, crawl

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

    Indexing experiment - semantic network 
    Also ingestion basic

"""


@data_app.command("add")
def add(
    name: str = typer.Option(None, "--name", "-n"),
    url: str = typer.Option(None, "--url", "-i"),
    prefix_filter: typing.Optional[str] = typer.Option(None, "--filter", "-f"),
    batch_size: typing.Optional[int] = typer.Option(100, "--size", "-s"),
    schedule: typing.Optional[str] = typer.Option(None, "--cron", "-c"),
    namespace: str = typer.Option("default", "--namespace", "-ns"),
):
    """
    create an index on a schedule to ingest data or do it once off without schedule
    we need a site map and name - this can be looking for json+ld or just do a page scrape
    if we do this, the interesting thing then becomes how to build the network over it and how the functions are generated

    see if we can use the filters in the site maps or not!!
    Look into refs with the schema ids - if we can ref well know orgs etc that would be cool

    as we ingest a lot of data we need to think about the value. why not just go to google or chat GPT?
    we are trying to build a competency for organizing data and routing functions

    add this by the API too - columnar store
    """

    from funkyprompt.model import AbstractContentModel
    from funkyprompt.io import VectorDataStore
    from funkyprompt.io.tools.ingestion import (
        ingest_page_to_model,
        iterate_types_from_headed_paragraphs,
    )

    # temporary

    Model = AbstractContentModel.create_model(name, namespace=namespace)
    store = VectorDataStore(Model, description=f"Ingested from {url}")

    logger.debug(f"Ingesting {url} to {namespace}.{name}")
    data = list(iterate_types_from_headed_paragraphs(url, Model))
    store.add(data)
    logger.debug(f"Ingested")


@data_add_app.command("webpage")
def ingest_page(
    url: str = typer.Option(None, "--url", "-u"),
    store_name: str = typer.Option(None, "--name", "-n"),
    namespace: str = typer.Option("default", "--namespace", "-ns"),
):
    """
    ingest a page at url into a named store...

    """
    from funkyprompt.model import AbstractContentModel
    from funkyprompt.io import VectorDataStore
    from funkyprompt.io.tools.ingestion import ingest_page_to_model

    Model = AbstractContentModel(store_name, namespace=namespace)
    store = VectorDataStore(Model, description=f"Ingested from {url}")

    logger.debug(f"Ingesting {url} to {namespace}.{store_name}")
    ingest_page_to_model(url=url, model=Model)


"""

      Main App and entry points

"""


@runner_app.command("function")
def run_workflow_method(
    name: str = typer.Option(None, "--name", "-n"),
    method: typing.Optional[str] = typer.Option(None, "--method", "-m"),
    value: typing.Optional[str] = typer.Option(None, "--value", "-v"),
    is_test: typing.Optional[bool] = typer.Option(False, "--test", "-t"),
):
    """
    run functions defined in the library with --name
    """
    import json
    from funkyprompt.ops.utils.inspector import load_op

    logger.info(f"Invoke -> {name=} {method=} {value=}")

    """
    This is designed to run with workflows 
    
    Run the specific module - unit test we can always load them and we get correct request
    Also output something for the workflow output parameters below
    
    to test the workflows and not worry about real handlers you can pass -t in the workflow
    """

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


@runner_app.command("api")
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


@runner_app.command("scheduler")
def scheduler_start():
    """
    run the scheduler to invoke functions on cron schedules
    """

    from funkyprompt.ops.deployment.scheduler import start_scheduler

    logger.info(f"Starting scheduler")
    _ = start_scheduler()


if __name__ == "__main__":
    app()
