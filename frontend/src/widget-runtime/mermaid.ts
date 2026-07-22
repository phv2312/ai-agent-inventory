import { showError } from './errors';
import { buildMermaidThemeVariables } from './mermaid-theme';
import { resolveMount } from './mount';
import {
    MAX_MERMAID_SOURCE_CHARS,
    MERMAID_RENDER_DEBOUNCE_MS,
    type MermaidOptions,
} from './types';

const MERMAID_JS_CDN =
    'https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.3/mermaid.min.js';

interface MermaidApi {
    initialize(config: Record<string, unknown>): void;
    render(
        id: string,
        source: string,
    ): Promise<{ svg: string }>;
}

let mermaidJsPromise: Promise<void> | null = null;
let mermaidInitialized = false;
let renderCounter = 0;
let renderDebounceTimer: ReturnType<typeof setTimeout> | null = null;
let lastSource = '';
let pendingMount: HTMLElement | null = null;
let pendingTitle: string | undefined;

/** Test-only reset for module singletons. */
export function resetMermaidRuntimeForTests(): void {
    mermaidJsPromise = null;
    mermaidInitialized = false;
    renderCounter = 0;
    if (renderDebounceTimer) {
        clearTimeout(renderDebounceTimer);
    }
    renderDebounceTimer = null;
    lastSource = '';
    pendingMount = null;
    pendingTitle = undefined;
    delete (window as { mermaid?: MermaidApi }).mermaid;
}

export function validateMermaidSource(source: string): string | null {
    if (!source || !source.trim()) {
        return 'Mermaid source is empty';
    }
    if (source.length > MAX_MERMAID_SOURCE_CHARS) {
        return 'Mermaid source too large';
    }
    return null;
}

/** Quote rectangle node labels that contain characters Mermaid parses badly. */
const _MERMAID_LABEL_QUOTE_CHARS = /[()+,#/]|\n|\\n/;

export function normalizeMermaidSource(source: string): string {
    return source.replace(
        /(\b[A-Za-z][\w-]*)\[([^\]"]+)\]/g,
        (match, id: string, label: string) => {
            if (!_MERMAID_LABEL_QUOTE_CHARS.test(label)) {
                return match;
            }
            const escaped = label.replace(/"/g, '\\"');
            return `${id}["${escaped}"]`;
        },
    );
}

/** Best-effort node count for flowchart/graph/sequence/ER sources (prompt guidance only). */
export function countMermaidNodes(source: string): number | null {
    const trimmed = source.trim();
    if (!trimmed) {
        return 0;
    }
    const header = trimmed.split('\n')[0]?.trim().toLowerCase() ?? '';

    if (header.startsWith('sequencediagram')) {
        const participants = trimmed.match(/^\s*participant\s+/gim);
        return participants?.length ?? 0;
    }

    if (header.startsWith('erdiagram')) {
        const entities = new Set<string>();
        for (const match of trimmed.matchAll(
            /\b([A-Za-z][\w]*)\s*\{/g,
        )) {
            entities.add(match[1]);
        }
        return entities.size;
    }

    if (header.startsWith('flowchart') || header.startsWith('graph')) {
        const ids = new Set<string>();
        const skip = new Set([
            'subgraph',
            'end',
            'flowchart',
            'graph',
            'click',
            'style',
            'class',
            'classDef',
            'linkStyle',
            'direction',
        ]);

        for (const line of trimmed.split('\n')) {
            const trimmedLine = line.trim();
            if (!trimmedLine || trimmedLine.startsWith('%%')) {
                continue;
            }
            if (/^subgraph\s/i.test(trimmedLine)) {
                continue;
            }

            const nodeDef = trimmedLine.match(
                /^([A-Za-z][\w-]*)\s*(?:\[\[|\[\(|\[\{|>>|\[>|\(\(|\(|{{|\[|>|\{)/,
            );
            if (nodeDef && !skip.has(nodeDef[1].toLowerCase())) {
                ids.add(nodeDef[1]);
            }

            for (const edge of trimmedLine.matchAll(
                /(?:-->|---|==>|-\.->)\s*([A-Za-z][\w-]*)/g,
            )) {
                if (!skip.has(edge[1].toLowerCase())) {
                    ids.add(edge[1]);
                }
            }
            for (const edge of trimmedLine.matchAll(
                /([A-Za-z][\w-]*)\s*(?:-->|---|==>|-\.->)/g,
            )) {
                if (!skip.has(edge[1].toLowerCase())) {
                    ids.add(edge[1]);
                }
            }
        }
        return ids.size;
    }

    return null;
}

function loadMermaidJs(): Promise<void> {
    const win = window as Window & { mermaid?: MermaidApi };
    if (win.mermaid) {
        return Promise.resolve();
    }
    if (mermaidJsPromise) {
        return mermaidJsPromise;
    }
    mermaidJsPromise = new Promise((resolve, reject) => {
        const existing = document.querySelector(
            `script[src="${MERMAID_JS_CDN}"]`,
        );
        if (existing) {
            if (win.mermaid) {
                resolve();
                return;
            }
            existing.addEventListener('load', () => resolve());
            existing.addEventListener('error', () =>
                reject(new Error('Mermaid library failed to load')),
            );
            return;
        }
        const script = document.createElement('script');
        script.src = MERMAID_JS_CDN;
        script.onload = () => resolve();
        script.onerror = () =>
            reject(new Error('Mermaid library failed to load'));
        document.head.appendChild(script);
    });
    return mermaidJsPromise;
}

function ensureMermaidInitialized(mermaid: MermaidApi): void {
    if (mermaidInitialized) {
        return;
    }
    mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        themeVariables: buildMermaidThemeVariables(),
        securityLevel: 'strict',
        flowchart: {
            useMaxWidth: true,
            padding: 8,
            nodeSpacing: 25,
            rankSpacing: 25,
        },
    });
    mermaidInitialized = true;
}

function truncateError(message: string, max = 200): string {
    const trimmed = message.trim();
    if (trimmed.length <= max) {
        return trimmed;
    }
    return `${trimmed.slice(0, max - 1)}…`;
}

async function renderMermaidNow(
    mount: HTMLElement,
    source: string,
    title?: string,
): Promise<void> {
    const mermaid = (window as Window & { mermaid?: MermaidApi }).mermaid;
    if (!mermaid) {
        showError(mount, 'Mermaid library failed to load');
        return;
    }
    ensureMermaidInitialized(mermaid);

    const titleHtml = title?.trim()
        ? `<div style="font-size:14px;font-weight:500;color:var(--color-text-primary,#e0e0e0);margin-bottom:8px;">${title.replace(/</g, '&lt;')}</div>`
        : '';

    mount.innerHTML = `${titleHtml}<div class="kn-mermaid-wrap" style="max-width:100%;overflow-x:auto;overflow-y:visible;"></div>`;
    const wrap = mount.querySelector('.kn-mermaid-wrap');
    if (!(wrap instanceof HTMLElement)) {
        showError(mount, 'Mermaid mount target not found');
        return;
    }

    const renderId = `kn-mermaid-${++renderCounter}`;
    try {
        const { svg } = await mermaid.render(renderId, source);
        wrap.innerHTML = svg;
        const renderedSvg = wrap.querySelector('svg');
        if (renderedSvg instanceof SVGSVGElement) {
            renderedSvg.style.width = '97%';
            renderedSvg.style.maxWidth = '97%';
            renderedSvg.style.height = 'auto';
        }
    } catch (e: unknown) {
        const msg =
            e instanceof Error ? e.message : 'Mermaid render failed';
        showError(mount, truncateError(msg));
    }
}

function scheduleRender(
    mount: HTMLElement,
    source: string,
    title?: string,
): void {
    pendingMount = mount;
    pendingTitle = title;
    if (renderDebounceTimer) {
        clearTimeout(renderDebounceTimer);
    }
    renderDebounceTimer = setTimeout(() => {
        renderDebounceTimer = null;
        const target = pendingMount;
        const nextTitle = pendingTitle;
        pendingMount = null;
        pendingTitle = undefined;
        if (!target) {
            return;
        }
        void loadMermaidJs()
            .then(() => renderMermaidNow(target, source, nextTitle))
            .catch(() => {
                showError(target, 'Mermaid library failed to load');
            });
    }, MERMAID_RENDER_DEBOUNCE_MS);
}

export function renderMermaid(
    source: string,
    options?: MermaidOptions,
): void {
    let mount: HTMLElement;
    try {
        mount = resolveMount(options?.mount);
    } catch {
        throw new Error('Mermaid mount target not found');
    }

    const validationError = validateMermaidSource(source);
    if (validationError) {
        showError(mount, validationError);
        return;
    }

    const normalized = normalizeMermaidSource(source);
    if (normalized === lastSource && !options?.title) {
        return;
    }
    lastSource = normalized;

    scheduleRender(mount, normalized, options?.title);
}
