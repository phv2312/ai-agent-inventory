import type { Collection, CollectionCreateRequest } from '../../types/collections';
import type { Reference } from '../../types/references';
import { apiFetch } from './client';

const API = '/api/v1';

interface CollectionListResponse {
    items: Collection[];
    skip: number;
    limit: number;
}

export async function createCollection(
    payload: CollectionCreateRequest,
): Promise<Collection> {
    return apiFetch(`${API}/collections/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
}

export async function listCollections(): Promise<Collection[]> {
    const res = await apiFetch<CollectionListResponse>(`${API}/collections/`);
    return res.items;
}

export async function getCollection(id: string): Promise<Collection> {
    return apiFetch(`${API}/collections/${id}`);
}

export async function getReferencesByCollection(id: string): Promise<Reference[]> {
    return apiFetch(`${API}/collections/${id}/references`);
}

export async function getReferencesByCollections(ids: string[]): Promise<Reference[]> {
    const batches = await Promise.all(
        ids.map((id) => getReferencesByCollection(id)),
    );
    return batches.flat();
}
