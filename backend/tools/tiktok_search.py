import hashlib 
import logging
from typing import Any
from langchain_core.tools import tool 
from pydantic import BaseModel ,Field

from core.config import get_settings
from tools.apify_client import ApifyClient, ApifyError

logger = logging.getLogger(__name__)

class TikTokPost(BaseModel):
    post_id: str
    url: str
    text: str                       # caption / description
    author_id: str
    author_name: str
    author_followers: int = 0
    author_verified: bool = False
    likes: int = 0
    comments: int = 0
    shares: int = 0
    plays: int = 0
    posted_at: str | None = None    # ISO 8601 string
    hashtags: list[str] = []
    mentions: list[str] = []
    music_title: str | None = None
    thumbnail_url: str | None = None
    # Computed fields
    engagement_score: float = 0.0   # (likes + shares*3 + comments*2) / max(plays,1) * 1000
    content_hash: str = ""          # sha256 of text — for dedup across platforms

class TikTokSearchResult(BaseModel):
    query: str
    case_id: str
    posts: list[TikTokPost]
    total_found: int
    apify_actor_used: str
    error: str | None = None 

class TikTokSearchInput(BaseModel):
    case_id: str = Field(description="Investigation case ID, e.g. CASE-2024-0847")
    keywords: list[str] = Field(
        description=(
            "Search terms in any language. Use the subject's name, location, "
            "and descriptive phrases. Arabic/French/Darija all work. "
            "Example: ['john doe missing', 'chicago missing person', 'missing silver alert']"
        )
    )
    max_results: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Max posts to retrieve. Keep ≤ 50 during investigation to stay within Apify limits.",
    )
    date_from: str | None = Field(
        default=None,
        description="Only return posts from this date onward. ISO format: '2024-01-15'",
    )

class TikTokScraper:
    """
    Wraps the Apify clockworks/tiktok-scraper actor.
    Can be used directly in tests or other services without the @tool wrapper.
    """
 
    def __init__(self):
        self._client = ApifyClient()
        self._settings = get_settings()
 
    async def search(
        self,
        keywords: list[str],
        max_results: int = 30,
        date_from: str | None = None,
    ) -> list[TikTokPost]:
        """
        Searches TikTok for posts matching the given keywords.
 
        The clockworks/tiktok-scraper actor treats keywords as hashtag
        searches internally. We pass them under both `hashtags` and
        `keywords` fields since the actor's behaviour changed across
        versions — providing both ensures compatibility.
 
        proxyConfiguration is important: TikTok blocks datacenter IPs.
        Using Apify's residential proxy pool significantly improves
        success rate. "useApifyProxy": true is free within your plan.
        """
        run_input: dict[str, Any] = {
            # Search inputs — provide both to handle actor version differences
            "hashtags": keywords,
            "keywords": keywords,
 
            # Limit — actor respects this per search term, so total
            # results may be up to len(keywords) * resultsLimit
            "resultsLimit": max(1, max_results // max(len(keywords), 1)),
 
            # Use Apify residential proxies — critical for TikTok
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
 
            # Only collect public data
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
            "shouldDownloadSubtitles": False,
        }
 
        if date_from:
            run_input["dateFrom"] = date_from
 
        raw_items = await self._client.run_actor(
            actor_id=self._settings.APIFY_ACTOR_TIKTOK,
            run_input=run_input,
        )
 
        posts = []
        for item in raw_items:
            try:
                post = self._map_to_post(item)
                posts.append(post)
            except Exception as e:
                logger.warning(f"Failed to map TikTok item: {e} | item_keys={list(item.keys())}")
 
        logger.info(f"TikTok search complete keywords={keywords} posts={len(posts)}")
        return posts
 
    @staticmethod
    def _map_to_post(item: dict[str, Any]) -> TikTokPost:
        """
        Maps raw Apify clockworks/tiktok-scraper output to TikTokPost.
 
        Apify's TikTok scraper returns fields like:
          id, webVideoUrl, text, authorMeta{}, musicMeta{},
          diggCount (likes), shareCount, playCount, commentCount,
          createTimeISO, hashtags[], mentions[]
 
        Field names can shift between actor versions — we use .get()
        everywhere and provide safe defaults.
        """
        author = item.get("authorMeta", {})
        stats = item  # top-level for engagement stats
 
        text = item.get("text", "") or ""
 
        # Compute content hash for cross-platform dedup
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
 
        likes = int(stats.get("diggCount", 0) or 0)
        shares = int(stats.get("shareCount", 0) or 0)
        comments = int(stats.get("commentCount", 0) or 0)
        plays = int(stats.get("playCount", 0) or 0)
 
        engagement_score = round(
            (likes + shares * 3 + comments * 2) / max(plays, 1) * 1000, 4
        )
 
        # Extract hashtags — Apify returns them as list of {name: str} objects
        # or sometimes as plain strings depending on actor version
        raw_hashtags = item.get("hashtags", []) or []
        hashtags = []
        for h in raw_hashtags:
            if isinstance(h, dict):
                hashtags.append(h.get("name", ""))
            elif isinstance(h, str):
                hashtags.append(h.lstrip("#"))
 
        raw_mentions = item.get("mentions", []) or []
        mentions = []
        for m in raw_mentions:
            if isinstance(m, dict):
                mentions.append(m.get("name", ""))
            elif isinstance(m, str):
                mentions.append(m.lstrip("@"))
 
        music = item.get("musicMeta", {}) or {}
 
        return TikTokPost(
            post_id=str(item.get("id", "")),
            url=item.get("webVideoUrl", "") or "",
            text=text,
            author_id=str(author.get("id", "")),
            author_name=author.get("name", "") or "",
            author_followers=int(author.get("fans", 0) or 0),
            author_verified=bool(author.get("verified", False)),
            likes=likes,
            comments=comments,
            shares=shares,
            plays=plays,
            posted_at=item.get("createTimeISO"),
            hashtags=[h for h in hashtags if h],
            mentions=[m for m in mentions if m],
            music_title=music.get("musicName"),
            thumbnail_url=item.get("covers", {}).get("default") if item.get("covers") else None,
            engagement_score=engagement_score,
            content_hash=content_hash,
        )
 
 
@tool(args_schema=TikTokSearchInput)
async def search_tiktok(
    case_id: str,
    keywords: list[str],
    max_results: int = 30,
    date_from: str | None = None,
) -> TikTokSearchResult:
    """
    Search TikTok for posts related to a missing persons investigation.
 
    Use this tool when:
    - You need to find crowd sightings or tips posted on TikTok
    - The case involves a young person (TikTok's primary demographic)
    - You want to cross-reference claims found on other platforms
    - You need to check if viral misinformation is spreading on TikTok
 
    The tool searches by keyword and hashtag simultaneously.
    Results include engagement metrics, which the scoring agent uses
    to compute crowd credibility scores.
 
    Always pass the case_id so results can be traced back to the case.
    """
    settings = get_settings()
    scraper = TikTokScraper()
 
    try:
        posts = await scraper.search(
            keywords=keywords,
            max_results=max_results,
            date_from=date_from,
        )
        return TikTokSearchResult(
            query=" | ".join(keywords),
            case_id=case_id,
            posts=posts,
            total_found=len(posts),
            apify_actor_used=settings.apify_actor_tiktok,
        )
 
    except ApifyError as e:
        logger.error(f"TikTok search failed case={case_id}: {e}")
        return TikTokSearchResult(
            query=" | ".join(keywords),
            case_id=case_id,
            posts=[],
            total_found=0,
            apify_actor_used=settings.apify_actor_tiktok,
            error=str(e),
        )
 