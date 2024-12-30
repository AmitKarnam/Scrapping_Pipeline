import asyncio
from producers.MedlinePlus.producer import EncyclopediaScraper


async def monitor_queue(queue: asyncio.Queue):
    """Monitors and prints queue size periodically"""
    while True:
        print(f"Current queue size: {queue.qsize()}")
        await asyncio.sleep(1)


async def consume_data(queue: asyncio.Queue):
    while True:
        item = await queue.get()
        if item is None:  # Sentinel value to indicate completion
            break

        # Unpack the tuple
        disease_url, scrape_function = item

        # Call the scraping function with the disease URL
        result = await scrape_function(disease_url)

        # Instead of printing we'll need to add it to the output queue
        print(f"Consumed and processed: {result}")

        queue.task_done()  # Notify that the task is complete


async def main():
    # Create queue with max size of 10
    queue = asyncio.Queue(maxsize=10)

    # Create scraper
    scraper = EncyclopediaScraper(queue, producer_count=26)

    # Generate and Validate URLs for each letter of diseases
    scraper.alphabet_urls = scraper.generate_alphabetical_urls()
    scraper.valid_urls = scraper.filter_valid_urls(scraper.alphabet_urls)

    # Start queue monitoring in background
    monitor_task = asyncio.create_task(monitor_queue(queue))

    # Start Consumers for the produced data in queue
    consumer_task = asyncio.create_task(consume_data(queue))

    # Start scraping
    await scraper.start_scraping()

    # Cancel monitoring once scraping is complete
    monitor_task.cancel()

    # Stop the consumer
    await queue.put(None)  # Add sentinel value for consumer to stop
    await consumer_task

    # Print final queue contents
    print("\nFinal queue contents:")
    while not queue.empty():
        item = await queue.get()
        if item is None:  # Skip sentinel value
            continue
        print(f"Queue item: {item}")


if __name__ == "__main__":
    asyncio.run(main())
