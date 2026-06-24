import { REFERENCE_STATUS, type ReferenceStatus } from '../../types/references';

interface Props {
    status: ReferenceStatus;
}

export function StatusBadge({ status }: Props) {
    const map: Record<ReferenceStatus, string> = {
        [REFERENCE_STATUS.PENDING]: 'bg-[var(--color-surface-elevated)] text-[var(--color-text-muted)]',
        [REFERENCE_STATUS.PROCESSING]: 'bg-yellow-950/50 text-[var(--color-warning)]',
        [REFERENCE_STATUS.COMPLETED]: 'bg-emerald-950/50 text-[var(--color-success)]',
        [REFERENCE_STATUS.FAILED]: 'bg-red-950/50 text-[var(--color-danger)]',
    };

    const label: Record<ReferenceStatus, string> = {
        [REFERENCE_STATUS.PENDING]: 'Pending',
        [REFERENCE_STATUS.PROCESSING]: 'Processing',
        [REFERENCE_STATUS.COMPLETED]: 'Ready',
        [REFERENCE_STATUS.FAILED]: 'Failed',
    };

    return (
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${map[status]}`}>
            {label[status]}
        </span>
    );
}
