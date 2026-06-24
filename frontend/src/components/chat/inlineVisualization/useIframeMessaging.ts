import {
    useCallback,
    useEffect,
    useRef,
    type RefObject,
} from 'react';
import { MSG_SET } from './scriptBridges';

export function useIframeMessaging(
    iframeRef: RefObject<HTMLIFrameElement | null>,
) {
    const debounceRef = useRef<number | null>(null);
    const latestHtmlRef = useRef('');

    const postMarkup = useCallback(
        (html: string, runScripts = false, replaceRoot = false) => {
            const win = iframeRef.current?.contentWindow;
            if (!win) return;
            win.postMessage(
                { type: MSG_SET, html, runScripts, replaceRoot },
                '*',
            );
        },
        [iframeRef],
    );

    const cancelPending = useCallback(() => {
        if (debounceRef.current !== null) {
            window.clearTimeout(debounceRef.current);
            debounceRef.current = null;
        }
    }, []);

    const debouncePostMarkup = useCallback(
        (html: string, delayMs = 150) => {
            latestHtmlRef.current = html;
            if (debounceRef.current !== null) {
                window.clearTimeout(debounceRef.current);
            }
            debounceRef.current = window.setTimeout(() => {
                debounceRef.current = null;
                postMarkup(latestHtmlRef.current, false, false);
            }, delayMs);
        },
        [postMarkup],
    );

    useEffect(() => {
        return () => {
            if (debounceRef.current !== null) {
                window.clearTimeout(debounceRef.current);
                debounceRef.current = null;
            }
        };
    }, []);

    return { postMarkup, debouncePostMarkup, cancelPending };
}
