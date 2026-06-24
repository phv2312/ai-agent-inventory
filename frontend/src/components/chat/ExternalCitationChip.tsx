import type { ReactNode } from 'react';
import type { LinkPreviewItem } from '../../services/api/linkPreviews';

const markdownExternalLinkRegex = /\[[^\]]*]\((https?:\/\/[^\s)]+)\)/gi;

export function normalizeExternalUrl(url: string | undefined): string | null {
    if (!url) return null;
    try {
        const parsed = new URL(url);
        if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
            return null;
        }
        parsed.hash = '';
        return parsed.toString();
    } catch {
        return null;
    }
}

export function extractExternalUrls(content: string): string[] {
    markdownExternalLinkRegex.lastIndex = 0;
    const urls: string[] = [];
    let match: RegExpExecArray | null = null;
    while ((match = markdownExternalLinkRegex.exec(content)) !== null) {
        const normalized = normalizeExternalUrl(match[1]);
        if (normalized) {
            urls.push(normalized);
        }
    }
    return Array.from(new Set(urls));
}

export function getHostname(url: string): string {
    try {
        return new URL(url).hostname;
    } catch {
        return url;
    }
}

export function getDomainChipText(url: string): string {
    const hostname = getHostname(url).replace(/^www\./i, '');
    const [first] = hostname.split('.');
    return (first || hostname || 'web').toLowerCase();
}


function formatPublishedDate(iso: string | null | undefined): string | null {
    if (!iso) return null;
    const parsed = new Date(iso);
    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
    });
}

interface ExternalCitationChipProps {
    href: string;
    domainText: string;
    label: string;
    preview?: LinkPreviewItem;
}

export function ExternalCitationChip({
    href,
    domainText,
    label,
    preview,
}: ExternalCitationChipProps) {
    const hostname = getHostname(href);
    const title = preview?.title || label || hostname;
    const publishedDate = formatPublishedDate(preview?.publishedAt);

    return (
        <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="group relative inline-flex align-middle mx-0.5 !no-underline"
            aria-label={`Open source ${domainText}: ${title}`}
        >
            <span className="relative inline-flex items-center rounded-sm border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-1.5 py-0.5 text-[9px] font-semibold leading-none text-[var(--color-text-muted)] transition-colors group-hover:border-[var(--color-primary)] group-hover:text-[var(--color-primary)]">
                {domainText}
            </span>
            <span className="pointer-events-none absolute left-1/2 top-full z-20 flex w-72 -translate-x-1/2 flex-col gap-2 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-3 shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity">
                <span className="min-w-0 truncate text-xs text-[var(--color-text-muted)]">
                    {domainText}
                </span>
                <span className="text-sm font-semibold leading-snug text-[var(--color-text)]">
                    {title}
                </span>
                {publishedDate ? (
                    <span className="text-xs text-[var(--color-text-muted)]">
                        {publishedDate}
                    </span>
                ) : null}
            </span>
        </a>
    );
}

export function asLinkLabel(children: ReactNode): string {
    if (typeof children === 'string') return children;
    if (typeof children === 'number') return String(children);
    if (Array.isArray(children)) {
        return children.map((child) => asLinkLabel(child)).join('');
    }
    return '';
}
