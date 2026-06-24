import { useState } from 'react';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { ReferenceUploadFilesModal } from './UploadModal';
import { fetchReferencesByCollection } from '../../store/reference.slice';
import { CloudArrowUpIcon, ArrowPathIcon, DocumentTextIcon } from '../../config/icons';

export function Header() {
    const dispatch = useAppDispatch();
    const { references } = useAppSelector((state) => state.reference);
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
    const selectedCollectionId = useAppSelector(
        (state) => state.collection.selectedCollectionId,
    );

    const handleUploadClick = () => {
        setIsUploadModalOpen(true);
    };

    const handleRefreshClick = () => {
        if (selectedCollectionId) {
            dispatch(fetchReferencesByCollection(selectedCollectionId));
        }
    };

    return (
        <>
            <header className="border-b border-app bg-app px-6 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-surface-elevated)]">
                            <DocumentTextIcon className="h-5 w-5 text-[var(--color-primary)]" />
                        </div>
                        <div>
                            <h1 className="text-lg font-semibold text-[var(--color-text)]">
                                Document Management
                            </h1>
                            <p className="text-sm text-muted">
                                {references.length}{' '}
                                {references.length === 1 ? 'document' : 'documents'} in knowledge
                                base
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleRefreshClick}
                            className={`rounded-lg p-2 transition-all duration-200 ${
                                selectedCollectionId === null
                                    ? 'cursor-not-allowed text-[var(--color-text-faint)]'
                                    : 'cursor-pointer text-muted hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text)]'
                            }`}
                            disabled={selectedCollectionId === null}
                            title="Refresh"
                        >
                            <ArrowPathIcon className="h-5 w-5" />
                        </button>

                        <button
                            onClick={handleUploadClick}
                            disabled={selectedCollectionId === null}
                            className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 ${
                                selectedCollectionId === null
                                    ? 'cursor-not-allowed bg-[var(--color-surface-elevated)] text-[var(--color-text-faint)]'
                                    : 'cursor-pointer bg-[var(--color-surface-elevated)] text-[var(--color-text)] hover:bg-[var(--color-sidebar-hover)]'
                            }`}
                        >
                            <CloudArrowUpIcon className="h-4 w-4" />
                            <span className="hidden sm:inline">Upload Files</span>
                        </button>
                    </div>
                </div>
            </header>

            <ReferenceUploadFilesModal
                isOpen={isUploadModalOpen}
                onClose={() => setIsUploadModalOpen(false)}
            />
        </>
    );
}
