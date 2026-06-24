export type ChartType =
    | 'bar'
    | 'line'
    | 'pie'
    | 'doughnut'
    | 'scatter'
    | 'bubble'
    | 'radar';

export interface ChartSeries {
    label: string;
    data: number[];
    color?: string;
}

export interface ChartConfig {
    type: ChartType;
    labels?: string[];
    series: ChartSeries[];
    title?: string;
    height?: number;
    legend?: 'auto' | 'custom' | 'none';
    options?: Record<string, unknown>;
    mount?: string;
}

export interface MermaidOptions {
    mount?: string;
    title?: string;
}

export const MAX_MERMAID_SOURCE_CHARS = 16_000;
export const MERMAID_RENDER_DEBOUNCE_MS = 150;

/** Per-widget limit — split into multiple show_widget / iframes when exceeded. */
export const MAX_MERMAID_NODES_PER_WIDGET = 8;
