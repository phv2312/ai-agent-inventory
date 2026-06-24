import type { ChunkMetadata } from './metadata';

export type ChunkId = string;

export interface Chunk {
    id: ChunkId;
    text: string;
    metadata: ChunkMetadata;
}

export interface ChunkReadRequest {
    chunkIds: ChunkId[];
}
