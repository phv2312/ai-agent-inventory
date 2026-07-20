export const CONTENT_BLOCK_TYPE = {
    TEXT: 'text',
    VISUAL_WIDGET: 'visual_widget',
} as const;

export type ContentBlockType =
    (typeof CONTENT_BLOCK_TYPE)[keyof typeof CONTENT_BLOCK_TYPE];

export const WIDGET_BLOCK_STATUS = {
    IN_PROGRESS: 'in_progress',
    COMPLETE: 'complete',
    ERROR: 'error',
} as const;

export type WidgetBlockStatus =
    (typeof WIDGET_BLOCK_STATUS)[keyof typeof WIDGET_BLOCK_STATUS];

export interface ContentBlock {
    type: ContentBlockType;
    order: number;
    status: WidgetBlockStatus;
    text?: string | null;
    textChunks?: string[];
    title?: string | null;
    loadingMessages?: string[];
    widgetCode?: string | null;
    widgetCodeChunks?: string[];
    errorMessage?: string | null;
}

export interface BlockOpenPayload {
    event_type: 'block-open';
    type: ContentBlockType;
    order: number;
    status: WidgetBlockStatus;
    content?: string | null;
    error_message?: string | null;
}

export interface BlockDeltaPayload {
    event_type: 'block-delta';
    order: number;
    type: ContentBlockType;
    status: WidgetBlockStatus;
    content?: string | null;
    error_message?: string | null;
}

export interface BlockClosePayload {
    event_type: 'block-close';
    order: number;
    type: ContentBlockType;
    status: WidgetBlockStatus;
    content?: string | null;
    error_message?: string | null;
}

/** Raw block from REST (camelCase after apiFetch) or SSE (snake_case). */
export function apiBlockToContentBlock(raw: {
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
        type: raw.type as ContentBlockType,
        order: raw.order,
        status: raw.status as WidgetBlockStatus,
        text: raw.text,
        title: raw.title,
        loadingMessages: raw.loadingMessages ?? raw.loading_messages ?? [],
        widgetCode: raw.widgetCode ?? raw.widget_code,
        errorMessage: raw.errorMessage ?? raw.error_message,
    };
}
