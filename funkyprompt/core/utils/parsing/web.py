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
        
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return{
        'text' : soup.get_text(),
        'image': qualify(_primary_image(soup),bridge)
    }
