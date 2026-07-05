import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ReactNode } from 'react';
import { useMemo } from 'react';
import type { ContentBlock } from '../../types/contentBlocks';
import {
    CONTENT_BLOCK_TYPE,
    WIDGET_BLOCK_STATUS,
} from '../../types/contentBlocks';
import { normalizeCitationContent } from '../../utils/citationFormatting';
import { InlineVisualizationFrame } from './inlineVisualization/InlineVisualizationFrame';

interface MarkdownComponents {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    a: (props: any) => ReactNode;
}

interface Props {
    blocks: ContentBlock[];
    isMessageStreaming: boolean;
    markdownComponents: MarkdownComponents;
    mappingEvidence?: Record<string, string> | null;
}

export function ContentBlockList({
    blocks,
    isMessageStreaming,
    markdownComponents,
    mappingEvidence,
}: Props) {
    const sorted = useMemo(
        () => [...blocks].sort((a, b) => a.order - b.order),
        [blocks],
    );

    if (sorted.length === 0) {
        return null;
    }

    return (
        <div className="space-y-3">
            {sorted.map((block) => {
                if (block.type === CONTENT_BLOCK_TYPE.TEXT) {
                    const text = normalizeCitationContent(
                        block.text ?? '',
                        mappingEvidence,
                    );
                    if (!text.trim()) return null;
                    return (
                        <div
                            key={block.id}
                            className="prose prose-invert prose-p:text-[15px] prose-p:leading-relaxed prose-chat max-w-none text-[var(--color-text)]"
                        >
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={markdownComponents}
                            >
                                {text}
                            </ReactMarkdown>
                        </div>
                    );
                }

                if (block.type === CONTENT_BLOCK_TYPE.VISUAL_WIDGET) {
                    const streamActive =
                        isMessageStreaming &&
                        block.status === WIDGET_BLOCK_STATUS.STREAMING;
                    const incomplete =
                        block.status === WIDGET_BLOCK_STATUS.INCOMPLETE;
                    return (
                        <InlineVisualizationFrame
                            key={block.id}
                            widgetCode={block.widgetCode ?? ''}
                            title={block.title ?? undefined}
                            loadingMessages={block.loadingMessages}
                            streamActive={streamActive}
                            incomplete={incomplete}
                        />
                    );
                }

                return null;
            })}
        </div>
    );
}
