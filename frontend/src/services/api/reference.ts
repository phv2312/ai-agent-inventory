import type { Reference } from '../../types/references';
import { apiFetch } from './client';

const API = '/api/v1';

export async function uploadReference(
    file: File,
    collectionId: string,
    docName?: string,
): Promise<Reference> {
    const formData = new FormData();
    formData.append('reference', file);
    formData.append('collection_id', collectionId);
    if (docName) {
        formData.append('metadata', JSON.stringify({ doc_name: docName }));
    }

    return apiFetch(`${API}/references/`, {
        method: 'POST',
        body: formData,
    });
}

export async function getReference(id: string): Promise<Reference> {
    return apiFetch(`${API}/references/${id}`);
}

export async function refreshReferencesByIds(ids: string[]): Promise<Reference[]> {
    return Promise.all(ids.map((id) => getReference(id)));
}
