import { useState } from 'react';
import { createPortal } from 'react-dom';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import {
    closeCreateModal,
    createNewCollection,
    setLoading,
    setError,
} from '../../store/collection.slice';
import type { CollectionCreateRequest } from '../../types/collections';

export function CreateModal() {
    const dispatch = useAppDispatch();
    const { isCreateModalOpen, isLoading, error } = useAppSelector(
        (state) => state.collection,
    );

    const [name, setName] = useState('');
    const [description, setDescription] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name.trim()) return;

        dispatch(setLoading(true));
        try {
            const newCollectionRequest: CollectionCreateRequest = {
                name: name.trim(),
                description: description.trim() || undefined,
            };

            dispatch(createNewCollection(newCollectionRequest));

            setName('');
            setDescription('');
            dispatch(closeCreateModal());
        } catch (err) {
            const errorMessage =
                err instanceof Error ? err.message : 'Failed to create collection';
            dispatch(setError(errorMessage));
        } finally {
            dispatch(setLoading(false));
        }
    };

    const handleClose = () => {
        if (!isLoading) {
            setName('');
            setDescription('');
            dispatch(closeCreateModal());
        }
    };

    if (!isCreateModalOpen) return null;

    return createPortal(
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60">
            <div className="mx-4 w-full max-w-md rounded-lg bg-surface shadow-xl">
                <div className="border-b border-app px-6 py-4">
                    <h2 className="text-lg font-semibold text-[var(--color-text)]">
                        Create New Collection
                    </h2>
                </div>

                {error && (
                    <div className="border-b border-[var(--color-danger)]/30 bg-red-950/30 px-6 py-3">
                        <p className="text-sm text-[var(--color-danger)]">{error}</p>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4 p-6">
                    <div>
                        <label
                            htmlFor="collection-name"
                            className="mb-2 block text-sm font-medium text-[var(--color-text)]"
                        >
                            Collection Name *
                        </label>
                        <input
                            id="collection-name"
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g., Marketing Materials"
                            className="w-full rounded-lg border border-app bg-[var(--color-surface-elevated)] px-3 py-2 text-[var(--color-text)] focus:border-[var(--color-primary)] focus:outline-none"
                            disabled={isLoading}
                            required
                        />
                    </div>

                    <div>
                        <label
                            htmlFor="collection-description"
                            className="mb-2 block text-sm font-medium text-[var(--color-text)]"
                        >
                            Description
                        </label>
                        <textarea
                            id="collection-description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Brief description of what this collection contains..."
                            rows={3}
                            className="w-full resize-none rounded-lg border border-app bg-[var(--color-surface-elevated)] px-3 py-2 text-[var(--color-text)] focus:border-[var(--color-primary)] focus:outline-none"
                            disabled={isLoading}
                        />
                    </div>

                    <div className="flex justify-end space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="rounded-lg bg-[var(--color-surface-elevated)] px-4 py-2 text-sm font-medium text-[var(--color-text)] transition-colors hover:bg-[var(--color-sidebar-hover)]"
                            disabled={isLoading}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!name.trim() || isLoading}
                            className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-primary-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {isLoading ? 'Creating...' : 'Create Collection'}
                        </button>
                    </div>
                </form>
            </div>
        </div>,
        document.body,
    );
}
