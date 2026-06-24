export interface WidgetSandboxErrorDetail {
    message: string;
    source?: string;
    line?: number;
    col?: number;
    stack?: string;
}

export interface IframeState {
    iframeReady: boolean;
    contentHeightPx: number | null;
    errorDetail: WidgetSandboxErrorDetail | null;
    usedStreamBootstrap: boolean;
}

export type IframeAction =
    | { type: 'stream-started' }
    | { type: 'iframe-loaded'; isBootstrap: boolean }
    | { type: 'height-updated'; height: number }
    | { type: 'error-detected'; detail: WidgetSandboxErrorDetail };

export const INITIAL_IFRAME_STATE: IframeState = {
    iframeReady: false,
    contentHeightPx: null,
    errorDetail: null,
    usedStreamBootstrap: false,
};

export function iframeReducer(state: IframeState, action: IframeAction): IframeState {
    switch (action.type) {
        case 'stream-started':
            return {
                ...state,
                usedStreamBootstrap: true,
                errorDetail: null,
            };
        case 'iframe-loaded':
            if (action.isBootstrap) {
                return { ...state, iframeReady: true };
            }
            return { ...state, errorDetail: null };
        case 'height-updated':
            return { ...state, contentHeightPx: action.height };
        case 'error-detected':
            return { ...state, errorDetail: action.detail };
        default:
            return state;
    }
}
