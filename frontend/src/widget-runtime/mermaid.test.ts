import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { buildMermaidThemeVariables } from './mermaid-theme';
import {
    countMermaidNodes,
    normalizeMermaidSource,
    renderMermaid,
    resetMermaidRuntimeForTests,
    validateMermaidSource,
} from './mermaid';
import {
    MAX_MERMAID_NODES_PER_WIDGET,
    MAX_MERMAID_SOURCE_CHARS,
} from './types';

describe('buildMermaidThemeVariables', () => {
    it('includes required keys for dark chat palette', () => {
        const vars = buildMermaidThemeVariables();
        expect(vars.primaryColor).toBeTruthy();
        expect(vars.primaryTextColor).toBeTruthy();
        expect(vars.lineColor).toBeTruthy();
        expect(vars.clusterBkg).toBeTruthy();
    });
});

describe('countMermaidNodes', () => {
    it('counts flowchart nodes', () => {
        const source = `flowchart TD
  A[Start] --> B[Process]
  B --> C[End]`;
        expect(countMermaidNodes(source)).toBe(3);
    });

    it('counts tiered subgraph without counting subgraph ids as nodes', () => {
        const source = `flowchart TB
  subgraph client[Client layer]
    SDK[SDK / ORM]
  end
  subgraph access[Access layer]
    Proxy[Proxy]
  end
  subgraph coord[Coordinator layer]
    Root[Root coord]
  end
  SDK --> Proxy
  Proxy --> Root`;
        expect(countMermaidNodes(source)).toBe(3);
    });

    it('counts sequence participants', () => {
        const source = `sequenceDiagram
  participant A as Client
  participant B as Server
  A->>B: ping`;
        expect(countMermaidNodes(source)).toBe(2);
    });
});

describe('normalizeMermaidSource', () => {
    it('quotes rectangle labels with newlines and parentheses', () => {
        const raw = 'flowchart TB\n  Mix[MixCoord\\n(Root+Data+Query)]';
        expect(normalizeMermaidSource(raw)).toBe(
            'flowchart TB\n  Mix["MixCoord\\n(Root+Data+Query)"]',
        );
    });

    it('leaves simple labels unchanged', () => {
        const raw = 'flowchart TD\n  Proxy[Proxy] --> SN[StreamingNode]';
        expect(normalizeMermaidSource(raw)).toBe(raw);
    });
});

describe('validateMermaidSource', () => {
    it('rejects empty source', () => {
        expect(validateMermaidSource('   ')).toMatch(/empty/i);
    });

    it('rejects oversize source', () => {
        const big = 'flowchart TD\n' + 'A-->B\n'.repeat(
            MAX_MERMAID_SOURCE_CHARS,
        );
        expect(validateMermaidSource(big)).toMatch(/too large/i);
    });

    it('accepts diagrams larger than soft node guidance limit', () => {
        const lines = ['flowchart TD'];
        for (let i = 0; i < MAX_MERMAID_NODES_PER_WIDGET + 1; i += 1) {
            const id = `N${i}`;
            lines.push(`  ${id}[Node ${i}]`);
            if (i > 0) {
                lines.push(`  N${i - 1} --> ${id}`);
            }
        }
        expect(validateMermaidSource(lines.join('\n'))).toBeNull();
    });

    it('accepts valid small flowchart', () => {
        expect(
            validateMermaidSource('flowchart TD\n  A --> B'),
        ).toBeNull();
    });
});

describe('renderMermaid', () => {
    beforeEach(() => {
        resetMermaidRuntimeForTests();
        document.body.innerHTML = '<div id="kn-root"></div>';
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
        document.body.innerHTML = '';
    });

    it('shows error for empty source', () => {
        renderMermaid('');
        const mount = document.getElementById('kn-root');
        expect(mount?.innerHTML).toMatch(/empty/i);
    });

    it('debounces coalesced renders', async () => {
        const render = vi.fn().mockResolvedValue({ svg: '<svg></svg>' });
        (
            window as Window & {
                mermaid?: {
                    initialize: () => void;
                    render: typeof render;
                };
            }
        ).mermaid = {
            initialize: vi.fn(),
            render,
        };

        renderMermaid('flowchart TD\n  A --> B');
        renderMermaid('flowchart TD\n  A --> B --> C');
        expect(render).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(150);
        expect(render).toHaveBeenCalledTimes(1);
        expect(render.mock.calls[0][1]).toContain('A --> B --> C');
    });

    it('expands a rendered diagram to the available widget width', async () => {
        const render = vi
            .fn()
            .mockResolvedValue({ svg: '<svg width="240" height="80"></svg>' });
        (
            window as Window & {
                mermaid?: {
                    initialize: () => void;
                    render: typeof render;
                };
            }
        ).mermaid = {
            initialize: vi.fn(),
            render,
        };

        renderMermaid('flowchart LR\n  A --> B');
        await vi.advanceTimersByTimeAsync(150);

        const svg = document.querySelector('.kn-mermaid-wrap svg');
        expect(svg).toBeInstanceOf(SVGSVGElement);
        if (!(svg instanceof SVGSVGElement)) {
            throw new Error('Expected Mermaid to render an SVG element');
        }
        expect(svg.style.width).toBe('100%');
        expect(svg.style.height).toBe('auto');
    });

    it('shows CDN load failure message', async () => {
        const originalQuery = document.querySelector.bind(document);
        vi.spyOn(document, 'querySelector').mockImplementation(
            (selector: string) => {
                if (selector.includes('mermaid')) {
                    return null;
                }
                return originalQuery(selector);
            },
        );

        const appendChild = vi
            .spyOn(document.head, 'appendChild')
            .mockImplementation((node) => {
                if (node instanceof HTMLScriptElement) {
                    queueMicrotask(() => node.onerror?.(new Event('error')));
                }
                return node;
            });

        renderMermaid('flowchart TD\n  A --> B');
        await vi.advanceTimersByTimeAsync(150);

        const mount = document.getElementById('kn-root');
        expect(mount?.innerHTML).toMatch(/failed to load/i);

        appendChild.mockRestore();
        vi.restoreAllMocks();
    });

    it('shows parse error from mermaid.render', async () => {
        (
            window as Window & {
                mermaid?: {
                    initialize: () => void;
                    render: () => Promise<never>;
                };
            }
        ).mermaid = {
            initialize: vi.fn(),
            render: vi.fn().mockRejectedValue(new Error('Parse error on line 2')),
        };

        renderMermaid('flowchart TD\n  broken syntax');
        await vi.advanceTimersByTimeAsync(150);

        const mount = document.getElementById('kn-root');
        expect(mount?.innerHTML).toMatch(/parse error/i);
    });
});
