import { renderChart } from './chart';
import { renderMermaid } from './mermaid';

export const KN = {
    version: '1.5.0',
    chart: renderChart,
    mermaid: renderMermaid,
};

export type KNRuntime = typeof KN;

declare global {
    interface Window {
        KN: KNRuntime;
    }
}

if (typeof window !== 'undefined') {
    window.KN = KN;
}
