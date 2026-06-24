const CITE_TAG_PATTERN = /<CITE>([\s\S]*?)<\/CITE>/gi;

function nextCitationIndex(
    chunkIndexById: Record<string, number>,
    nextIdx: number,
): number {
    const used = Object.values(chunkIndexById);
    if (used.length === 0) return nextIdx;
    return Math.max(nextIdx, ...used) + 1;
}

function seedChunkIndexFromMapping(
    mappingEvidence: Record<string, string>,
): Record<string, number> {
    const chunkIndexById: Record<string, number> = {};
    for (const [idx, chunkId] of Object.entries(mappingEvidence)) {
        const parsed = Number(idx);
        if (!Number.isFinite(parsed) || chunkIndexById[chunkId]) continue;
        chunkIndexById[chunkId] = parsed;
    }
    return chunkIndexById;
}

export function normalizeCitationContent(
    content: string,
    mappingEvidence?: Record<string, string> | null,
): string {
    if (!content) return content;

    const chunkIndexById = mappingEvidence
        ? seedChunkIndexFromMapping(mappingEvidence)
        : {};
    let nextIdx = nextCitationIndex(chunkIndexById, 1);

    let formatted = content.replace(CITE_TAG_PATTERN, (_, raw: string) => {
        const chunkId = raw.trim();
        if (!chunkId) return '';
        if (!chunkIndexById[chunkId]) {
            chunkIndexById[chunkId] = nextIdx;
            nextIdx += 1;
        }
        const idx = chunkIndexById[chunkId];
        return ` [【${idx}】](#ref:${chunkId})`;
    });

    if (mappingEvidence) {
        for (const [idx, chunkId] of Object.entries(mappingEvidence)) {
            const regex = new RegExp(`\\[${idx}\\]`, 'g');
            formatted = formatted.replace(regex, ` [【${idx}】](#ref:${chunkId})`);
        }
    }

    return formatted;
}
