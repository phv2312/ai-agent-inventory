export const CONTENT_BLOCK_TYPE = {
    TEXT: 'text',
    VISUAL_WIDGET: 'visual_widget',
} as const;

export type ContentBlockType =
    (typeof CONTENT_BLOCK_TYPE)[keyof typeof CONTENT_BLOCK_TYPE];

export const WIDGET_BLOCK_STATUS = {
    STREAMING: 'streaming',
    COMPLETE: 'complete',
    INCOMPLETE: 'incomplete',
    ERROR: 'error',
} as const;

export type WidgetBlockStatus =
    (typeof WIDGET_BLOCK_STATUS)[keyof typeof WIDGET_BLOCK_STATUS];

export interface ContentBlock {
    id: string;
    type: ContentBlockType;
    order: number;
    status: WidgetBlockStatus;
    module?: string | null;
    text?: string | null;
    title?: string | null;
    loadingMessages?: string[];
    widgetCode?: string | null;
    errorMessage?: string | null;
}

export interface BlockOpenPayload {
    block_id: string;
    type: ContentBlockType;
    order: number;
    module?: string | null;
    title?: string | null;
    loading_messages?: string[];
}

export interface BlockDeltaPayload {
    block_id: string;
    content: string;
}

export interface BlockClosePayload {
    block_id: string;
    status: WidgetBlockStatus;
    error_message?: string | null;
}

/** Raw block from REST (camelCase after apiFetch) or SSE (snake_case). */
export function apiBlockToContentBlock(raw: {
    id: string;
    type: string;
    order: number;
    status: string;
    text?: string | null;
    module?: string | null;
    title?: string | null;
    loading_messages?: string[];
    loadingMessages?: string[];
    widget_code?: string | null;
    widgetCode?: string | null;
    error_message?: string | null;
    errorMessage?: string | null;
}): ContentBlock {
    return {
        id: raw.id,
        type: raw.type as ContentBlockType,
        order: raw.order,
        status: raw.status as WidgetBlockStatus,
        module: raw.module,
        text: raw.text,
        title: raw.title,
        loadingMessages: raw.loadingMessages ?? raw.loading_messages ?? [],
        widgetCode: raw.widgetCode ?? raw.widget_code,
        errorMessage: raw.errorMessage ?? raw.error_message,
    };
}
