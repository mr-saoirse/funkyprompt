import funkyprompt
from funkyprompt import logger
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import requests
import json
import itertools
import polars as pl
from funkyprompt.model import AbstractContentModel, InstructEmbeddingContentModel
from funkyprompt.io.stores import ColumnarDataStore
from funkyprompt.model import AbstractModel
from funkyprompt.io.stores import VectorDataStore
import typing

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
}


def iter_doc_pages(file, **kwargs):
    """
    simple document reader - want to expand this to model text in more interesting ways

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


def ingest_pdf(
    model: AbstractContentModel,
    file: str,
    doc_id: str = None,
):
    """
    To ingest a pdf choose an embedding, a file and name of the store to add it to.
    It is advisable to pick a doc id to group sections by but can be the pdf file name


    **Args**
        model: the model to use e,g, Model = InstructEmbeddingContentModel.create_model('NewBookChapters')
        file: the name of the pdf (full path)
        embedding_provider: the embedding to use (must map what is already in store for non empty store) open-ai|instruct
        doc_id: a section or book name
    """

    if doc_id is None:
        # default id
        doc_id = file.split("/")[-1].split(".")[0].replace(" ", "_")

    # description does not matter here
    store = VectorDataStore(model, description=f"Ingesting book {file}")
    doc_hash = funkyprompt.str_hash(file)
    records = []
    funkyprompt.logger.debug(f"Reading document")
    for i, page in enumerate(iter_doc_pages(file)):
        if i % 100 == 0 and i > 0:
            funkyprompt.logger.debug(f"inserting batch")
            store.add(records)
            records = []
        record = model(name=f"{doc_hash}{i}", content=page, document=doc_id)
        records.append(record)
    funkyprompt.logger.debug(f"inserting remaining document")
    store.add(records)
    funkyprompt.logger.debug(f"done")


def ingest_arrow(name, file, key_field, embedding_provider="open-ai"):
    """
    ingest anything that polars can read into arrow format
    we consider a future embedding in column stores but not used now

    **Args**:
        name: the name of the store to ingest into - unlike vector stores its 1:1 with the schema of the data
        file: the file to ingest from
        key_field: the primary key field for the schema (required for merging datasets)
        embedding_provider: currently not implemented

    **Returns**
        a VectorDataStore constructed from the model `name`

    """

    data = pl.read_csv(file)
    Model = AbstractModel.create_model_from_pyarrow(name, data.to_arrow().schema)
    records = [Model(**d) for d in data.to_dicts()]
    store = ColumnarDataStore(Model)
    store.add(records, key_field=key_field)
    return store


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
    model: AbstractContentModel,
    name: str = None,
    namespace: str = None,
    min_text_length=10,
) -> typing.Generator[AbstractContentModel, AbstractContentModel, None]:
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

    page = requests.get(url=url, headers=DEFAULT_HEADERS)
    soup = BeautifulSoup(page.content, "html.parser")
    elements = soup.find_all(lambda tag: tag.name in ["h2", "p"])

    if not elements:
        # fallback - crude
        element = soup.find_all(lambda tag: tag.name in ["body"])
        for body in element:
            ft = model(name=url, content=body.text, document=url)
            yield ft
    else:
        current = "general"
        store_index = 0
        part_index = 0
        for element in elements:
            # track header and decide what to do
            if element.name == "h2":
                # check this conditions - wikipediaesque - just a simple hacky parser
                name = element.text.split("[")[0]
                if not len(name):
                    name = element.text.split("]")[-1]
                current = name
                store_index += 1
                part_index = 0
            elif current and element.text:
                part_index += 1
                key = name.replace(" ", "-") + "-" + str(part_index)
                if len(element.text) > min_text_length:
                    ft = model(name=key, content=element.text, doc_id=name)
                    yield ft


def _ingest_web_page(url: str, model: AbstractContentModel):
    """
    experimental simple page summarizer helper - dumb concatenation into max length
    """

    def concatenate_texts(texts, max_length=1e5):
        result = []
        current_text = ""
        for text in texts:
            if len(current_text) + len(text) + 1 <= max_length:
                if current_text:
                    current_text += " "
                current_text += text
            else:
                result.append(current_text)
                current_text = text
        if current_text:
            result.append(current_text)

        return result

    parts = [
        p.content
        for p in iterate_types_from_headed_paragraphs(
            url, model=model, name=url.split(":")[-1]
        )
    ]
    parts = concatenate_texts(parts)
    return parts


def ingest_page_to_model(
    url: str, model: AbstractContentModel, description: str = None
):
    data = _ingest_web_page(url, model=model)

    store = VectorDataStore(
        model, description=description or f"Data scraped from {url}"
    )
    records = []
    for i, record in enumerate(data):
        record = model(name=f"{url}_{i}", content=record, document=url)
        records.append(record)
    store.add(records)
    return store


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

    def __init__(
        self,
        site,
        prefix_filter=None,
        max_depth=7,
        model=None,
        fetch_pages=False,
        site_map_suffix="sitemap.xml",
    ):
        self._site_map = f"{site}/{site_map_suffix}"
        self._domain = site
        self._preview_filter = prefix_filter
        self._max_depth = max_depth
        self._visited = []
        self._model = model
        self._fetch_pages = fetch_pages
        self._found = []
        # temp
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        }

    def get_sitemap(self):
        resp = requests.get(self._site_map, headers=self._headers)
        if resp.status_code != 200:
            logger.warning(f"Failed to load {resp.status_code}")
        return resp.text

    def __iter__(self):
        for page in self.iterate_pages():
            yield page

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
                logger.debug(f"Received response from {sitemap_url}")

                if ".xml" in sitemap_url:
                    soup = BeautifulSoup(response.text, "xml")
                    urls = [
                        loc.text
                        for loc in soup.find_all("loc")
                        if sitemap_test or lame_file_test(loc.text)
                    ]
                else:
                    # we are going to jump straight as though we things its a page of links e.g. index.html
                    urls = [sitemap_url]

                # now we look deeper into sitemaps
                for url in urls:
                    if sitemap_test(url):
                        for f in self.find(url):
                            yield f
                    else:
                        for data in self.try_json_ld(
                            url,
                            depth=depth,
                        ):
                            yield data
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
            and (self._preview_filter or url) in url
        ):
            """
            If there is any JSON+LD (we dont care what) then retrieve it
            """
            text = BeautifulSoup(requests.get(url).text, "html.parser")
            data = text.find("script", {"type": "application/ld+json"})

            if data:
                data = json.loads("".join(data.contents))
                # returns the model if provided otherwise the raw
                logger.debug(f"Found {url} ")
                self._found.append(url)
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


def simple_scrape_links_into_model(
    url: str, model: AbstractContentModel, description=None
):
    """
    simple util to scrape some simple pages into the model

    url = 'http://www.paulgraham.com/articles.html'
    Model =    InstructEmbeddingContentModel.create_model('NewBookChapters')
    """
    records = []
    store = VectorDataStore(
        model, description=description or f"Data scraped from {url}"
    )
    logger.info(f"Scraping site...")
    for url, i, text in simple_scrape_links(url, model=model):
        if i % 100 == 0 and i > 0:
            logger.info(f"adding batch to store site...")
            store.add(records)
            records = []
        record = model(name=f"{url}_{i}", document=url, content=text)
        records.append(record)
    logger.info(f"adding final batch to store site...")
    store.add(records)
    return store


def simple_scrape_links(url: str, model: AbstractContentModel):
    """
    url = 'http://www.paulgraham.com/articles.html'

    """

    page = requests.get(url=url, headers=DEFAULT_HEADERS)
    soup = BeautifulSoup(page.content, "html.parser")
    elements = soup.find_all("a", href=True)
    urls = [urljoin(url, tag["href"]) for tag in elements]

    for url in urls:
        for i, part in enumerate(_ingest_web_page(url, model=model)):
            yield url, i, part


"""
SNIPPETS
"""


def load_example_foody_guides(
    limit=10,
):
    """

    loads new york guides data samples
    note the constructor/factory might be needed to map objects

    we can make this a general function but we need much better schema tools first (and schema migration tools)

    """
    from funkyprompt.io.tools.ingestion import SimpleJsonLDSpider
    from funkyprompt.model.entity import SchemaOrgVectorEntity

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


def ingest_site(
    model: AbstractContentModel,
    domain: str,
    site_map_or_index: str,
    prefix_filter: str = None,
):
    """
    without doing anything to complex, creating small snippets for use cases and will refactor later
    my switch to use other libraries but do not want to add too many deps in the short term

    **Args**
        name: the store to add the data to - can be specific to the site, category or very generic
        domain: the .com etc website to fetch from
        site_map_or_index: a link to site map or index to scrape links from
        prefix_filter: for example /blogs/ /recipes/ or something specific we are interested in
    """

    # this is a misnomer at the moment - json is a special case - we should use it if its useful
    s = SimpleJsonLDSpider(
        domain,
        prefix_filter=prefix_filter,
        site_map_suffix=site_map_or_index,
        fetch_pages=True,
    )
    for page in s:
        # for now we will use the found collection
        pass

    records = []
    for url in s._found:
        for i, p in enumerate(_ingest_web_page(url, model=model)):
            record = model(name=f"{url}_{i}", content=p, document=url)
            records.append(record)

    store = VectorDataStore(model)
    store.add(records)
    return store
