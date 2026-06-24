function escapeHtml(text: string): string {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export function showError(mount: HTMLElement, message: string): void {
    mount.innerHTML = `<div class="kn-error" role="alert" style="padding:12px;color:#f09595;font-family:system-ui,sans-serif;font-size:14px;">${escapeHtml(message)}</div>`;
}
