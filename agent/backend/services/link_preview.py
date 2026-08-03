from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Union
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from cachetools import TTLCache


logger = logging.getLogger(__name__)

_LINK_PREVIEW_CACHE: TTLCache[str, LinkPreviewItem] = TTLCache(
    maxsize=2048,
    ttl=1800,
)

_MAX_BYTES = 512 * 1024
_MAX_REDIRECTS = 3
_HTTP_TIMEOUT = 5.0


@dataclass
class LinkPreviewItem:
    url: str
    title: str | None = None
    description: str | None = None
    image: str | None = None
    favicon: str | None = None
    site_name: str | None = None
    published_at: str | None = None


class LinkPreviewService:
    async def get_many(self, urls: list[str]) -> list[LinkPreviewItem]:
        normalized_urls: list[str] = []
        for url in urls:
            normalized = self._normalize_url(url)
            if normalized:
                normalized_urls.append(normalized)

        unique_urls = list(dict.fromkeys(normalized_urls))
        if not unique_urls:
            return []

        cached: list[LinkPreviewItem] = []
        to_fetch: list[str] = []
        for url in unique_urls:
            cached_item = _LINK_PREVIEW_CACHE.get(url)
            if cached_item is not None:
                cached.append(cached_item)
            else:
                to_fetch.append(url)

        fetched: list[LinkPreviewItem] = []
        if to_fetch:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=_HTTP_TIMEOUT,
                max_redirects=_MAX_REDIRECTS,
                headers={"User-Agent": "agent-api-link-preview/1.0"},
            ) as client:
                fetched = list(
                    await asyncio.gather(
                        *[
                            self._fetch_preview(client=client, url=url)
                            for url in to_fetch
                        ],
                        return_exceptions=False,
                    )
                )
                for item in fetched:
                    _LINK_PREVIEW_CACHE[item.url] = item

        by_url = {item.url: item for item in [*cached, *fetched]}
        return [by_url[url] for url in unique_urls if url in by_url]

    def _normalize_url(self, raw_url: str) -> str | None:
        parsed = urlparse(raw_url.strip())
        if parsed.scheme not in ("http", "https"):
            return None
        if not parsed.netloc:
            return None
        return parsed._replace(fragment="").geturl()

    async def _fetch_preview(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> LinkPreviewItem:
        if not await self._is_safe_url(url):
            logger.warning("Blocked unsafe URL for preview: %s", url)
            return LinkPreviewItem(url=url)

        final_url = url
        try:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                final_url = str(response.url)
                if not await self._is_safe_url(final_url):
                    logger.warning(
                        "Blocked redirected unsafe URL for preview: %s",
                        final_url,
                    )
                    return LinkPreviewItem(url=url)

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type.lower():
                    return LinkPreviewItem(url=url)

                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) > _MAX_BYTES:
                        break

        except Exception as err:  # noqa: BLE001
            logger.warning("Failed to fetch preview for %s: %s", url, err)
            return LinkPreviewItem(url=url)

        html = content.decode("utf-8", errors="ignore")
        return self._extract_preview(
            url=url,
            html=html,
            base_url=final_url,
        )

    def _extract_preview(
        self,
        url: str,
        html: str,
        base_url: str,
    ) -> LinkPreviewItem:
        soup = BeautifulSoup(html, "html.parser")

        title = self._meta_content(soup, "property", "og:title")
        if not title and soup.title:
            title = soup.title.get_text(strip=True)

        description = self._meta_content(soup, "property", "og:description")
        if not description:
            description = self._meta_content(soup, "name", "description")

        site_name = self._meta_content(soup, "property", "og:site_name")
        if not site_name:
            site_name = self._meta_content(soup, "name", "application-name")

        published_at = self._meta_content(soup, "property", "article:published_time")
        if not published_at:
            published_at = self._meta_content(soup, "property", "og:published_time")
        if not published_at:
            published_at = self._meta_content(soup, "name", "pubdate")

        image = self._meta_content(soup, "property", "og:image")
        image_url = self._join_url(base_url, image)

        icon = self._find_icon_href(soup)
        favicon_url = self._join_url(base_url, icon)
        if not favicon_url:
            favicon_url = self._fallback_favicon(base_url)

        return LinkPreviewItem(
            url=url,
            title=self._clip(title, max_len=160),
            description=self._clip(description, max_len=300),
            image=image_url,
            favicon=favicon_url,
            site_name=self._clip(site_name, max_len=80),
            published_at=published_at,
        )

    def _meta_content(
        self,
        soup: BeautifulSoup,
        attr_name: str,
        attr_value: str,
    ) -> str | None:
        tag = soup.find("meta", attrs={attr_name: attr_value})
        if not tag:
            return None
        content = tag.get("content")
        if not isinstance(content, str):
            return None
        text = content.strip()
        return text or None

    def _find_icon_href(self, soup: BeautifulSoup) -> str | None:
        for tag in soup.find_all("link"):
            rel_value = tag.get("rel")
            if isinstance(rel_value, str):
                rel_tokens = rel_value.lower().split()
            elif isinstance(rel_value, list):
                rel_tokens = [str(token).lower() for token in rel_value]
            else:
                rel_tokens = []

            rel_joined = " ".join(rel_tokens)
            if "icon" not in rel_tokens and "apple-touch-icon" not in rel_joined:
                continue

            href = tag.get("href")
            if isinstance(href, str) and href.strip():
                return href.strip()
        return None

    def _join_url(self, base_url: str, path_or_url: str | None) -> str | None:
        if not path_or_url:
            return None
        return urljoin(base_url, path_or_url)

    def _fallback_favicon(self, url: str) -> str | None:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            return None
        return f"{parsed.scheme}://{parsed.hostname}/favicon.ico"

    def _clip(self, text: str | None, max_len: int) -> str | None:
        if not text:
            return None
        trimmed = " ".join(text.split())
        if len(trimmed) <= max_len:
            return trimmed
        return f"{trimmed[: max_len - 1]}…"

    async def _is_safe_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname
        if not host:
            return False

        lowered = host.lower()
        if lowered in {"localhost"} or lowered.endswith(".localhost"):
            return False

        try:
            ip_obj = ipaddress.ip_address(host)
            return self._is_public_ip(ip_obj)
        except ValueError:
            pass

        try:
            infos = await asyncio.to_thread(
                socket.getaddrinfo,
                host,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except OSError:
            return False

        for info in infos:
            sockaddr = info[4]
            if not sockaddr:
                continue
            ip_str = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                return False
            if not self._is_public_ip(ip_obj):
                return False
        return True

    def _is_public_ip(
        self,
        ip_obj: Union[ipaddress.IPv4Address, ipaddress.IPv6Address],
    ) -> bool:
        return not (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )
