from funkyprompt.io.tools.downloader import get_page_json_ld_data
from funkyprompt import logger
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json


class SimpleJsonLDSpider:
    def __init__(self, site, prefix_filter, max_depth=7):
        self._site_map = f"{site}/sitemap.xml"
        self._domain = site
        self._preview_filter = prefix_filter
        self._max_depth = max_depth
        self._visited = []
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

    # def iterate_page_data(self, limit=None):
    #     for page in self.iterate_page_data(limit=limit):
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
                # data = json.loads(data.contents)
                if isinstance(data, list):
                    for d in data:
                        yield url, d
                else:
                    yield url, data
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
