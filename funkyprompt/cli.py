#!/usr/local/bin/python3
import typer
import typing
from funkyprompt import logger
from funkyprompt.io.tools.downloader import get_page_json_ld_data
from funkyprompt import agent
from funkyprompt import ops

app = typer.Typer()

spider_app = typer.Typer()
app.add_typer(spider_app, name="spider")

k8s_app = typer.Typer()
app.add_typer(k8s_app, name="k8s", help="Use the spider to ingest data into the system")


# diagram/design and types app


@app.command("serve")
def run_method(
    port: typing.Optional[int] = typer.Option(False, "--port", "-p"),
    voice_interface_enabled: typing.Optional[bool] = typer.Option(
        False, "--voice", "-v"
    ),
):
    """
    Serve in instance of funkyprompt on the specified port
    """
    pass


@app.command("test")
def run_method(
    prompt: typing.Optional[bool] = typer.Option(False, "--prompt", "-p"),
):
    """
    test method to check installation
    """
    logger.info(f"Hello World")


@app.command("query")
def query(
    prompt: typing.Optional[bool] = typer.Option(False, "--query", "-q"),
):
    """
    run a query against the agent
    """
    pass


@spider_app.command("init")
def ingest_type(
    source_uri: str = typer.Option(None, "--uri", "-u"),
    namespace: str = typer.Option("default", "--namespace", "-n"),
    prompt: str = typer.Option(None, "--prompt", "-p"),
):
    """
    initialize a schema using some sample remote data
    """
    data = get_page_json_ld_data(source_uri)
    logger.info(data)

    # A standard way to ask for types from samples on the web
    # override if you want to experiment
    prompt = (
        prompt
        or f"""
    Please generate a Pydantic type for the Json data below.
    Instructions:
    - Use snake casing for the types and add aliases to map from the provided data to our schema.
    - Add to the Config a source_url attribute with the value"""
    )

    # we build the request for fetching the type
    request = f"""{prompt}
    source_url: "{  source_uri   }"
    data:
    ```json
    {data}
    ```
    """

    # request the type from the agent - response types can be json, a Pydantic type
    data = agent(request, response_type="json")

    ops.save_type(data, namespace=namespace, add_crud_ops=True)


@spider_app.command("ingest")
def ingest_type(
    entity_type: str = typer.Option(None, "--type", "-t"),
    url_prefix: str = typer.Option(None, "--prefix", "-p"),
    limit: str = typer.Option(100, "--limit", "-l"),
    save: bool = typer.Option(False, "--save", "-s"),
):
    """
    ingest data into a schema of type [entity_type] up to a [limit]
    we scrape a configured entity from a url and we can filter the site on the give [url_prefix] if given
    if the save option is set, we write to a vector store using convention
    otherwise we write to the terminal
    """
    from funkyprompt.io.tools.downloader import site_map_from_sample_url, crawl

    entity_type = ops.load_type(entity_type)
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


if __name__ == "__main__":
    app()
