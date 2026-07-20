import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CheckCircleIcon, DocumentTextIcon } from '../../config/icons';

const CHAT_REMARK_PLUGINS = [remarkGfm];

type ReasoningStepKind = 'default' | 'done';

export interface ReasoningStep {
    text: string;
    kind: ReasoningStepKind;
}

function stripMarkdownLight(s: string): string {
    return s
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/`([^`]+)`/g, '$1')
        .trim();
}

function classifyDonePlain(plain: string): boolean {
    return /^(done|completed|finished|xong|hoàn thành)\.?$/i.test(plain);
}

export function parseReasoningSteps(raw: string): ReasoningStep[] {
    const trimmed = raw.trim();
    if (!trimmed) return [];

    let blocks = trimmed
        .split(/\n{2,}/)
        .map((b) => b.trim())
        .filter(Boolean);

    if (blocks.length <= 1) {
        const lines = trimmed
            .split(/\n/)
            .map((l) => l.trim())
            .filter(Boolean);
        const bulletLines = lines.filter(
            (l) => /^[-*•]\s/.test(l) || /^\d+[.)]\s/.test(l),
        );
        if (bulletLines.length >= 2) {
            blocks = bulletLines.map((l) =>
                l
                    .replace(/^[-*•]\s*/, '')
                    .replace(/^\d+[.)]\s*/, '')
                    .trim(),
            );
        }
    }

    if (blocks.length === 0) {
        blocks = [trimmed];
    }

    return blocks.map((text) => {
        const plain = stripMarkdownLight(text);
        return {
            text,
            kind: classifyDonePlain(plain) ? 'done' : 'default',
        };
    });
}

export function reasoningSummaryHeader(raw: string, steps: ReasoningStep[]): string {
    if (steps.length > 0) {
        const first = stripMarkdownLight(steps[0].text).replace(/\s+/g, ' ');
        if (first) {
            return first.length > 72 ? `${first.slice(0, 69)}…` : first;
        }
    }
    const line = stripMarkdownLight(raw.split('\n')[0] || '').replace(/\s+/g, ' ');
    if (line) {
        return line.length > 72 ? `${line.slice(0, 69)}…` : line;
    }
    return 'Thought process';
}

export function ReasoningTimeline({
    steps,
    isStreaming,
}: {
    steps: ReasoningStep[];
    isStreaming?: boolean;
}) {
    return (
        <ul className="mt-2 list-none space-y-0 pl-0">
            {steps.map((step, i) => {
                const isLast = i === steps.length - 1;
                const isDone = step.kind === 'done';
                const isActive = isStreaming && isLast && !isDone;
                const stepKey = `${step.kind}-${step.text}-${i}`;

                return (
                    <li key={stepKey} className="flex items-stretch gap-3">
                        <div className="flex w-6 shrink-0 flex-col items-center">
                            <div
                                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded border shadow-sm ${
                                    isDone
                                        ? 'border-emerald-800/60 bg-emerald-950/40 text-[var(--color-success)]'
                                        : isActive
                                          ? 'border-[var(--color-primary)]/40 bg-[var(--color-surface-elevated)] text-[var(--color-primary)]'
                                          : 'border-app bg-surface text-muted'
                                }`}
                            >
                                {isDone ? (
                                    <CheckCircleIcon className="h-4 w-4" />
                                ) : isActive ? (
                                    <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--color-primary)]" />
                                ) : (
                                    <DocumentTextIcon className="h-3.5 w-3.5" />
                                )}
                            </div>
                            {!isLast ? (
                                <div className="mt-1 min-h-[8px] w-px flex-1 bg-[var(--color-border)]" />
                            ) : null}
                        </div>
                        <div
                            className={`prose prose-invert prose-sm max-w-none min-w-0 flex-1 text-muted prose-p:my-1 prose-headings:my-2 prose-headings:font-serif prose-headings:font-semibold prose-headings:text-[var(--color-text)] prose-a:text-[var(--color-primary)] prose-strong:text-[var(--color-text)] ${isLast ? 'pb-0' : 'pb-4'}`}
                        >
                            <ReactMarkdown remarkPlugins={CHAT_REMARK_PLUGINS}>
                                {step.text}
                            </ReactMarkdown>
                        </div>
                    </li>
                );
            })}
        </ul>
    );
}
