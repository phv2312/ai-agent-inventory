import { QUICK_PROMPTS } from '../../constants/quickPrompts';

interface Props {
    onSelect: (template: string) => void;
}

export function QuickPromptPills({ onSelect }: Props) {
    return (
        <div className="flex flex-wrap items-center justify-center gap-2 px-4">
            {QUICK_PROMPTS.map((prompt) => (
                <button
                    key={prompt.id}
                    type="button"
                    onClick={() => onSelect(prompt.template)}
                    className="rounded-full border border-[var(--color-border)] bg-transparent px-4 py-2 text-sm text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text)] cursor-pointer"
                >
                    {prompt.label}
                </button>
            ))}
        </div>
    );
}
