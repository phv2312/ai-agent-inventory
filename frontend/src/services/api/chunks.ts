import type { Chunk } from '../../types/chunks';
import { toCamelCaseObject } from '../../utils/case';
import { BASE_URL } from './env';

const API = '/api/v1';

interface ChunkItemResponse {
    id: string;
    text: string | null;
    metadata: Record<string, unknown> | null;
    status: string;
    warnings: string[] | null;
}

interface ChunksBatchResponse {
    items: ChunkItemResponse[];
}

export async function getChunksByIds(
    chunkIds: string[],
    messageId?: string,
): Promise<Chunk[]> {
    const params = new URLSearchParams();
    chunkIds.forEach((id) => params.append('chunk_ids', id));
    if (messageId) {
        params.append('message_id', messageId);
    }

    const res = await fetch(`${BASE_URL}${API}/chunks/?${params.toString()}`, {
        headers: { accept: 'application/json' },
    });
    if (!res.ok) {
        throw new Error(await res.text());
    }
    const data = toCamelCaseObject(await res.json()) as ChunksBatchResponse;

    return data.items
        .filter((item) => item.status === 'ok' && item.text)
        .map((item) => ({
            id: item.id,
            text: item.text ?? '',
            metadata: {
                docName: String(item.metadata?.docName ?? item.metadata?.doc_name ?? ''),
                pageIdx: (item.metadata?.pageIdx ?? item.metadata?.page_idx ?? null) as number | null,
                referenceId: String(item.metadata?.referenceId ?? item.metadata?.reference_id ?? ''),
                imagePath: '',
                contentType: 'text',
            },
        }));
}
