import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { selectReference } from '../../store/reference.slice';
import type { Reference } from '../../types/references';
import { referenceDisplayName } from '../../types/references';
import { StatusBadge } from './StatusBadge';
import { DocumentTextIcon, EyeIcon, TrashIcon } from '../../config/icons';

interface Props {
    reference: Reference;
    onDelete: (referenceId: string) => Promise<void>;
    onViewChunks: (reference: Reference) => void;
}

export function Row({ reference, onDelete, onViewChunks }: Props) {
    const dispatch = useAppDispatch();
    const { selectedReferenceId } = useAppSelector((state) => state.reference);
    const isSelected = selectedReferenceId === reference.id;
    const displayName = referenceDisplayName(reference);
    const canViewChunks = reference.status === 'completed';

    const handleDelete = async (): Promise<void> => {
        if (!window.confirm(`Delete “${displayName}”? This cannot be undone.`)) {
            return;
        }
        try {
            await onDelete(reference.id);
        } catch (error) {
            window.alert(
                error instanceof Error
                    ? `Could not delete document: ${error.message}`
                    : 'Could not delete document.',
            );
        }
    };

    return (
        <tr
            className={`cursor-pointer transition-colors duration-200 ${
                isSelected
                    ? 'bg-[var(--color-surface-elevated)]'
                    : 'hover:bg-[var(--color-sidebar-hover)]'
            }`}
            onClick={() =>
                dispatch(selectReference(isSelected ? null : reference.id))
            }
        >
            <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                    <DocumentTextIcon className="h-5 w-5 shrink-0 text-muted" />
                    <div>
                        <div className="text-sm font-medium text-[var(--color-text)]">
                            {displayName}
                        </div>
                        {reference.errorMessage && (
                            <div className="mt-0.5 text-xs text-[var(--color-danger)]">
                                {reference.errorMessage}
                            </div>
                        )}
                    </div>
                </div>
            </td>
            <td className="px-4 py-3">
                <StatusBadge status={reference.status} />
            </td>
            <td className="px-4 py-3 text-xs text-muted">
                {new Date(reference.updatedAt).toLocaleString()}
            </td>
            <td className="px-4 py-3">
                <div className="flex items-center justify-end gap-1 whitespace-nowrap">
                <button
                    type="button"
                    aria-label={
                        canViewChunks
                            ? `View chunks for ${displayName}`
                            : `Chunks unavailable until ${displayName} is indexed`
                    }
                    className="rounded-md p-2 text-muted transition-colors hover:bg-blue-500/10 hover:text-blue-400 disabled:cursor-not-allowed disabled:opacity-40"
                    disabled={!canViewChunks}
                    onClick={(event) => {
                        event.stopPropagation();
                        onViewChunks(reference);
                    }}
                    title={canViewChunks ? 'View chunks' : 'Chunks available when indexing is complete'}
                >
                    <EyeIcon className="h-4 w-4" />
                </button>
                <button
                    type="button"
                    aria-label={`Delete ${displayName}`}
                    className="rounded-md p-2 text-muted transition-colors hover:bg-red-500/10 hover:text-red-400"
                    onClick={(event) => {
                        event.stopPropagation();
                        void handleDelete();
                    }}
                    title="Delete document"
                >
                    <TrashIcon className="h-4 w-4" />
                </button>
                </div>
            </td>
        </tr>
    );
}
