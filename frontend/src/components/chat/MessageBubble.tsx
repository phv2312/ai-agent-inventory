import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ChatMessage } from '../../types/messages';
import { MESSAGE_ROLE } from '../../types/messages';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { fetchChunkByID } from '../../store/inspector.slice';
import { normalizeCitationContent } from '../../utils/citationFormatting';
import { ChevronDownIcon, BotIndicatorIcon } from '../../config/icons';
import {
    parseReasoningSteps,
    reasoningSummaryHeader,
    ReasoningTimeline,
} from './ReasoningTimeline';
import {
    asLinkLabel,
    ExternalCitationChip,
    extractExternalUrls,
    getDomainChipText,
    normalizeExternalUrl,
} from './ExternalCitationChip';
import { getLinkPreviews, type LinkPreviewItem } from '../../services/api/linkPreviews';
import { ContentBlockList } from './ContentBlockList';

interface Props {
    message: ChatMessage;
    isStreaming?: boolean;
}

function asText(children: ReactNode): string {
    if (typeof children === 'string') return children;
    if (typeof children === 'number') return String(children);
    if (Array.isArray(children)) {
        return children.map((child) => asText(child)).join('');
    }
    return '';
}

function extractCitationNumber(children: ReactNode): number | null {
    const text = asText(children);
    const match = text.match(/\d+/);
    if (!match) return null;
    const parsed = Number(match[0]);
    return Number.isFinite(parsed) ? parsed : null;
}

function CitationCircle({ index }: { index: number }) {
    return (
        <span className="inline-flex h-[1.125rem] w-[1.125rem] items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface-elevated)] text-[9px] font-semibold leading-none text-[var(--color-text-muted)] transition-colors group-hover:border-[var(--color-primary)] group-hover:text-[var(--color-primary)]">
            {index}
        </span>
    );
}


export function MessageBubble({ message, isStreaming }: Props) {
    const isUser = message.role === MESSAGE_ROLE.USER;
    const globalStreaming = useAppSelector((state) => state.chat.isStreaming);
    const streamingMessageId = useAppSelector((state) => {
        const idx = state.chat.streamingMessageIdx;
        if (idx === null) return null;
        return state.chat.messages[idx]?.id ?? null;
    });
    const isMessageStreaming =
        Boolean(isStreaming) ||
        (globalStreaming && streamingMessageId === message.id);

    const [isReasoningExpanded, setIsReasoningExpanded] = useState(
        () => Boolean(message.reasoning?.trim()) || !message.content?.trim(),
    );
    const [externalPreviews, setExternalPreviews] = useState<
        Record<string, LinkPreviewItem>
    >({});

    useEffect(() => {
        if (isMessageStreaming && message.reasoning?.trim() && !message.content?.trim()) {
            setIsReasoningExpanded(true);
        }
    }, [isMessageStreaming, message.reasoning, message.content]);

    const reasoningSteps = useMemo(() => {
        const raw = message.reasoning || '';
        const steps = parseReasoningSteps(raw);
        if (steps.length === 0 && raw.trim()) {
            return [{ text: raw.trim(), kind: 'default' as const }];
        }
        return steps;
    }, [message.reasoning]);

    const toggleReasoning = useCallback(() => {
        setIsReasoningExpanded((prev) => !prev);
    }, []);

    const renderedContent = useMemo(
        () => normalizeCitationContent(message.content, message.mappingEvidence),
        [message.content, message.mappingEvidence],
    );

    const externalUrls = useMemo(
        () => extractExternalUrls(renderedContent),
        [renderedContent],
    );

    useEffect(() => {
        if (isMessageStreaming || externalUrls.length === 0) return;

        let isActive = true;
        getLinkPreviews(externalUrls)
            .then((previews) => {
                if (!isActive) return;
                setExternalPreviews((prev) => ({ ...prev, ...previews }));
            })
            .catch((error) => {
                console.warn('Failed to fetch link previews', error);
            });

        return () => {
            isActive = false;
        };
    }, [externalUrls, isMessageStreaming]);

    const dispatch = useAppDispatch();

    const components = useMemo(
        () => ({
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            a: ({ href, children, ...props }: any) => {
                if (href?.startsWith('#ref:')) {
                    const chunkId = href.replace('#ref:', '');
                    const number = extractCitationNumber(children);
                    const disabled = isMessageStreaming;
                    return (
                        <button
                            type="button"
                            disabled={disabled}
                            className={`group relative inline-flex align-middle mx-0.5 ${
                                disabled
                                    ? 'cursor-not-allowed opacity-50'
                                    : 'cursor-pointer'
                            }`}
                            onClick={() => {
                                if (disabled) return;
                                dispatch(
                                    fetchChunkByID({
                                        chunkId,
                                        messageId: message.id,
                                    }),
                                );
                            }}
                            {...props}
                        >
                            {number ? <CitationCircle index={number} /> : children}
                        </button>
                    );
                }

                const normalizedHref = normalizeExternalUrl(href);
                if (!isMessageStreaming && normalizedHref) {
                    return (
                        <ExternalCitationChip
                            href={normalizedHref}
                            domainText={getDomainChipText(normalizedHref)}
                            label={asLinkLabel(children)}
                            preview={externalPreviews[normalizedHref]}
                        />
                    );
                }

                return (
                    <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] underline"
                        {...props}
                    >
                        {children}
                    </a>
                );
            },
        }),
        [dispatch, externalPreviews, isMessageStreaming, message.id],
    );

    if (isUser) {
        return (
            <div className="mb-2 flex w-full justify-end animate-slide-up">
                <div className="max-w-[85%] w-fit rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] px-4 py-2 text-[var(--color-text)]">
                    <p className="text-[15px] leading-relaxed whitespace-pre-wrap">
                        {message.content}
                    </p>
                </div>
            </div>
        );
    }

    const hasReasoning = Boolean(message.reasoning?.trim()) && reasoningSteps.length > 0;

    const hasContentBlocks = message.contentBlocks.length > 0;

    if (!message.content && !hasContentBlocks && !hasReasoning && isMessageStreaming) {
        return (
            <div
                className="mb-4 flex items-center gap-2 py-2 text-sm text-muted animate-slide-up"
                role="status"
                aria-live="polite"
            >
                <BotIndicatorIcon className="h-4 w-4" animated />
            </div>
        );
    }

    const reasoningChrome = hasReasoning ? (
        <div>
            <button
                type="button"
                className="flex w-full items-center gap-2 py-1.5 text-left text-sm text-muted hover:text-[var(--color-text)] transition-colors"
                onClick={toggleReasoning}
            >
                <span className="min-w-0 flex-1 truncate">
                    {reasoningSummaryHeader(message.reasoning ?? '', reasoningSteps)}
                </span>
                <ChevronDownIcon
                    className={`h-4 w-4 shrink-0 text-[var(--color-text-faint)] transition-transform duration-200 ${isReasoningExpanded ? 'rotate-180' : ''}`}
                />
            </button>
            {isReasoningExpanded ? (
                <ReasoningTimeline
                    steps={reasoningSteps}
                    isStreaming={isMessageStreaming && !message.content?.trim()}
                />
            ) : null}
        </div>
    ) : null;

    return (
        <div className="mb-8 flex w-full justify-start animate-slide-up">
            <div className="w-full space-y-3">
                {reasoningChrome}

                {hasContentBlocks ? (
                    <ContentBlockList
                        blocks={message.contentBlocks}
                        isMessageStreaming={isMessageStreaming}
                        markdownComponents={components}
                        mappingEvidence={message.mappingEvidence}
                    />
                ) : message.content ? (
                    <div className="prose prose-invert prose-p:text-[15px] prose-p:leading-relaxed prose-chat max-w-none text-[var(--color-text)]">
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                            {renderedContent}
                        </ReactMarkdown>
                    </div>
                ) : null}
            </div>
        </div>
    );
}
