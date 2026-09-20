import {
    useCallback,
    useEffect,
    useLayoutEffect,
    useMemo,
    useReducer,
    useRef,
    useState,
} from 'react';
import svgWidgetStyles from '../../../assets/svg-styles.css?raw';
import knRuntimeBundle from '../../../assets/kn-runtime.iife.js?raw';
import lavishWidgetStyles from '../../../../../agent/core/prompts/visualization/assets/lavish.css?raw';
import previewBootstrap from '../../../../../agent/core/prompts/visualization/assets/preview-bootstrap.js?raw';
import {
    INITIAL_IFRAME_STATE,
    iframeReducer,
    type WidgetSandboxErrorDetail,
} from './iframeState';
import {
    bridgeScripts,
    MORPHDOM_SRC,
    MSG_HEIGHT,
    MSG_SET,
    MSG_WIDGET_ERROR,
} from './scriptBridges';
import { useIframeMessaging } from './useIframeMessaging';

const CHAT_EMBED_BG = '#1a1a1a';
const CHART_JS_SRC =
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js';
const MERMAID_JS_SRC =
    'https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js';

const WIDGET_DARK_OVERRIDES = `
/* Adapt the portable Lavish artifacts to the surrounding chat design system. */
:root {
    color-scheme: dark;
    --lv-bg: var(--color-background, ${CHAT_EMBED_BG});
    --lv-panel: var(--color-surface, #2f2f2f);
    --lv-elevated: var(--color-surface-elevated, #383838);
    --lv-fg: var(--color-text, #ececec);
    --lv-muted: var(--color-text-muted, #a3a3a3);
    --lv-border: var(--color-border-subtle, #333333);
    --lv-accent: var(--color-primary, #60a5fa);
    --lv-accent-hover: var(--color-primary-hover, #93c5fd);
    --lv-accent-ink: #171717;
    --lv-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    --lv-serif: 'Newsreader', Georgia, serif;
    --lv-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
}
html, body {
    background: transparent !important;
    color: var(--lv-fg);
    overflow-x: hidden;
    overflow-y: visible;
}
body {
    padding: 0 !important;
    font: 15px/1.55 var(--lv-sans);
}
#kn-root { display: block; width: 100%; }
#kn-root > :first-child { margin-top: 0; }
#kn-root > :last-child { margin-bottom: 0; }
.lv-panel, .lv-card {
    border-color: var(--lv-border);
    box-shadow: none;
}
.lv-panel { padding: 20px; border-radius: 16px; }
.lv-card { padding: 16px; border-radius: 12px; }
/* Content sections use the full conversation width, including saved fragments
   with inline column definitions. Keep control rows and graphic internals intact. */
#kn-root .lv-grid, #kn-root .lv-stack {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 16px;
}
#kn-root :is(.lv-grid, .lv-stack) > * {
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    flex: none !important;
    margin-inline: 0 !important;
}
#kn-root :is(.lv-panel, .lv-card):has(> .lv-card) {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 16px;
}
#kn-root :is(.lv-panel, .lv-card) > .lv-card {
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    flex: none !important;
    margin: 0 !important;
}
#kn-root .mermaid { margin: 0; }
#kn-root .mermaid svg { height: auto; }
.lv-value { font-size: clamp(22px, 4vw, 32px); }
.lv-chart { height: 260px; }
@media (max-width: 480px) {
    .lv-panel, .lv-card { padding: 14px; }
    .lv-chart { height: 220px; }
}
`;

function runtimeScriptTag(): string {
    if (!knRuntimeBundle.trim()) {
        return '';
    }
    return `<script>${knRuntimeBundle}</script>`;
}

/**
 * The agent's visualization fragments are deliberately framework-free.  They
 * rely on this host contract: Lavish styles plus global Chart and Mermaid must
 * exist before a fragment's own scripts run.  Keep these blocking classic
 * scripts in the document head so this is also true for a completed response
 * rendered directly through srcDoc.
 */
export function buildWidgetHostHead(): string {
    return `<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet"><style id="kn-lavish-widget-styles">${lavishWidgetStyles}</style><script src="${CHART_JS_SRC}"></script><script src="${MERMAID_JS_SRC}"></script><script>${previewBootstrap}</script><style id="kn-widget-chat-surface">${WIDGET_DARK_OVERRIDES}</style>${runtimeScriptTag()}`;
}

function buildSrcDoc(widgetCode: string): string {
    const head = `<meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><script>${bridgeScripts.reportError(MSG_WIDGET_ERROR)}</script><style id="kn-svg-widget-styles">${svgWidgetStyles}</style>${buildWidgetHostHead()}`;
    const resizeScript =
        `<script>${bridgeScripts.resizeNotifier(MSG_HEIGHT)}</` + `script>`;
    return `<!DOCTYPE html><html lang="en"><head>${head}</head><body style="margin:0;padding:0;box-sizing:border-box;background:${CHAT_EMBED_BG};color:var(--color-text-primary);font-family:system-ui,sans-serif;min-height:min-content"><div id="kn-root">${widgetCode}</div>${resizeScript}</body></html>`;
}

function buildStreamBootstrapSrcDoc(): string {
    const streamListener = bridgeScripts.streamListener(MSG_SET, MSG_HEIGHT);
    const morphOnload = bridgeScripts.morphOnload();
    const head = `<meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><script>${bridgeScripts.reportError(MSG_WIDGET_ERROR)}</script><style id="kn-svg-widget-styles">${svgWidgetStyles}</style>${buildWidgetHostHead()}`;
    return `<!DOCTYPE html><html lang="en"><head>${head}</head><body style="margin:0;padding:0;box-sizing:border-box;background:${CHAT_EMBED_BG};color:var(--color-text-primary);font-family:system-ui,sans-serif;min-height:min-content"><div id="kn-root"></div><script>${streamListener}</` + `script><script src="${MORPHDOM_SRC}" onload="${morphOnload}"></` + `script></body></html>`;
}

interface Props {
    widgetCode: string;
    title?: string;
    loadingMessages?: string[];
    streamActive: boolean;
    incomplete?: boolean;
}

export function InlineVisualizationFrame({
    widgetCode,
    title,
    loadingMessages = [],
    streamActive,
    incomplete = false,
}: Props) {
    const iframeRef = useRef<HTMLIFrameElement>(null);
    const [state, dispatch] = useReducer(iframeReducer, INITIAL_IFRAME_STATE);
    const { iframeReady, contentHeightPx, errorDetail, usedStreamBootstrap } = state;
    const prevStreamActiveRef = useRef(false);
    const [loadingIdx, setLoadingIdx] = useState(0);

    const { postMarkup, debouncePostMarkup, cancelPending } =
        useIframeMessaging(iframeRef);

    const bootstrapSrcDoc = useMemo(() => buildStreamBootstrapSrcDoc(), []);

    const iframeSrcDoc = useMemo(() => {
        if (streamActive || usedStreamBootstrap) {
            return bootstrapSrcDoc;
        }
        return buildSrcDoc(widgetCode);
    }, [streamActive, widgetCode, bootstrapSrcDoc, usedStreamBootstrap]);

    const onIframeLoad = useCallback(() => {
        const isBootstrap = streamActive || usedStreamBootstrap;
        dispatch({ type: 'iframe-loaded', isBootstrap });
    }, [streamActive, usedStreamBootstrap]);

    useLayoutEffect(() => {
        if (streamActive && !prevStreamActiveRef.current) {
            dispatch({ type: 'stream-started' });
        }
        prevStreamActiveRef.current = streamActive;
    }, [streamActive]);

    useLayoutEffect(() => {
        const onMessage = (ev: MessageEvent): void => {
            if (ev.source !== iframeRef.current?.contentWindow) return;
            if (!ev.data || typeof ev.data !== 'object') return;

            if (ev.data.type === MSG_HEIGHT) {
                const h = Number(ev.data.height);
                if (!Number.isFinite(h) || h <= 0) return;
                dispatch({ type: 'height-updated', height: Math.ceil(h) });
                return;
            }

            if (ev.data.type === MSG_WIDGET_ERROR) {
                const msg =
                    typeof ev.data.message === 'string' && ev.data.message.trim()
                        ? ev.data.message.trim()
                        : 'Script error in visualization';
                const detail: WidgetSandboxErrorDetail = {
                    message: msg,
                    source:
                        typeof ev.data.source === 'string'
                            ? ev.data.source
                            : undefined,
                    line:
                        typeof ev.data.line === 'number' ? ev.data.line : undefined,
                    col: typeof ev.data.col === 'number' ? ev.data.col : undefined,
                    stack:
                        typeof ev.data.stack === 'string'
                            ? ev.data.stack
                            : undefined,
                };
                dispatch({ type: 'error-detected', detail });
            }
        };
        window.addEventListener('message', onMessage);
        return () => window.removeEventListener('message', onMessage);
    }, []);

    useLayoutEffect(() => {
        if (!iframeReady) return;

        if (!streamActive && !usedStreamBootstrap) {
            return;
        }

        if (!streamActive && usedStreamBootstrap) {
            cancelPending();
            postMarkup(widgetCode, true, false);
            return () => {
                cancelPending();
            };
        }

        debouncePostMarkup(widgetCode);

        return () => {
            cancelPending();
        };
    }, [
        widgetCode,
        streamActive,
        iframeReady,
        usedStreamBootstrap,
        postMarkup,
        debouncePostMarkup,
        cancelPending,
    ]);

    useEffect(() => {
        if (!streamActive || widgetCode.trim() || loadingMessages.length === 0) {
            return;
        }
        const timer = window.setInterval(() => {
            setLoadingIdx((prev) => (prev + 1) % loadingMessages.length);
        }, 2400);
        return () => window.clearInterval(timer);
    }, [streamActive, widgetCode, loadingMessages]);

    const hasBody = Boolean(widgetCode.trim());
    const iframeTitle = title?.trim() || 'Inline visualization';
    const showLoading = streamActive && !hasBody && loadingMessages.length > 0;
    const loadingText = loadingMessages[loadingIdx] ?? 'Loading visualization…';
    const showStatus = incomplete || errorDetail;

    if (!hasBody && !streamActive && !incomplete) {
        return null;
    }

    return (
        <div className="my-3 w-full overflow-visible">
            {showStatus ? (
                <div className="mb-2 flex items-center gap-2 text-xs">
                    {incomplete ? (
                        <span className="rounded bg-amber-500/15 px-2 py-0.5 text-amber-400">
                            Unable to complete visualization
                        </span>
                    ) : null}
                    {errorDetail ? (
                        <span
                            className="text-red-400"
                            title={errorDetail.message}
                        >
                            Error
                        </span>
                    ) : null}
                </div>
            ) : null}
            {showLoading ? (
                <div className="py-2 text-sm text-[var(--color-text-muted)] animate-pulse">
                    {loadingText}
                </div>
            ) : null}
            <iframe
                ref={iframeRef}
                title={iframeTitle}
                className="w-full border-0 block bg-transparent outline-none"
                style={{
                    overflow: 'hidden',
                    minHeight: contentHeightPx === null ? '4rem' : undefined,
                    height:
                        contentHeightPx !== null
                            ? `${contentHeightPx}px`
                            : undefined,
                }}
                sandbox="allow-scripts"
                scrolling="no"
                srcDoc={iframeSrcDoc}
                onLoad={onIframeLoad}
            />
        </div>
    );
}
