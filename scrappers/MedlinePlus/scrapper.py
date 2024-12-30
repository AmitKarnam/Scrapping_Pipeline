import aiohttp
from aiohttp import ClientError, ClientResponseError
from bs4 import BeautifulSoup
import asyncio
import re

USER_RELEVANT_HEADERS = [
    "alternative names", "causes", "symptoms",
    "treatment", "exams and tests", "diagnosis",
    "prevention", "possible complications"
]


def clean_and_format_text(text):
    """
    Clean and format text by properly separating and formatting list items.
    """
    text = ' '.join(text.split())

    if "may include:" in text.lower():
        prefix, items = text.split("may include:", 1)
        items = re.split('(?=[A-Z])', items.strip())
        items = [item.strip() for item in items if item.strip()]
        formatted_items = '\n    • '.join(items)
        return f"{prefix.strip()} may include:\n    • {formatted_items}"

    if text.startswith("•") or text.startswith("-"):
        items = re.split('(?:•|-)', text)
        items = [item.strip() for item in items if item.strip()]
        return '\n    • '.join(items)

    return text


async def fetch_disease_data(url, max_retries=3, backoff_factor=1):
    """
    Fetches and formats medical condition information from MedlinePlus asynchronously.

    Args:
        url (str): The MedlinePlus URL for the medical condition
        max_retries (int): The maximum number of retry attempts
        backoff_factor (int): The backoff factor for exponential backoff

    Returns:
        str: Formatted medical documentation
    """
    retry_attempts = 0

    while retry_attempts < max_retries:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        raise ClientResponseError(
                            response.request_info, response.history,
                            status=response.status, message="HTTP error"
                        )

                    html_content = await response.text()

            # If successful, parse and return the content
            soup = BeautifulSoup(html_content, "html.parser")

            # Document structure
            documentation = []

            # Disease name
            disease_name = soup.find("h1").get_text(strip=True)
            documentation.append(disease_name.upper())
            documentation.append("")  # Empty line for spacing

            # Summary
            summary_div = soup.find('div', {'id': 'ency_summary'})
            if summary_div:
                documentation.append("OVERVIEW")
                documentation.append(summary_div.get_text(strip=True))
                documentation.append("")

            # Sections
            sections = {}
            current_header = None
            content = []

            for element in soup.find_all(['h2', 'p', 'ul']):
                if element.name == 'h2':
                    if current_header and current_header.lower() in USER_RELEVANT_HEADERS:
                        sections[current_header] = '\n'.join(content)
                    current_header = element.get_text(strip=True)
                    content = []
                else:
                    if element.name == 'ul':
                        list_items = element.find_all('li')
                        content.extend(
                            [f"    • {item.get_text(strip=True)}" for item in list_items])
                    else:
                        text = clean_and_format_text(element.get_text(strip=True))
                        if text:
                            content.append(text)

            if current_header and current_header.lower() in USER_RELEVANT_HEADERS:
                sections[current_header] = '\n'.join(content)

            # Add sections to documentation
            for header, body in sections.items():
                if any(keyword in header.lower() for keyword in USER_RELEVANT_HEADERS):
                    documentation.append(header.upper())
                    documentation.append(body)
                    documentation.append("")  # Empty line for spacing

            return '\n'.join(documentation)

        except (ClientError, asyncio.TimeoutError) as e:
            retry_attempts += 1
            wait_time = backoff_factor * (2 ** (retry_attempts - 1))
            print(
                f"Attempt {retry_attempts}/{max_retries}: Failed to fetch data from {url}. Retrying in {wait_time} seconds... [Error: {e}]"
            )
            await asyncio.sleep(wait_time)

    return f"Failed to retrieve the page after {max_retries} attempts."