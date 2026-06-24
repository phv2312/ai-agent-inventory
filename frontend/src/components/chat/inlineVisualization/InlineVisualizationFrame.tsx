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

const WIDGET_DARK_OVERRIDES = `
html { color-scheme: dark; }
html, body { background-color: ${CHAT_EMBED_BG} !important; overflow-x: auto; overflow-y: visible; }
`;

function runtimeScriptTag(): string {
    if (!knRuntimeBundle.trim()) {
        return '';
    }
    return `<script>${knRuntimeBundle}</script>`;
}

function buildSrcDoc(widgetCode: string): string {
    const head = `<meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><script>${bridgeScripts.reportError(MSG_WIDGET_ERROR)}</script><style id="kn-svg-widget-styles">${svgWidgetStyles}</style><style id="kn-widget-chat-surface">${WIDGET_DARK_OVERRIDES}</style>${runtimeScriptTag()}`;
    const resizeScript =
        `<script>${bridgeScripts.resizeNotifier(MSG_HEIGHT)}</` + `script>`;
    return `<!DOCTYPE html><html lang="en"><head>${head}</head><body style="margin:0;padding:0;box-sizing:border-box;background:${CHAT_EMBED_BG};color:var(--color-text-primary);font-family:system-ui,sans-serif;min-height:min-content"><div id="kn-root">${widgetCode}</div>${resizeScript}</body></html>`;
}

function buildStreamBootstrapSrcDoc(): string {
    const streamListener = bridgeScripts.streamListener(MSG_SET, MSG_HEIGHT);
    const morphOnload = bridgeScripts.morphOnload();
    const head = `<meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><script>${bridgeScripts.reportError(MSG_WIDGET_ERROR)}</script><style id="kn-svg-widget-styles">${svgWidgetStyles}</style><style id="kn-widget-chat-surface">${WIDGET_DARK_OVERRIDES}</style>${runtimeScriptTag()}`;
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
        <div className="my-2 w-full overflow-visible">
            {showStatus ? (
                <div className="mb-2 flex items-center gap-2 text-xs">
                    {incomplete ? (
                        <span className="rounded bg-amber-500/15 px-2 py-0.5 text-amber-400">
                            Incomplete
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
                srcDoc={iframeSrcDoc}
                onLoad={onIframeLoad}
            />
        </div>
    );
}
