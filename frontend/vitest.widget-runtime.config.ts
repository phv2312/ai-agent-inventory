import { defineConfig } from 'vitest/config';

export default defineConfig({
    test: {
        environment: 'node',
        environmentMatchGlobs: [
            ['src/widget-runtime/mermaid.test.ts', 'jsdom'],
        ],
        include: [
            'src/widget-runtime/**/*.test.ts',
            'src/components/chat/inlineVisualization/**/*.test.ts',
        ],
    },
});
