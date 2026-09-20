import { useState } from 'react';
import type { InterruptionData } from '../../services/api/chats';
import { useChatStream } from '../../hooks/useChatStream';
import { useAppSelector } from '../../hooks/redux';
import { SparklesIcon } from '../../config/icons';

export function InterruptionDialog({ review }: { review?: InterruptionData }) {
    const [showRevision, setShowRevision] = useState(false);
    const [feedback, setFeedback] = useState('');
    const active = useAppSelector((state) => state.chat.pendingInterruption);
    const pending = review ?? active;
    const interruptionError = useAppSelector(
        (state) => state.chat.interruptionError,
    );
    const { isStreaming, isResolvingInterruption, resolveInterruption } =
        useChatStream();
    const busy = isStreaming || isResolvingInterruption;

    if (!pending) return null;

    return (
        <div
            className="flex justify-center px-4 py-4"
            role="dialog"
            aria-modal="false"
            aria-labelledby={`global-plan-title-${pending.id ?? pending.version}`}
        >
            <div className="flex max-h-full w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl">
                <div className="border-b border-[var(--color-border)] px-6 py-5">
                    <div className="flex items-start gap-3">
                        <span className="mt-0.5 rounded-xl bg-blue-500/15 p-2 text-[var(--color-primary)]">
                            <SparklesIcon className="h-5 w-5" />
                        </span>
                        <div>
                            <h2
                                id={`global-plan-title-${pending.id ?? pending.version}`}
                                className="text-lg font-semibold text-[var(--color-text)]"
                            >
                                Review global query plan
                            </h2>
                            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                                {review ? "Saved plan review" : "Approve this plan before researching. Chat is paused while this review is open."}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="overflow-y-auto px-6 py-5">
                    {pending.interruptions.map((interruption) => (
                        <div key={interruption.id} className="space-y-4">
                            {interruption.plan ? (
                                <>
                                    <div>
                                        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-faint)]">
                                            Query
                                        </p>
                                        <p className="mt-1 text-sm font-medium text-[var(--color-text)]">
                                            {interruption.plan.query}
                                        </p>
                                    </div>
                                    <ol className="space-y-3">
                                        {interruption.plan.sections.map(
                                            (section, index) => (
                                                <li
                                                    key={`${section.title}-${index}`}
                                                    className="flex gap-3 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-background)] p-4"
                                                >
                                                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-500/15 text-xs font-semibold text-[var(--color-primary)]">
                                                        {index + 1}
                                                    </span>
                                                    <div className="min-w-0">
                                                        <p className="text-sm font-semibold text-[var(--color-text)]">
                                                            {section.title}
                                                        </p>
                                                        <p className="mt-1 text-sm leading-6 text-[var(--color-text-muted)]">
                                                            {section.purpose}
                                                        </p>
                                                    </div>
                                                </li>
                                            ),
                                        )}
                                    </ol>
                                </>
                            ) : (
                                <p className="rounded-xl border border-[var(--color-warning)]/30 bg-yellow-950/20 p-4 text-sm text-[var(--color-warning)]">
                                    The agent requested approval, but no readable plan
                                    was provided.
                                </p>
                            )}
                        </div>
                    ))}

                    {!review && showRevision && (
                        <div className="mt-5">
                            <label
                                htmlFor="global-plan-feedback"
                                className="mb-2 block text-sm font-medium text-[var(--color-text)]"
                            >
                                What should change?
                            </label>
                            <textarea
                                id="global-plan-feedback"
                                value={feedback}
                                onChange={(event) => setFeedback(event.target.value)}
                                rows={3}
                                autoFocus
                                disabled={busy}
                                placeholder="For example: add a risk section and compare the last three years."
                                className="w-full resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2.5 text-sm text-[var(--color-text)] outline-none transition-colors focus:border-[var(--color-primary)]"
                            />
                        </div>
                    )}

                    {!review && interruptionError && (
                        <p className="mt-4 rounded-lg bg-red-950/30 px-3 py-2 text-sm text-[var(--color-danger)]">
                            {interruptionError}
                        </p>
                    )}
                </div>

                {review ? (
                    <div className="border-t border-[var(--color-border)] px-6 py-4 text-sm text-[var(--color-text)]">
                        <p className="font-semibold">Your answer: {review.decision}</p>
                        {review.feedback && <p className="mt-2 whitespace-pre-wrap">{review.feedback}</p>}
                    </div>
                ) : <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-border)] px-6 py-4">
                    <button
                        type="button"
                        disabled={busy}
                        onClick={() => void resolveInterruption('cancel')}
                        className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--color-danger)] transition-colors hover:bg-red-950/30 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        Cancel global query
                    </button>

                    <div className="flex flex-wrap justify-end gap-2">
                        {showRevision ? (
                            <>
                                <button
                                    type="button"
                                    disabled={busy}
                                    onClick={() => setShowRevision(false)}
                                    className="rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-medium text-[var(--color-text)] hover:bg-[var(--color-surface-elevated)] disabled:opacity-50"
                                >
                                    Back
                                </button>
                                <button
                                    type="button"
                                    disabled={busy || !feedback.trim()}
                                    onClick={() => {
                                        const revisionFeedback = feedback.trim();
                                        setShowRevision(false);
                                        setFeedback('');
                                        void resolveInterruption(
                                            'revise',
                                            revisionFeedback,
                                        );
                                    }}
                                    className="rounded-lg bg-[var(--color-surface-elevated)] px-4 py-2 text-sm font-semibold text-[var(--color-text)] hover:bg-[var(--color-sidebar-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {busy ? 'Submitting...' : 'Submit changes'}
                                </button>
                            </>
                        ) : (
                            <>
                                <button
                                    type="button"
                                    disabled={busy}
                                    onClick={() => setShowRevision(true)}
                                    className="rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-medium text-[var(--color-text)] hover:bg-[var(--color-surface-elevated)] disabled:opacity-50"
                                >
                                    Request changes
                                </button>
                                <button
                                    type="button"
                                    disabled={busy}
                                    onClick={() =>
                                        void resolveInterruption('approve')
                                    }
                                    className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--color-primary-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    {busy ? 'Running plan...' : 'Approve & continue'}
                                </button>
                            </>
                        )}
                    </div>
                </div>}
            </div>
        </div>
    );
}
