import { apiFetch } from './client';

export interface LinkPreviewItem {
    url: string;
    title: string | null;
    description: string | null;
    image: string | null;
    favicon: string | null;
    siteName: string | null;
    publishedAt: string | null;
}

interface LinkPreviewResponse {
    items: LinkPreviewItem[];
}

const linkPreviewCache = new Map<string, LinkPreviewItem>();
const pendingLinkPreviewRequests = new Map<string, Promise<LinkPreviewItem>>();

export async function getLinkPreviews(
    urls: string[],
): Promise<Record<string, LinkPreviewItem>> {
    const uniqueUrls = Array.from(new Set(urls));
    const result: Record<string, LinkPreviewItem> = {};

    const missing: string[] = [];
    for (const url of uniqueUrls) {
        const cached = linkPreviewCache.get(url);
        if (cached) {
            result[url] = cached;
        } else {
            missing.push(url);
        }
    }

    if (missing.length === 0) {
        return result;
    }

    const stillMissing = missing.filter((url) => !pendingLinkPreviewRequests.has(url));
    let batchPromise: Promise<Record<string, LinkPreviewItem>> | null = null;

    if (stillMissing.length > 0) {
        batchPromise = apiFetch<LinkPreviewResponse>('/api/v1/chats/link-previews', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ urls: stillMissing }),
        }).then((response) => {
            const map: Record<string, LinkPreviewItem> = {};
            for (const item of response.items) {
                linkPreviewCache.set(item.url, item);
                map[item.url] = item;
            }
            return map;
        }).finally(() => {
            for (const url of stillMissing) {
                pendingLinkPreviewRequests.delete(url);
            }
        });

        for (const url of stillMissing) {
            pendingLinkPreviewRequests.set(
                url,
                batchPromise.then((map) => map[url] ?? {
                    url,
                    title: null,
                    description: null,
                    image: null,
                    favicon: null,
                    siteName: null,
                    publishedAt: null,
                }),
            );
        }
    }

    await Promise.all(uniqueUrls.map(async (url) => {
        const cached = linkPreviewCache.get(url);
        if (cached) {
            result[url] = cached;
            return;
        }

        const pending = pendingLinkPreviewRequests.get(url);
        if (!pending) return;

        const resolved = await pending;
        linkPreviewCache.set(url, resolved);
        result[url] = resolved;
    }));

    return result;
}
