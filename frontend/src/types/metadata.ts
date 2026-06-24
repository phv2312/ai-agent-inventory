// For form input (structured)
export interface DocumentMetadata {
  doc_id: string;
  doc_type: string;
  effective_date: string;
  keywords: string;
  version: string;
}

// For display (flexible key-value pairs from database)
export interface DocumentMetadataTag {
  name: string;
  value: string;
}

// Chunk metadata structure
export interface ChunkMetadata {
    docName: string;
    imagePath: string;
    referenceId: string;
    contentType: string | null;
    pageIdx: number | null;
    // Bounding regions for PDF highlighting: [page-index, x1, y1, x2, y2, ...]
    boundingRegions?: number[][];
    // Flexible document metadata tags from database
    documentTags?: DocumentMetadataTag[];
}

/** Root list model from API: GET/PUT reference metadata. */
export type ListDocumentMetadataTag = DocumentMetadataTag[];

export interface DocumentMetadataDisplay {
  referenceId: number;
  tags: DocumentMetadataTag[];
}
