import type { CollectionId } from './conversations';

export type ReferenceId = string;

export const REFERENCE_STATUS = {
    PENDING: 'pending',
    PROCESSING: 'processing',
    COMPLETED: 'completed',
    FAILED: 'failed',
} as const;

export type ReferenceStatus = (typeof REFERENCE_STATUS)[keyof typeof REFERENCE_STATUS];

export interface Reference {
    id: ReferenceId;
    collectionId: CollectionId;
    docName: string;
    filename: string;
    contentType: string;
    status: ReferenceStatus;
    errorMessage: string | null;
    metadata: Record<string, unknown> | null;
    createdAt: string;
    updatedAt: string;
}

/** Display name for UI rows */
export function referenceDisplayName(ref: Reference): string {
    return ref.docName || ref.filename;
}
