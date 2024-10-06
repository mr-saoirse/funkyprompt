import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from funkyprompt.core.utils import logger

def _primary_image(soup):
    """a common format for finding a representative image"""
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        return og_image['content']

    images = soup.find_all('img')
    if not images:
        return None

    largest_image = max(
        images,
        key=lambda img: int(img.get('width', 0)) * int(img.get('height', 0))
    )
 
    return largest_image.get('src')

def scrape_text(url):
    """
    simple text scraper - using this for primitive visit semantics
    test cases;
    
    
    """
    original_url = url
    def qualify(s, bridge='/'):
        """if images are not absolute, a lame attempt to make them so"""
        if original_url not in s:
            return f"{original_url.lstrip('/')}{bridge}{s.rstrip('/')}"
        
    url_parsed = urlparse(url)    
    if url_parsed.netloc == 'github.com':
        bridge = '/tree/main/'
        """a lame way to check for readme variants to replace the thing"""
        for r in ['README', 'Readme']:
            url_temp = f"{url_parsed.scheme}://raw.githubusercontent.com{url_parsed.path}/main/{r}.md"        
            response = requests.head(url, allow_redirects=True)
            if response.status_code == 200:
                url = url_temp
                logger.debug(f"Using url {url}")
                break
        
    soup = get_soup(url)
    return{
        'text' : soup.get_text(),
        #'image': qualify(_primary_image(soup))
    }


def get_soup(url:str):
    """"""
    
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://google.com', 
    }
    
    if url[0] == '/':
        with open(url, 'r', encoding='utf-8') as file:
            html_content = file.read()
    else:
        response = requests.get(url, headers=headers)
        html_content = response.text
        
    return BeautifulSoup(html_content, 'html.parser')
    

