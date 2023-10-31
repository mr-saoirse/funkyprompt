import funkyprompt
from funkyprompt import logger
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import requests
import json
import itertools


def iter_doc_pages(file, **kwargs):
    """
    simple document reader - want to expand this to model text in more interesting ways

    BC = AbstractVectorStoreEntry.create_model("BookChapters")
    store = VectorDataStore(BC)
    for i, page in enumerate(iter_doc_pages(file)):
        record = BC(name = "LongitudePage{i}", text=page)
        store.add(record)

    """

    import fitz

    def process_page(page, headers={}):
        def line_detail(spans):
            return [(s["text"], round(s["size"]), s["font"]) for s in spans]

        spans = [
            line_detail(line["spans"])
            for block in page
            for line in block.get("lines", [])
        ]
        spans = list(itertools.chain.from_iterable(spans))
        # TODO implement the flatten ligic based on header changes with carry on context in headers from previous pages
        lines = "\n".join([line[0] for line in spans])
        return lines

    with fitz.open(file) as pdf_document:
        for i in range(pdf_document.page_count):
            page = pdf_document.load_page(i).get_text("dict")
            yield process_page(page["blocks"])


def ingest_pdf(name, file, embedding_provider="open-ai", doc_id=None):
    from funkyprompt.io.stores import VectorDataStore
    from funkyprompt.ops.entities import (
        AbstractVectorStoreEntry,
        InstructAbstractVectorStoreEntry,
    )

    # pdf ingestion use case - provide model
    Factory = (
        InstructAbstractVectorStoreEntry
        if embedding_provider == "instruct"
        else AbstractVectorStoreEntry
    )
    Model = Factory.create_model(name)
    store = VectorDataStore(Model)
    doc_hash = funkyprompt.str_hash(file)
    records = []
    funkyprompt.logger.debug(f"Reading document")
    for i, page in enumerate(iter_doc_pages(file)):
        record = Model(name=f"{doc_hash}{i}", text=page, doc_id=doc_id)
        records.append(record)

    store.add(records)


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


class SimpleJsonLDSpider:
    """
    WIP

    Example:

        from funkyprompt.io.tools.downloader import SimpleJsonLDSpider
        from funkyprompt.ops.entities import SchemaOrgVectorEntity
        def factory(**sample):
            Model = SchemaOrgVectorEntity.create_model_from_schema("Guides", sample)
            sample['text'] = sample.get('articleBody')
            return Model(**sample)

        s = SimpleJsonLDSpider('https://www.theinfatuation.com',
                            prefix_filter='/new-york/guides/',
                            model = factory
                            )

        from funkyprompt.io.stores import VectorDataStore
        recs = [data for url, data in s.iterate_pages(limit=10)]
        vs = VectorDataStore(recs[0])
        vs.add(recs)

    """

    def __init__(self, site, prefix_filter, max_depth=7, model=None):
        self._site_map = f"{site}/sitemap.xml"
        self._domain = site
        self._preview_filter = prefix_filter
        self._max_depth = max_depth
        self._visited = []
        self._model = model
        # temp
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        }

    def get_sitemap(self):
        resp = requests.get(self._site_map, headers=self._headers)
        if resp.status_code != 200:
            logger.warning(f"Failed to load {resp.status_code}")
        return resp.text

    def iterate_pages(self, limit=None):
        for i, page in enumerate(self.find(self._site_map)):
            if limit and i > limit:
                break
            yield page

    def find(self, sitemap_url, depth=None):
        depth = self._max_depth or depth
        logger.debug(f"<<<<<< SM: {sitemap_url} >>>>>>>>")
        if self._domain in sitemap_url:

            def lame_file_test(s):
                return "." not in s.split("/")[-1]

            def sitemap_test(s):
                return ".xml" in s and s != sitemap_url

            response = requests.get(sitemap_url, headers=self._headers)

            if response.status_code == 200:
                logger.debug(f"Visited {sitemap_url}")
                soup = BeautifulSoup(response.text, "xml")
                urls = [
                    loc.text
                    for loc in soup.find_all("loc")
                    if sitemap_test or lame_file_test(loc.text)
                ]

                # now we look deeper into sitemaps
                for url in urls:
                    if sitemap_test(url):
                        for f in self.find(url):
                            yield f
                    else:
                        for recipe in self.try_json_ld(
                            url,
                            depth=depth,
                        ):
                            yield recipe
            else:
                logger.warning(f"{response.text} >> not hitting {response.status_code}")
                for page in self.try_json_ld(
                    sitemap_url.replace("sitemap.xml", ""), depth=depth
                ):
                    yield page
        else:
            logger.warning(f"Hopping out as domain not covering {sitemap_url}")

    def as_model(self, d):
        """
        the model is either a Pydantic object or another factor that calls a Pydantic object
        """
        return d if self._model is None else self._model(**d)

    def try_json_ld(self, url, depth):
        """
        go down any depth from a sitemap looking for things
        """

        if (
            not urlparse(url).port
            and self._domain in url
            and self._preview_filter in url
        ):
            """
            If there is any JSON+LD (we dont care what) then retrieve it
            """

            data = BeautifulSoup(requests.get(url).text, "html.parser").find(
                "script", {"type": "application/ld+json"}
            )

            if data:
                data = json.loads("".join(data.contents))
                # returns the model if provided otherwise the raw
                logger.debug(f"Found {url}")
                if isinstance(data, list):
                    for d in data:
                        yield url, self.as_model(d)
                else:
                    yield url, self.as_model(data)
            else:
                # treat as links
                response = requests.get(url, headers=self._headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"]
                        absolute_url = urljoin(url, href)
                        # print(url, absolute_url)
                        if self._domain in absolute_url:
                            # print(absolute_url)
                            if depth > 0 and absolute_url not in self._visited:
                                logger.info(
                                    f"{absolute_url=}, {depth=}, total visited urls={len(self._visited)}"
                                )
                                self._visited.append(absolute_url)
                                # if len(visited) % THROTTLE_SLEEP_AT == 0:
                                #     logger.info("Sleeping....")
                                #     time.sleep(5)
                                for page in self.try_json_ld(absolute_url, depth - 1):
                                    yield page


"""
SNIPPETS
"""


def load_example_foody_guides(
    limit=10,
):
    """

    loads new york guides data samples
    note the constructor/factory might be needed to map objects

    we can make this a general function but we need much better scheam tools first (and schema migration tools)

    """
    from funkyprompt.io.tools.ingestion import SimpleJsonLDSpider
    from funkyprompt.ops.entities import SchemaOrgVectorEntity
    from funkyprompt.io.stores import VectorDataStore

    def factory(**sample):
        """
        this works if we trust the sample's schema and want to create dynamic models
        """
        Model = SchemaOrgVectorEntity.create_model_from_schema("FoodyGuides", sample)
        sample["text"] = sample.get("articleBody")
        return Model(**sample)

    s = SimpleJsonLDSpider(
        "https://www.theinfatuation.com",
        prefix_filter="/new-york/guides/",
        model=factory,
    )

    recs = [data for url, data in s.iterate_pages(limit=limit)]
    # use the reference type to make the store
    vs = VectorDataStore(recs[0])
    vs.add(recs[:2])

    # return a sample
    return recs[0]
