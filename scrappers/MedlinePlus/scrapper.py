import aiohttp
from bs4 import BeautifulSoup
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


async def fetch_disease_data(url):
    """
    Fetches and formats medical condition information from MedlinePlus asynchronously.

    Args:
        url (str): The MedlinePlus URL for the medical condition

    Returns:
        str: Formatted medical documentation
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                return "Failed to retrieve the page"

            html_content = await response.text()

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
