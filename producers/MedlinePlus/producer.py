import asyncio
import urllib.parse
import string
import aiohttp
from bs4 import BeautifulSoup
from scrappers.MedlinePlus.scrapper import fetch_disease_data


class EncyclopediaScraper:
    def __init__(self, queue: asyncio.Queue, producer_count: int = 3):
        self.queue = queue
        self.producer_count = producer_count
        self.alphabet_urls = []
        self.valid_urls = []

    def get_base_url(self, base_url="https://medlineplus.gov/ency/"):
        return base_url.rstrip('/')  # Remove trailing slash if present

    def generate_alphabetical_urls(self, base_url=None):
        if base_url is None:
            base_url = self.get_base_url()

        # Generate URLs for each uppercase letter
        url_mapping = {}
        for letter in string.ascii_uppercase:
            resource_path = f"encyclopedia_{letter}.htm"
            full_url = f"{base_url}/{resource_path}"
            url_mapping[letter] = full_url

        return url_mapping

    def is_valid_url(self, url):
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def filter_valid_urls(self, urls, valid_only=True):
        if valid_only:
            return {letter: url for letter, url in urls.items() if self.is_valid_url(url)}
        return urls

    async def fetch_links_from_page(self, url, ul_id="index", base_url="https://medlineplus.gov/ency"):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        soup = BeautifulSoup(html_content, 'html.parser')
                        ul_element = soup.find('ul', id=ul_id)

                        if ul_element:
                            links = []
                            for link in ul_element.find_all('a', href=True):
                                href = link['href']
                                # Check if the link matches the pattern and prepend the base URL
                                if href.startswith("article/") and href.endswith(".htm"):
                                    full_url = f"{base_url}/{href.lstrip('/')}"
                                    links.append(full_url)
                            return links
                        else:
                            print(f"UL element with '{ul_id}' not found")
                            return None
                    else:
                        print(f"Error in http status for url '{url}' ")
                        return None
        except aiohttp.ClientError as e:
            print(f"Error fetching URL: {e}")
            return None

    async def produce_links(self, alphabet_url: str):
        disease_links = await self.fetch_links_from_page(alphabet_url)
        if disease_links:  # Check if the list is not None or empty
            for link in disease_links:
                # Add each disease link to the queue
                await self.queue.put((link, fetch_disease_data))
                print(f"Added to queue: '{link}' ")

    async def start_scraping(self):
        """Starts multiple scraping tasks concurrently"""
        # Create producer tasks
        scraping_tasks = [
            asyncio.create_task(self.produce_links(url))
            for url in self.valid_urls.values()
        ]

        # Wait for all scraping tasks to finish
        await asyncio.gather(*scraping_tasks)

        # Signal that production is complete
        await self.queue.put(None)  # Sentinel value
