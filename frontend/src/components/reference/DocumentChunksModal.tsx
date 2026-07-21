import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { XMarkIcon } from '../../config/icons';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import {
    closeDocumentChunks,
    loadDocumentChunkDetail,
    loadDocumentChunkPreviews,
    selectDocumentChunk,
} from '../../store/documentChunks.slice';

export function DocumentChunksModal() {
    const dispatch = useAppDispatch();
    const closeButtonRef = useRef<HTMLButtonElement>(null);
    const {
        reference,
        previews,
        total,
        selectedChunkId,
        selectedChunk,
        isLoadingPreviews,
        isLoadingDetail,
        previewError,
        detailError,
    } = useAppSelector((state) => state.documentChunks);

    useEffect(() => {
        if (!reference) return;
        closeButtonRef.current?.focus();
        dispatch(loadDocumentChunkPreviews({ referenceId: reference.id, offset: 0 }));
    }, [dispatch, reference]);

    useEffect(() => {
        const closeOnEscape = (event: KeyboardEvent): void => {
            if (event.key === 'Escape') dispatch(closeDocumentChunks());
        };
        window.addEventListener('keydown', closeOnEscape);
        return () => window.removeEventListener('keydown', closeOnEscape);
    }, [dispatch]);

    if (!reference) return null;

    const selectChunk = (chunkId: string): void => {
        dispatch(selectDocumentChunk(chunkId));
        dispatch(loadDocumentChunkDetail({ referenceId: reference.id, chunkId }));
    };

    const loadMore = (): void => {
        dispatch(
            loadDocumentChunkPreviews({ referenceId: reference.id, offset: previews.length }),
        );
    };

    return createPortal(
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4"
            onMouseDown={(event) => {
                if (event.currentTarget === event.target) dispatch(closeDocumentChunks());
            }}
        >
            <section
                aria-describedby="document-chunks-description"
                aria-labelledby="document-chunks-title"
                aria-modal="true"
                className="flex h-[min(44rem,calc(100vh-2rem))] w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-app bg-surface shadow-xl"
                role="dialog"
            >
                <header className="flex items-start justify-between border-b border-app px-5 py-4">
                    <div>
                        <h2 id="document-chunks-title" className="text-lg font-semibold text-[var(--color-text)]">
                            Document chunks
                        </h2>
                        <p id="document-chunks-description" className="mt-1 text-sm text-muted">
                            {reference.docName} · pages shown in descending order
                        </p>
                    </div>
                    <button
                        ref={closeButtonRef}
                        type="button"
                        aria-label="Close document chunks"
                        className="rounded-md p-2 text-muted hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text)]"
                        onClick={() => dispatch(closeDocumentChunks())}
                    >
                        <XMarkIcon className="h-5 w-5" />
                    </button>
                </header>
                {previewError ? (
                    <div className="m-5 rounded-lg border border-red-500/40 bg-red-950/30 p-4 text-sm text-red-300" role="alert">
                        <p>Could not load document chunks.</p>
                        <button
                            type="button"
                            className="mt-2 underline"
                            onClick={() => dispatch(loadDocumentChunkPreviews({ referenceId: reference.id, offset: 0 }))}
                        >
                            Retry
                        </button>
                    </div>
                ) : isLoadingPreviews && previews.length === 0 ? (
                    <p className="p-8 text-sm text-muted" role="status">Loading chunk previews…</p>
                ) : previews.length === 0 ? (
                    <p className="p-8 text-sm text-muted">This completed document has no indexed chunks.</p>
                ) : (
                    <div className="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-[20rem_minmax(0,1fr)]">
                        <div className="min-h-0 overflow-y-auto border-b border-app md:border-r md:border-b-0">
                            <ol className="divide-y divide-[var(--color-border-subtle)]">
                                {previews.map((chunk) => (
                                    <li key={chunk.id}>
                                        <button
                                            type="button"
                                            className={`w-full px-4 py-3 text-left hover:bg-[var(--color-surface-elevated)] ${selectedChunkId === chunk.id ? 'bg-[var(--color-surface-elevated)]' : ''}`}
                                            onClick={() => selectChunk(chunk.id)}
                                        >
                                            <span className="block text-xs font-medium text-muted">
                                                #{chunk.ordinal} · {chunk.pageNumber === null ? 'Page unavailable' : `Page ${chunk.pageNumber}`}
                                            </span>
                                            <span className="mt-1 block line-clamp-3 text-sm text-[var(--color-text)]">{chunk.preview}</span>
                                        </button>
                                    </li>
                                ))}
                            </ol>
                            {previews.length < total && (
                                <button type="button" className="m-4 rounded-md border border-app px-3 py-2 text-sm text-muted hover:bg-[var(--color-surface-elevated)]" disabled={isLoadingPreviews} onClick={loadMore}>
                                    {isLoadingPreviews ? 'Loading…' : 'Load more'}
                                </button>
                            )}
                        </div>
                        <article className="min-h-0 overflow-y-auto p-5" aria-live="polite">
                            {isLoadingDetail && <p className="text-sm text-muted">Loading selected chunk…</p>}
                            {detailError && <p className="text-sm text-red-300" role="alert">Could not load this chunk. Select it again to retry.</p>}
                            {selectedChunk && (
                                <div className="space-y-6">
                                    <section aria-labelledby="chunk-metadata-title">
                                        <h3 id="chunk-metadata-title" className="text-sm font-semibold text-[var(--color-text)]">
                                            Metadata
                                        </h3>
                                        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-lg border border-app bg-[var(--color-surface-elevated)] p-4 text-sm">
                                            <dt className="text-muted">Document</dt>
                                            <dd className="break-all text-[var(--color-text)]">{selectedChunk.documentName}</dd>
                                            <dt className="text-muted">Chunk ID</dt>
                                            <dd className="break-all font-mono text-xs text-[var(--color-text)]">{selectedChunk.id}</dd>
                                            <dt className="text-muted">Page</dt>
                                            <dd className="text-[var(--color-text)]">{selectedChunk.pageNumber === null ? 'Unavailable' : selectedChunk.pageNumber}</dd>
                                        </dl>
                                    </section>
                                    <section aria-labelledby="chunk-content-title">
                                        <h3 id="chunk-content-title" className="text-sm font-semibold text-[var(--color-text)]">
                                            Content
                                        </h3>
                                        <div className="prose prose-sm mt-3 max-w-none break-words text-[var(--color-text)] prose-headings:text-[var(--color-text)] prose-p:text-[var(--color-text)] prose-strong:text-[var(--color-text)] prose-a:text-[var(--color-primary)] prose-code:text-[var(--color-text)] prose-pre:bg-[var(--color-surface-elevated)] prose-pre:text-[var(--color-text)] prose-li:text-[var(--color-text)]">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {selectedChunk.text}
                                            </ReactMarkdown>
                                        </div>
                                    </section>
                                </div>
                            )}
                            {!isLoadingDetail && !detailError && !selectedChunk && <p className="text-sm text-muted">Select a preview to read its complete chunk.</p>}
                        </article>
                    </div>
                )}
            </section>
        </div>,
        document.body,
    );
}
