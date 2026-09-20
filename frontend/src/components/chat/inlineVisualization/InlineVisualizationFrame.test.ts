import { describe, expect, it } from 'vitest';
import { buildWidgetHostHead } from './InlineVisualizationFrame';

describe('inline visualization host contract', () => {
    it('loads styles and libraries before fragment scripts execute', () => {
        const head = buildWidgetHostHead();

        expect(head).toContain('id="kn-lavish-widget-styles"');
        expect(head).toContain('id="kn-widget-chat-surface"');
        expect(head).toContain("--lv-panel: var(--color-surface, #2f2f2f)");
        expect(head).toContain("'Plus Jakarta Sans'");
        expect(head).toContain(
            'https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js',
        );
        expect(head).toContain(
            'https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js',
        );
        expect(head).toContain('mermaid.initialize');
        expect(head).toContain('window.KN');
        expect(
            head.indexOf('chart.umd.min.js'),
        ).toBeLessThan(head.indexOf('mermaid.min.js'));
        expect(head.indexOf('mermaid.min.js')).toBeLessThan(
            head.indexOf('mermaid.initialize'),
        );
    });
});
