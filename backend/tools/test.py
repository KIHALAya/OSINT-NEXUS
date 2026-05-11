import asyncio
import logging
from tools.apify_client import ApifyClient

# Setup minimal logging to see results
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    client = ApifyClient()
    
    # Better OSINT keywords as suggested by the user
    keywords = ["gabby petito", "#gabbypetito", "gabby petito update"]
    max_results = 5
    
    run_input = {
        "search": keywords,
        "resultsPerPage": max_results,
        "proxyCountryCode": "None",
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
    }
    
    logger.info(f"Running Apify TikTok scraper with input: {run_input}")
    
    try:
        items = await client.run_actor(
            actor_id="clockworks/tiktok-scraper",
            run_input=run_input
        )
        logger.info(f"Scraper returned {len(items)} items")
        if items:
            for i, item in enumerate(items[:3]):
                logger.info(f"Item {i+1}: {item.get('webVideoUrl')} - {item.get('text')[:50]}...")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
