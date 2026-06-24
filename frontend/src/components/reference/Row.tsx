import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { selectReference } from '../../store/reference.slice';
import type { Reference } from '../../types/references';
import { referenceDisplayName } from '../../types/references';
import { StatusBadge } from './StatusBadge';
import { DocumentTextIcon } from '../../config/icons';

interface Props {
    reference: Reference;
}

export function Row({ reference }: Props) {
    const dispatch = useAppDispatch();
    const { selectedReferenceId } = useAppSelector((state) => state.reference);
    const isSelected = selectedReferenceId === reference.id;
    const displayName = referenceDisplayName(reference);

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
        </tr>
    );
}
