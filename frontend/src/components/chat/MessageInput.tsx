import { useMemo, useRef, useState } from 'react';
import { Mention, MentionsInput } from 'react-mentions';
import { useChatStream } from '../../hooks/useChatStream';
import { useAppSelector } from '../../hooks/redux';
import { useConversationSelections } from '../../hooks/useConversationSelections';
import { PaperAirplaneIcon } from '../../config/icons';
import { referenceDisplayName } from '../../types/references';
import { parseChatCommand } from '../../utils/chatCommands';

const mentionStyle = {
    textDecoration: 'underline',
    textDecorationColor: 'var(--color-primary)',
    textDecorationThickness: '2px',
    textUnderlineOffset: '2px',
};

interface MessageInputProps {
    variant?: 'centered' | 'bottom';
    text?: string;
    onTextChange?: (value: string) => void;
}

const THREAD_MAX_W = 'max-w-3xl';

export function MessageInput({
    variant = 'bottom',
    text: controlledText,
    onTextChange,
}: MessageInputProps) {
    const composerInputRef = useRef<HTMLTextAreaElement>(null);
    const [internalText, setInternalText] = useState('');
    const text = controlledText ?? internalText;
    const setText = onTextChange ?? setInternalText;

    const { sendMessage, isStreaming, isResolvingInterruption, cancel } =
        useChatStream();
    const pendingInterruption = useAppSelector(
        (state) => state.chat.pendingInterruption,
    );
    const { selectedConversationId } = useAppSelector((state) => state.conversation);
    const { references } = useConversationSelections(selectedConversationId);

    const mentionData = useMemo(
        () =>
            references.map((ref) => ({
                id: ref.docName,
                display: referenceDisplayName(ref),
            })),
        [references],
    );

    if (!selectedConversationId) {
        return (
            <div className="shrink-0 px-6 py-8 text-center">
                <p className="text-sm text-muted">
                    Select a conversation to start chatting
                </p>
            </div>
        );
    }

    const submitForm = (e: React.FormEvent) => {
        e.preventDefault();
        const trimmed = text.trim();
        const command = parseChatCommand(trimmed);
        if (
            !command.message
            || isStreaming
            || isResolvingInterruption
            || pendingInterruption
        ) {
            return;
        }
        setText('');
        void sendMessage(trimmed);
    };

    const isCentered = variant === 'centered';
    const wrapperClass = isCentered ? 'w-full' : 'shrink-0 bg-app';

    const placeholder = pendingInterruption
        ? 'Review the global query plan to continue'
        : isCentered
          ? 'Ask anything, or use /global for a planned query'
          : 'Write a message, or start with /global...';
    const isBlocked = Boolean(
        isStreaming || isResolvingInterruption || pendingInterruption,
    );

    return (
        <div className={wrapperClass}>
            <div
                className={`mx-auto w-full min-w-0 ${
                    isCentered
                        ? 'px-0 pb-0 pt-0'
                        : `${THREAD_MAX_W} px-4 pb-8 pt-2`
                }`}
            >
                <form
                    className="w-full min-w-0"
                    onSubmit={submitForm}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            submitForm(e);
                        }
                    }}
                >
                    <div className="message-composer-card overflow-hidden rounded-3xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] shadow-md">
                        <div className={`px-4 ${isCentered ? 'pt-3.5' : 'pt-3'}`}>
                            <MentionsInput
                                inputRef={composerInputRef}
                                value={text}
                                onChange={(_, newValue) => setText(newValue)}
                                placeholder={placeholder}
                                allowSuggestionsAboveCursor
                                disabled={isBlocked}
                                className={`composer-mentions mentions w-full border-0 bg-transparent shadow-none ring-0 ${
                                    isCentered
                                        ? 'min-h-[5.25rem]'
                                        : 'min-h-[3.25rem] composer-mentions-thread'
                                }`}
                            >
                                <Mention
                                    trigger="@"
                                    data={mentionData}
                                    markup="@[__display__](__id__)"
                                    displayTransform={(_, display) => `@${display}`}
                                    style={mentionStyle}
                                />
                            </MentionsInput>
                        </div>

                        <div className="flex items-center justify-end gap-2 px-3 pb-3 pt-1 sm:px-4">
                            {isStreaming ? (
                                <button
                                    type="button"
                                    onClick={cancel}
                                    className="rounded-full px-4 py-1.5 text-sm font-medium text-[var(--color-danger)] transition-colors hover:bg-red-950/40 cursor-pointer"
                                >
                                    Stop
                                </button>
                            ) : (
                                <button
                                    type="submit"
                                    disabled={
                                        !parseChatCommand(text).message || isBlocked
                                    }
                                    className="inline-flex items-center justify-center rounded-full bg-[var(--color-primary)] p-2.5 text-white shadow-sm transition-colors hover:bg-[var(--color-primary-hover)] disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
                                    aria-label="Send message"
                                >
                                    <PaperAirplaneIcon className="h-4 w-4" />
                                </button>
                            )}
                        </div>
                    </div>
                </form>
            </div>
        </div>
    );
}
