import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Final, Literal
from crawl4ai import (
    AsyncWebCrawler,
    CacheMode,
    CrawlResult,
    BrowserConfig,
    CrawlerRunConfig,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import (
    DuckDuckGoSearchException,
    RatelimitException,
)
from pydantic import BaseModel


class DuckduckgoConfigs(BaseModel):
    region: Literal["vn-vn"] = "vn-vn"
    timelimit: Literal["d", "w", "m", "y"] = "w"
    backend: Literal["html", "lite", "auto"] = "html"


class SearchURL(BaseModel):
    title: str
    href: str


class SearchResult(SearchURL):
    markdown: str | None = None


class WebReaderConfig(BaseModel):
    text_mode: bool = True
    word_count_threshold: int = 100
    exclude_external_links: bool = True
    exclude_internal_links: bool = True


class WebReader:
    def __init__(self, configs: WebReaderConfig | None = None) -> None:
        self.configs = configs or WebReaderConfig()

    @property
    def browser_config(self) -> BrowserConfig:
        return BrowserConfig(
            text_mode=self.configs.text_mode,
            headless=True,
        )

    @property
    def run_config(self) -> CrawlerRunConfig:
        return CrawlerRunConfig(
            exclude_external_links=self.configs.exclude_external_links,
            exclude_internal_links=self.configs.exclude_internal_links,
            word_count_threshold=self.configs.word_count_threshold,
            magic=True,
            cache_mode=CacheMode.BYPASS,
        )

    async def aread(self, search_url: SearchURL) -> SearchResult:
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result: CrawlResult = await crawler.arun(
                url=search_url.href,
                config=self.run_config,
            )

            params = {**search_url.model_dump(), "markdown": result.markdown}

            return SearchResult.model_validate(params)


class DuckduckgoWebSearch:
    STOP_AFTER_ATTEMPT: Final[int] = 3
    EXPONENTIAL_MULTIPLIER: Final[int] = 4
    EXPONENTIAL_MIN: Final[int] = 5
    EXPONENTIAL_MAX: Final[int] = 15

    def __init__(
        self,
        executor: ThreadPoolExecutor | None = None,
        configs: DuckduckgoConfigs | None = None,
        web_reader: WebReader | None = None,
    ) -> None:
        self.executor = executor or ThreadPoolExecutor()
        self.configs = configs or DuckduckgoConfigs()
        self.web_reader = web_reader or WebReader()

    async def parse_web_content(self, searched_result: SearchURL) -> SearchResult:
        markdown = await self.web_reader.aread(searched_result)
        return SearchResult.model_validate(
            {**searched_result.model_dump(), "markdown": markdown.markdown}
        )

    @retry(
        stop=stop_after_attempt(STOP_AFTER_ATTEMPT),
        wait=wait_exponential(
            multiplier=EXPONENTIAL_MULTIPLIER, min=EXPONENTIAL_MIN, max=EXPONENTIAL_MAX
        ),
        retry=retry_if_exception_type(DuckDuckGoSearchException | RatelimitException),
        reraise=True,
    )
    async def asearch(
        self,
        query: str,
        topk: int = 5,
        *args: str,
        **kwargs: str,
    ) -> list[SearchResult]:
        loop = asyncio.get_event_loop()
        searched_urls = await loop.run_in_executor(
            self.executor,
            self._search,
            query,
            topk,
        )

        searched_results = await asyncio.gather(
            *[self.web_reader.aread(result) for result in searched_urls]
        )

        return list(
            filter(lambda result: result.markdown is not None, searched_results)
        )

    def _search(self, query: str, topk: int = 5) -> list[SearchURL]:
        with DDGS() as ddgs:
            results = ddgs.text(
                query,
                region=self.configs.region,
                timelimit=self.configs.timelimit,
                # backend=self.configs.backend,
                max_results=topk,
            )
            return [SearchURL.model_validate(result) for result in results]
