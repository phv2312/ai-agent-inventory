import { showError } from './errors';
import { resolveMount } from './mount';
import { seriesColor } from './palette';
import type { ChartConfig } from './types';

const CHART_JS_CDN =
    'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js';

const CHART_TYPES = new Set([
    'bar',
    'line',
    'pie',
    'doughnut',
    'scatter',
    'bubble',
    'radar',
]);

let chartJsPromise: Promise<void> | null = null;

export function validateChartConfig(config: ChartConfig): string | null {
    if (!config || typeof config !== 'object') {
        return 'Chart config must be an object';
    }
    if (!config.type || !CHART_TYPES.has(config.type)) {
        return `Invalid chart type: ${String(config.type)}`;
    }
    if (!Array.isArray(config.series) || config.series.length === 0) {
        return 'Chart requires at least one series';
    }
    for (const s of config.series) {
        if (!s.label?.trim()) {
            return 'Each series requires a label';
        }
        if (!Array.isArray(s.data) || s.data.length === 0) {
            return `Series "${s.label}" requires data points`;
        }
    }
    if (config.type !== 'scatter' && config.type !== 'bubble') {
        if (!config.labels?.length) {
            return 'Chart requires labels for this type';
        }
    }
    return null;
}

export function computeChartWrapperHeight(config: ChartConfig): number {
    if (config.height && config.height > 0) {
        return config.height;
    }
    const indexAxis = (config.options as { indexAxis?: string } | undefined)
        ?.indexAxis;
    const isHorizontalBar = config.type === 'bar' && indexAxis === 'y';
    const labelCount =
        config.labels?.length ?? config.series[0]?.data.length ?? 4;
    if (isHorizontalBar) {
        return Math.max(240, labelCount * 32 + 64);
    }
    if (config.type === 'pie' || config.type === 'doughnut') {
        return 220;
    }
    return 240;
}

function loadChartJs(): Promise<void> {
    if (typeof window !== 'undefined' && (window as { Chart?: unknown }).Chart) {
        return Promise.resolve();
    }
    if (chartJsPromise) {
        return chartJsPromise;
    }
    chartJsPromise = new Promise((resolve, reject) => {
        const existing = document.querySelector(`script[src="${CHART_JS_CDN}"]`);
        if (existing) {
            if ((window as { Chart?: unknown }).Chart) {
                resolve();
                return;
            }
            existing.addEventListener('load', () => resolve());
            existing.addEventListener('error', () =>
                reject(new Error('Chart.js failed to load')),
            );
            return;
        }
        const script = document.createElement('script');
        script.src = CHART_JS_CDN;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('Chart.js failed to load'));
        document.head.appendChild(script);
    });
    return chartJsPromise;
}

function buildLegendHtml(config: ChartConfig, colors: string[]): string {
    const mode = config.legend ?? 'custom';
    if (mode === 'none') {
        return '';
    }
    const items = config.series
        .map((s, i) => {
            const color = colors[i] ?? '#3266ad';
            const label = s.label.replace(/</g, '&lt;');
            return `<span style="display:flex;align-items:center;gap:4px;"><span style="width:10px;height:10px;border-radius:2px;background:${color};"></span>${label}</span>`;
        })
        .join('');
    return `<div style="display:flex;flex-wrap:wrap;gap:16px;margin-bottom:8px;font-size:12px;color:var(--color-text-secondary,#a0a0a0);">${items}</div>`;
}

export function renderChart(config: ChartConfig): void {
    const validationError = validateChartConfig(config);
    let mount: HTMLElement;
    try {
        mount = resolveMount(config.mount);
    } catch {
        throw new Error('Chart mount target not found');
    }
    if (validationError) {
        showError(mount, validationError);
        return;
    }

    const height = computeChartWrapperHeight(config);
    const chartId = `kn-chart-${Math.random().toString(36).slice(2, 9)}`;
    const colors = config.series.map((s, i) => seriesColor(i, s.color));
    const legendMode = config.legend ?? 'custom';
    const legendHtml =
        legendMode === 'custom' ? buildLegendHtml(config, colors) : '';

    mount.innerHTML = `${legendHtml}<div style="position:relative;width:100%;height:${height}px;"><canvas id="${chartId}"></canvas></div>`;

    const init = (): void => {
        const ChartCtor = (
            window as { Chart?: new (...args: unknown[]) => unknown }
        ).Chart;
        if (!ChartCtor) {
            showError(mount, 'Chart.js not available');
            return;
        }
        const canvas = document.getElementById(chartId);
        if (!(canvas instanceof HTMLCanvasElement)) {
            showError(mount, 'Chart canvas not found');
            return;
        }
        const datasets = config.series.map((s, i) => ({
            label: s.label,
            data: s.data,
            backgroundColor: colors[i],
            borderColor: colors[i],
            borderWidth: 1,
        }));
        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: legendMode === 'auto' },
                title: config.title
                    ? { display: true, text: config.title }
                    : { display: false },
            },
        };
        const options = {
            ...baseOptions,
            ...(config.options ?? {}),
            plugins: {
                ...baseOptions.plugins,
                ...((config.options?.plugins as object) ?? {}),
            },
        };
        new ChartCtor(canvas, {
            type: config.type,
            data: { labels: config.labels ?? [], datasets },
            options,
        });
    };

    void loadChartJs()
        .then(init)
        .catch((e: unknown) => {
            const msg = e instanceof Error ? e.message : 'Chart load failed';
            showError(mount, msg);
        });
}
