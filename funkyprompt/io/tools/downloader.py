import json
import requests
from bs4 import BeautifulSoup


def get_page_json_ld_data(url: str) -> dict:
    """
    Given a url, get the JSON LD on the page
    e.g https://www.allrecipes.com/recipe/216470/pesto-chicken-penne-casserole/
    """
    parser = "html.parser"
    req = requests.get(url)
    soup = BeautifulSoup(req.text, parser)
    data = json.loads(
        "".join(soup.find("script", {"type": "application/ld+json"}).contents)
    )

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
    for k, v in data.items():
        if isinstance(v, list):
            data[k] = v[:max_sublist_samples]
        if isinstance(v, str) and len(v) > max_str_length:
            data[v] = v[:max_str_length]
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
