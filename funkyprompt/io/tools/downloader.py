import json
import requests
from bs4 import BeautifulSoup
import funkyprompt


def get_page_json_ld_data(url: str) -> dict:
    """
    Given a url, get the JSON LD on the page
    e.g https://www.allrecipes.com/recipe/216470/pesto-chicken-penne-casserole/

    this is a simple helper utility and not well tested for all circumstances
    """
    parser = "html.parser"
    req = requests.get(url)
    soup = BeautifulSoup(req.text, parser)
    data = json.loads(
        "".join(soup.find("script", {"type": "application/ld+json"}).contents)
    )

    if "@graph" in data:
        funkyprompt.logger.warning("Dereference to @graph when fetching schema")
        data = data["@graph"]

    if isinstance(data, list):
        funkyprompt.logger.warning(
            f"Selecting one item from the list of length {len(data)}"
        )
        return data[0]

    return data


def sample_attributes_from_record(data, max_str_length=100, max_sublist_samples=1):
    """
    when we sample data we need to make sure we do not send to much to the LLM
    This function allows us to filter
    note that when we make our type, we should prune the pydantic object to exclude low value data that we take up space
    in the example schema for recipes, comments are arguably superfluous
    even if they are not, you probably want some sort of attribute to decide how and where to save them
    normally by vector data you want to select certain fields to merge into the text column - over time we can do this interactively
    """
    if isinstance(data, list):
        data = data[0]
    keys = list(data.keys())
    for k in keys:
        v = data[k]
        if isinstance(v, list):
            data[k] = v[:max_sublist_samples]
        if isinstance(v, str) and len(v) > max_str_length:
            data[k] = v[:max_str_length]
    return data


def site_map_from_sample_url(url, first=True):
    """
    walk to the root to find the first or nearest sitemap
    """
    return


def crawl(site_map, prefix=None, entity_type=None, limit=100, batch_size=1):
    """
    crawl the site and filter on the url prefix if given
    stop after we have parsed [limit] entities are if we dont know the type after we have visited [limit] pages
    """
    pass


def iterate_types_from_headed_paragraphs(
    url: str,
    entity_type: funkyprompt.ops.entities.AbstractVectorStoreEntry,
    name: str = None,
    namespace: str = None,
):
    """This is a simple scraper. Something like Unstructured could be used in future to make this better

    for example
    url = "https://www.gutenberg.org/files/20748/20748-h/20748-h.htm"
    class FairyTales(AbstractVectorStoreEntry):
        pass
        # class Config:
        #     embeddings_provider = "instruct"
        # vector: Optional[List[float]] = Field(
        #     fixed_size_length=INSTRUCT_EMBEDDING_VECTOR_LENGTH
        # )

    This can be used to ingest types e.g
    data = list(iterate_types_from_headed_paragraphs(url, FairyTales ))
    VectorDataStore(FairyTales).add(data)

    **Args**
        url: the page to scrape headed paragraphs into types
        entity_type: the type to ingest
        name: optional name of entity to generate to route data. By default the abstract entity type is used
        namespace : optional namespace to route. by default the entity type namespace is sed
    """

    page = requests.get(url=url)
    soup = BeautifulSoup(page.content, "html.parser")
    elements = soup.find_all(lambda tag: tag.name in ["h2", "p"])

    current = None
    store_index = 0
    part_index = 0
    for element in elements:
        # track header and decide what to do
        if element.name == "h2":
            if "]" in element.text:
                name = element.text.split("]")[-1]
                current = name
                store_index += 1
                part_index = 0
        elif current and element.text:
            part_index += 1
            key = name.replace(" ", "-") + "-" + str(part_index)
            if len(element.text) > 50:
                ft = entity_type(name=key, text=element.text)
                yield ft
