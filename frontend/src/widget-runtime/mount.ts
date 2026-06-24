export function resolveMount(selector?: string): HTMLElement {
    const sel = selector?.trim() || '#kn-root';
    const el = document.querySelector(sel);
    if (el instanceof HTMLElement) {
        return el;
    }
    const byId = document.getElementById('kn-root');
    if (byId) {
        return byId;
    }
    const fallback = document.createElement('div');
    fallback.id = 'kn-root';
    document.body.appendChild(fallback);
    return fallback;
}
