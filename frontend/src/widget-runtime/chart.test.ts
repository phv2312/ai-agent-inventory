import { describe, expect, it } from 'vitest';

import { computeChartWrapperHeight, validateChartConfig } from './chart';
import type { ChartConfig } from './types';

describe('validateChartConfig', () => {
    it('accepts valid bar chart config', () => {
        const config: ChartConfig = {
            type: 'bar',
            labels: ['A', 'B'],
            series: [{ label: 'S1', data: [1, 2] }],
        };
        expect(validateChartConfig(config)).toBeNull();
    });

    it('rejects missing series', () => {
        expect(
            validateChartConfig({
                type: 'bar',
                labels: ['A'],
                series: [],
            }),
        ).toMatch(/series/i);
    });

    it('rejects bar chart without labels', () => {
        expect(
            validateChartConfig({
                type: 'bar',
                series: [{ label: 'S1', data: [1] }],
            }),
        ).toMatch(/labels/i);
    });
});

describe('computeChartWrapperHeight', () => {
    it('uses explicit height when provided', () => {
        const config: ChartConfig = {
            type: 'bar',
            labels: ['A'],
            series: [{ label: 'S1', data: [1] }],
            height: 420,
        };
        expect(computeChartWrapperHeight(config)).toBe(420);
    });

    it('expands height for horizontal bar charts', () => {
        const labels = Array.from({ length: 8 }, (_, i) => `L${i}`);
        const config: ChartConfig = {
            type: 'bar',
            labels,
            series: [{ label: 'S1', data: labels.map(() => 1) }],
            options: { indexAxis: 'y' },
        };
        expect(computeChartWrapperHeight(config)).toBeGreaterThanOrEqual(300);
    });
});
