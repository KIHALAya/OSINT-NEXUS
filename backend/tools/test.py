import asyncio
from tools.apify_client import ApifyClient

async def main():
    client = ApifyClient()
    items = await client.run_actor(
        "clockworks/tiktok-scraper",
        {"resultsLimit": 3}
    )
    print(items)

asyncio.run(main())