import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { selectCollection } from '../../store/collection.slice';
import type { Collection } from '../../types/collections';
import { FolderIcon, ClockIcon } from '../../config/icons';

interface Props {
    collection: Collection;
    onNavigate?: () => void;
}

export function Item({ collection, onNavigate }: Props) {
    const dispatch = useAppDispatch();
    const { selectedCollectionId } = useAppSelector((state) => state.collection);

    const isSelected = selectedCollectionId === collection.id;

    const handleClick = () => {
        dispatch(selectCollection(collection.id));
        onNavigate?.();
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffDays = Math.floor(
            Math.abs(now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24),
        );

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    };

    return (
        <div
            className={`group mx-2 my-1 cursor-pointer rounded-lg border px-3 py-3 transition-all duration-200 ${
                isSelected
                    ? 'border-[var(--color-primary)]/40 bg-[var(--color-sidebar-active)]'
                    : 'border-transparent hover:bg-[var(--color-sidebar-hover)]'
            }`}
            onClick={handleClick}
        >
            <div className="flex items-start gap-3">
                <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors duration-200 ${
                        isSelected
                            ? 'bg-[var(--color-surface-elevated)]'
                            : 'bg-[var(--color-surface)] group-hover:bg-[var(--color-surface-elevated)]'
                    }`}
                >
                    <FolderIcon
                        className={`h-5 w-5 ${isSelected ? 'text-[var(--color-primary)]' : 'text-muted'}`}
                    />
                </div>

                <div className="min-w-0 flex-1">
                    <h3
                        className={`mb-0.5 truncate text-sm font-medium ${
                            isSelected ? 'text-[var(--color-text)]' : 'text-[var(--color-sidebar-text)]'
                        }`}
                        title={collection.name}
                    >
                        {collection.name}
                    </h3>
                    {collection.description && (
                        <p className="mb-2 line-clamp-2 text-xs text-muted">
                            {collection.description}
                        </p>
                    )}
                    <div className="flex items-center gap-1 text-xs text-muted">
                        <ClockIcon className="h-3 w-3" />
                        {formatDate(collection.updatedAt)}
                    </div>
                </div>
            </div>
        </div>
    );
}
