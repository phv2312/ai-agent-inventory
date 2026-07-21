export interface ReferenceChunkPreview {
    id: string;
    ordinal: number;
    pageNumber: number | null;
    preview: string;
}

export interface ReferenceChunksResponse {
    total: number;
    items: ReferenceChunkPreview[];
}

export interface ReferenceChunkDetail {
    id: string;
    documentId: string;
    documentName: string;
    pageNumber: number | null;
    text: string;
}
