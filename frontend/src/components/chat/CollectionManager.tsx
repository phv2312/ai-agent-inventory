import { useAppDispatch, useAppSelector } from "../../hooks/redux";
import type { Collection } from "../../types/collections";
import {
    clearCollectionsForConversation,
    fetchReferencesByCollections,
    setCollectionsForConversation,
    toggleCollectionForConversation,
} from "../../store/chat.collection.slice";
import { useConversationSelections } from '../../hooks/useConversationSelections';

// Heroicons
function XMarkIcon({ className }: { className?: string }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
    );
}

function FolderIcon({ className }: { className?: string }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
        </svg>
    );
}

function CheckIcon({ className }: { className?: string }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
        </svg>
    );
}

function InboxStackIcon({ className }: { className?: string }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">            <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 7.5h-.75A2.25 2.25 0 0 0 4.5 9.75v7.5a2.25 2.25 0 0 0 2.25 2.25h7.5a2.25 2.25 0 0 0 2.25-2.25v-7.5a2.25 2.25 0 0 0-2.25-2.25h-.75m0-3-3-3m0 0-3 3m3-3v11.25m6-2.25h.75a2.25 2.25 0 0 1 2.25 2.25v7.5a2.25 2.25 0 0 1-2.25 2.25h-7.5a2.25 2.25 0 0 1-2.25-2.25v-.75" />
        </svg>
    );
}

export interface Props {
    isOpen: boolean;
    onClose: () => void;
}

export function CollectionManager({ isOpen, onClose }: Props) {
    const dispatch = useAppDispatch();
    const { collections } = useAppSelector(state => state.collection);
    const { selectedConversationId } = useAppSelector(state => state.conversation);
    const { collections: selectedCollections } = useConversationSelections(selectedConversationId);

    // Don't render if no conversation is selected
    if (!selectedConversationId) {
        return null;
    }

    const handleCollectionToggle = (collection: Collection) => {
        dispatch(toggleCollectionForConversation({ conversationId: selectedConversationId, collection }));
    };

    const handleSelectAll = () => {
        if (selectedCollections.length === collections.length) {
            dispatch(clearCollectionsForConversation({ conversationId: selectedConversationId }));
        } else {
            dispatch(setCollectionsForConversation({ conversationId: selectedConversationId, collections }));
        }
    };

    const handleSave = () => {
        dispatch(setCollectionsForConversation({ conversationId: selectedConversationId, collections: selectedCollections }));
        dispatch(fetchReferencesByCollections({ conversationId: selectedConversationId, collectionIds: selectedCollections.map(c => c.id) }));
        onClose();
    };

    const handleCancel = () => {
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
                onClick={handleCancel}
            />

            {/* Modal */}
            <div className="relative mx-4 max-h-[80vh] w-full max-w-lg overflow-hidden rounded-2xl bg-surface shadow-2xl animate-slide-up">
                <div className="flex items-start justify-between border-b border-app px-6 py-4">
                    <div>
                        <h2 className="text-lg font-semibold text-[var(--color-text)]">Manage Collections</h2>
                        <p className="mt-0.5 text-sm text-muted">Select context for this conversation</p>
                    </div>
                    <button
                        onClick={handleCancel}
                        className="cursor-pointer rounded-lg p-1.5 text-muted transition-all duration-200 hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text)]"
                    >
                        <XMarkIcon className="h-5 w-5" />
                    </button>
                </div>

                <div className="max-h-[50vh] space-y-4 overflow-y-auto p-6">
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-[var(--color-text)]">Available Collections</span>
                        {collections.length > 0 && (
                            <button
                                type="button"
                                onClick={handleSelectAll}
                                className="cursor-pointer text-xs font-medium text-[var(--color-primary)] transition-colors duration-200 hover:text-[var(--color-primary-hover)]"
                            >
                                {selectedCollections.length === collections.length ? 'Deselect All' : 'Select All'}
                            </button>
                        )}
                    </div>

                    {collections.length === 0 ? (
                        <div className="rounded-xl bg-[var(--color-surface-elevated)] px-4 py-8 text-center">
                            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-surface">
                                <InboxStackIcon className="h-6 w-6 text-muted" />
                            </div>
                            <p className="text-sm font-medium text-[var(--color-text)]">No collections available</p>
                            <p className="mt-1 text-xs text-muted">Create collections first to use as references</p>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {collections.map((collection) => {
                                const isSelected = selectedCollections.some((c) => c.id === collection.id);

                                return (
                                    <label
                                        key={collection.id}
                                        className={`flex cursor-pointer items-start rounded-xl border p-3 transition-all duration-200 ${
                                            isSelected
                                                ? 'border-[var(--color-primary)]/40 bg-[var(--color-surface-elevated)]'
                                                : 'border-app bg-surface hover:border-[var(--color-border)] hover:bg-[var(--color-surface-elevated)]'
                                        }`}
                                    >
                                        <div
                                            className={`mr-3 mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-all duration-200 ${
                                                isSelected
                                                    ? 'border-[var(--color-primary)] bg-[var(--color-primary)]'
                                                    : 'border-app bg-surface'
                                            }`}
                                        >
                                            {isSelected && <CheckIcon className="h-3 w-3 text-white" />}
                                        </div>
                                        <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={() => handleCollectionToggle(collection)}
                                            className="sr-only"
                                        />
                                        <div className="min-w-0 flex-1">
                                            <div className="flex items-center gap-2">
                                                <FolderIcon
                                                    className={`h-4 w-4 ${isSelected ? 'text-[var(--color-primary)]' : 'text-muted'}`}
                                                />
                                                <span className="text-sm font-medium text-[var(--color-text)]">
                                                    {collection.name}
                                                </span>
                                            </div>
                                            {collection.description && (
                                                <p className="mt-1 text-xs text-muted">{collection.description}</p>
                                            )}
                                        </div>
                                    </label>
                                );
                            })}
                        </div>
                    )}

                    {selectedCollections.length > 0 && (
                        <div className="mt-4 rounded-xl border border-[var(--color-primary)]/30 bg-[var(--color-surface-elevated)] p-3">
                            <p className="text-sm text-[var(--color-text)]">
                                <span className="font-semibold">{selectedCollections.length}</span> collection
                                {selectedCollections.length !== 1 ? 's' : ''} selected
                            </p>
                        </div>
                    )}
                </div>

                <div className="flex justify-end gap-3 border-t border-app bg-[var(--color-surface-elevated)] px-6 py-4">
                    <button
                        type="button"
                        onClick={handleCancel}
                        className="cursor-pointer rounded-lg border border-app bg-surface px-4 py-2.5 text-sm font-medium text-[var(--color-text)] transition-all duration-200 hover:bg-[var(--color-sidebar-hover)]"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        onClick={handleSave}
                        className="cursor-pointer rounded-lg bg-[var(--color-primary)] px-4 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:bg-[var(--color-primary-hover)]"
                    >
                        Update Collections
                    </button>
                </div>
            </div>
        </div>
    );
}
