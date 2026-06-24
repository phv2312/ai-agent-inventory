import { useSelector, useDispatch } from 'react-redux';
import type { RootState } from '../../store';
import { closeInspector } from '../../store/inspector.slice';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { XMarkIcon, BookOpenIcon, DocumentTextIcon } from '../../config/icons';

export function Inspector() {
    const dispatch = useDispatch();
    const { isOpen, selectedChunk, loading, error } = useSelector(
        (state: RootState) => state.inspector,
    );

    if (!isOpen) return null;

    return (
        <aside className="flex w-80 shrink-0 animate-slide-right flex-col border-l border-app bg-app">
            <div className="flex items-center justify-between border-b border-app px-4 py-3">
                <div className="flex items-center gap-2">
                    <BookOpenIcon className="h-5 w-5 text-[var(--color-primary)]" />
                    <span className="text-sm font-semibold text-[var(--color-text)]">
                        Document Reference
                    </span>
                </div>
                <button
                    type="button"
                    onClick={() => dispatch(closeInspector())}
                    className="cursor-pointer rounded-lg p-1.5 text-muted transition-all duration-200 hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text)]"
                >
                    <XMarkIcon className="h-4 w-4" />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto">
                {loading && (
                    <p className="px-4 py-3 text-sm text-muted">Loading source…</p>
                )}
                {error && (
                    <p className="px-4 py-3 text-sm text-[var(--color-danger)]">{error}</p>
                )}
                {selectedChunk && !loading && (
                    <>
                        <div className="border-b border-app bg-surface px-4 py-3">
                            <div className="flex items-start gap-3">
                                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--color-surface-elevated)]">
                                    <DocumentTextIcon className="h-5 w-5 text-[var(--color-primary)]" />
                                </div>
                                <div className="min-w-0">
                                    <h3 className="truncate text-sm font-semibold text-[var(--color-text)]">
                                        {selectedChunk.metadata.docName}
                                    </h3>
                                    {selectedChunk.metadata.pageIdx != null && (
                                        <p className="mt-0.5 text-xs text-muted">
                                            Page {selectedChunk.metadata.pageIdx + 1}
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="prose prose-invert prose-sm max-w-none px-4 py-4">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                rehypePlugins={[rehypeRaw]}
                            >
                                {selectedChunk.text}
                            </ReactMarkdown>
                        </div>
                    </>
                )}
            </div>
        </aside>
    );
}
