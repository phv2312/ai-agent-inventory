// Chunk metadata structure
export interface ChunkMetadata {
    docName: string;
    imagePath: string;
    referenceId: string;
    contentType: string | null;
    pageIdx: number | null;
    // Bounding regions for PDF highlighting: [page-index, x1, y1, x2, y2, ...]
    boundingRegions?: number[][];
}
