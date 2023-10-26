from funkyprompt.io.tools import downloader, fs
from funkyprompt import agent


def generate_type_sample(
    source_uri, namespace="default", name=None, prompt=None, save=False
):
    """
    this is an experiment in calling file save functions


    """
    data = downloader.get_page_json_ld_data(source_uri)

    # A standard way to ask for types from samples on the web
    # override if you want to experiment
    name = name or "Entity"

    prompt = (
        prompt
        or f"""
        Please generate a Pydantic object and save it as [Review.py] for the data given below.
        - Use only snakecase column names and alises to map from the provided data.
        - Simplify the schema to select only 5 or 6 of what you consider to be the primary attributes.
        - the Config should have a sample_url with the value {source_uri}.
        The data to use for generating the type is here however you should flatten the parent object so there are no child objects and then map the values in the root validator.
        To be clear map all the data to one Pydantic object.
        """
    )

    # we build the request for fetching the type
    request = f"""{prompt}
    Data:
    ```json
    {data}
    ```
    """

    # request the type from the agent - response types can be json, a Pydantic type
    data = agent(request, response_type="json")

    if save:
        fs.save_type(data, namespace=namespace, add_crud_ops=True)
