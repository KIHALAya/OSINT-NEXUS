"""
tests/test_tiktok_search.py
Run with: pytest tests/test_tiktok_search.py -v
"""
import pytest
from unittest.mock import AsyncMock, patch
from tools.tiktok_search import TikTokScraper, TikTokPost


MOCK_APIFY_ITEM = {
    "id": "7334455221133",
    "webVideoUrl": "https://www.tiktok.com/@user/video/7334455221133",
    "text": "رأيت فتاة تشبهها بالقرب من المول #missing #morocco",
    "authorMeta": {
        "id": "author_001",
        "name": "user_test",
        "fans": 1200,
        "verified": False,
    },
    "diggCount": 450,
    "shareCount": 89,
    "commentCount": 34,
    "playCount": 12000,
    "createTimeISO": "2024-01-15T14:30:00Z",
    "hashtags": [{"name": "missing"}, {"name": "morocco"}],
    "mentions": [],
    "musicMeta": {"musicName": "original sound"},
}


class TestTikTokScraper:

    @pytest.mark.asyncio
    async def test_search_returns_mapped_posts(self):
        with patch("tools.tiktok_search.ApifyClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.run_actor = AsyncMock(return_value=[MOCK_APIFY_ITEM])

            scraper = TikTokScraper()
            scraper._client = mock_instance
            posts = await scraper.search(keywords=["morocco missing"], max_results=10)

        assert len(posts) == 1
        post = posts[0]
        assert post.post_id == "7334455221133"
        assert post.likes == 450
        assert post.shares == 89
        assert "missing" in post.hashtags
        assert post.engagement_score > 0

    @pytest.mark.asyncio
    async def test_map_handles_missing_fields(self):
        minimal_item = {"id": "999", "text": "test", "authorMeta": {"id": "a1", "name": "u1"}}
        post = TikTokScraper._map_to_post(minimal_item)
        assert post.post_id == "999"
        assert post.likes == 0
        assert post.hashtags == []

    def test_content_hash_is_deterministic(self):
        post1 = TikTokScraper._map_to_post({**MOCK_APIFY_ITEM})
        post2 = TikTokScraper._map_to_post({**MOCK_APIFY_ITEM})
        assert post1.content_hash == post2.content_hash

    def test_engagement_score_calculation(self):
        post = TikTokScraper._map_to_post(MOCK_APIFY_ITEM)
        expected = round((450 + 89 * 3 + 34 * 2) / 12000 * 1000, 4)
        assert post.engagement_score == expected