export const CHART_COLORS = [
    '#3266ad',
    '#5dcaa5',
    '#afa9ec',
    '#f0997b',
    '#ed93b1',
    '#ef9f27',
];

export function seriesColor(index: number, override?: string): string {
    if (override?.trim()) {
        return override;
    }
    return CHART_COLORS[index % CHART_COLORS.length] ?? '#3266ad';
}
