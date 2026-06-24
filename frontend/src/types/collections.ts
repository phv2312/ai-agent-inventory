export type CollectionId = string;

export interface Collection {
    id: CollectionId;
    name: string;
    description?: string;
    createdAt: string;
    updatedAt: string;
}

export interface CollectionStats {
    referenceCount: number;
    chunkCount: number;
}

export interface CollectionCreateRequest {
    name: string;
    description?: string;
}

export interface CollectionUpdateRequest {
    id: CollectionId;
    name?: string;
    description?: string;
}

export interface CollectionDeleteRequest {
    id: CollectionId;
}
