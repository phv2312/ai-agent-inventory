import { useAppSelector } from '../../hooks/redux';
import { Item } from './CollectionItem';
import { InboxStackIcon } from '../../config/icons';

interface Props {
    onNavigate?: () => void;
}

export function CollectionList({ onNavigate }: Props) {
    const { collections, isLoading } = useAppSelector((state) => state.collection);

    if (isLoading) {
        return (
            <div className="flex flex-1 items-center justify-center py-8">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-primary)]" />
            </div>
        );
    }

    if (collections.length === 0) {
        return (
            <div className="px-4 py-6 text-center">
                <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-surface-elevated)]">
                    <InboxStackIcon className="h-5 w-5 text-muted" />
                </div>
                <p className="text-sm text-muted">No collections yet</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto pb-2">
            {collections.map((collection) => (
                <Item
                    key={collection.id}
                    collection={collection}
                    onNavigate={onNavigate}
                />
            ))}
        </div>
    );
}
