import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { openCreateModal } from '../../store/collection.slice';
import { Item } from './CollectionItem';
import { CreateModal } from './CreateModal';
import { FolderPlusIcon, FolderIcon, InboxStackIcon } from '../../config/icons';

export function Collection() {
    const dispatch = useAppDispatch();
    const { collections, isLoading, error } = useAppSelector((state) => state.collection);

    const handleCreateClick = () => {
        dispatch(openCreateModal());
    };

    return (
        <div className="flex h-full flex-col">
            <div className="border-b border-app p-4">
                <div className="mb-4 flex items-center gap-2">
                    <FolderIcon className="h-5 w-5 text-muted" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted">
                        Collections
                    </span>
                </div>
                <button
                    onClick={handleCreateClick}
                    disabled={isLoading}
                    className={`flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
                        isLoading
                            ? 'cursor-not-allowed bg-[var(--color-surface-elevated)] text-[var(--color-text-faint)]'
                            : 'cursor-pointer bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)]'
                    }`}
                >
                    <FolderPlusIcon className="h-4 w-4" />
                    Create Collection
                </button>
            </div>

            {error && (
                <div className="border-b border-[var(--color-danger)]/30 bg-red-950/30 p-4">
                    <p className="text-sm text-[var(--color-danger)]">{error}</p>
                </div>
            )}

            <div className="flex-1 overflow-y-auto">
                {isLoading ? (
                    <div className="p-8 text-center">
                        <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-border)] border-t-[var(--color-primary)]" />
                        <p className="text-sm text-muted">Loading collections...</p>
                    </div>
                ) : collections.length === 0 ? (
                    <div className="p-8 text-center">
                        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-surface-elevated)]">
                            <InboxStackIcon className="h-6 w-6 text-muted" />
                        </div>
                        <p className="mb-1 text-sm font-medium text-[var(--color-text)]">
                            No collections yet
                        </p>
                        <p className="text-xs text-muted">
                            Create your first collection to get started
                        </p>
                    </div>
                ) : (
                    <div className="p-2">
                        {collections.map((collection) => (
                            <Item key={collection.id} collection={collection} />
                        ))}
                    </div>
                )}
            </div>

            <div className="border-t border-app p-3">
                <div className="text-center text-xs text-muted">Knowledge Network</div>
            </div>

            <CreateModal />
        </div>
    );
}
