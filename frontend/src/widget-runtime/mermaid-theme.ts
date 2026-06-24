/** Map chat dark palette tokens to Mermaid `themeVariables` (theme: base). */
export function buildMermaidThemeVariables(): Record<string, string> {
    const read = (name: string, fallback: string): string => {
        if (typeof document === 'undefined') {
            return fallback;
        }
        const value = getComputedStyle(document.documentElement)
            .getPropertyValue(name)
            .trim();
        return value || fallback;
    };

    const bgPrimary = read('--color-background-primary', '#1a1a1a');
    const bgSecondary = read('--color-background-secondary', '#2a2a2a');
    const textPrimary = read('--color-text-primary', '#e0e0e0');
    const textSecondary = read('--color-text-secondary', '#a0a0a0');
    const border = read('--b', '#404040');
    const line = read('--color-text-info', '#85B7EB');

    return {
        background: bgPrimary,
        mainBkg: bgSecondary,
        primaryColor: bgSecondary,
        primaryTextColor: textPrimary,
        primaryBorderColor: border,
        secondaryColor: bgSecondary,
        secondaryTextColor: textPrimary,
        secondaryBorderColor: border,
        tertiaryColor: bgPrimary,
        tertiaryTextColor: textSecondary,
        tertiaryBorderColor: border,
        lineColor: line,
        clusterBkg: bgPrimary,
        clusterBorder: border,
        titleColor: textPrimary,
        edgeLabelBackground: bgSecondary,
        nodeTextColor: textPrimary,
    };
}
