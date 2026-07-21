import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { Row } from './Row';
import { fetchReferencesByCollection } from '../../store/reference.slice';
import { deleteReference } from '../../services/api/reference';
import { removeReference } from '../../store/reference.slice';
import {
    closeDocumentChunks,
    openDocumentChunks,
} from '../../store/documentChunks.slice';
import type { Reference } from '../../types/references';
import { InboxStackIcon } from '../../config/icons';

export function Table() {
    const dispatch = useAppDispatch();
    const { selectedCollectionId } = useAppSelector((state) => state.collection);
    const { references } = useAppSelector((state) => state.reference);

    const handleDelete = async (referenceId: string): Promise<void> => {
        await deleteReference(referenceId);
        dispatch(removeReference(referenceId));
        dispatch(closeDocumentChunks());
    };

    const handleViewChunks = (reference: Reference): void => {
        dispatch(openDocumentChunks(reference));
    };

    useEffect(() => {
        if (selectedCollectionId) {
            dispatch(fetchReferencesByCollection(selectedCollectionId));
        }
    }, [dispatch, selectedCollectionId]);

    if (!selectedCollectionId) {
        return (
            <div className="rounded-xl border border-app bg-surface p-12 text-center">
                <p className="text-sm text-muted">Select a collection to view documents.</p>
            </div>
        );
    }

    if (references.length === 0) {
        return (
            <div className="rounded-xl border border-app bg-surface p-12 text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-surface-elevated)]">
                    <InboxStackIcon className="h-8 w-8 text-muted" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-[var(--color-text)]">
                    No documents yet
                </h3>
                <p className="text-sm text-muted">Upload a PDF to get started.</p>
            </div>
        );
    }

    return (
        <div className="overflow-hidden rounded-xl border border-app bg-surface shadow-sm">
            <table className="w-full text-sm">
                <thead className="border-b border-app bg-[var(--color-surface-elevated)]">
                    <tr className="text-left text-muted">
                        <th className="px-4 py-3 font-medium">Document</th>
                        <th className="px-4 py-3 font-medium">Status</th>
                        <th className="px-4 py-3 font-medium">Updated</th>
                        <th className="w-24 px-4 py-3">
                            <span className="sr-only">Actions</span>
                        </th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border-subtle)]">
                    {references.map((ref) => (
                        <Row
                            key={ref.id}
                            reference={ref}
                            onDelete={handleDelete}
                            onViewChunks={handleViewChunks}
                        />
                    ))}
                </tbody>
            </table>
        </div>
    );
}
