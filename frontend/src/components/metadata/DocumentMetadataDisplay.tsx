import type { DocumentMetadataTag, ChunkMetadata } from '../../types/metadata';

interface DocumentMetadataDisplayProps {
    tags?: DocumentMetadataTag[];
    metadata?: ChunkMetadata;
    variant?: 'full' | 'compact' | 'tags';
    className?: string;
}

function formatMetadataFieldName(fieldName: string): string {
    const fieldNameMap: Record<string, string> = {
        'doc_type': 'Document Type',
        'doc_id': 'Document ID',
        'effective_date': 'Effective Date',
        'keywords': 'Keywords',
        'version': 'Version'
    };

    return fieldNameMap[fieldName] || fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function MetadataTag({ name, value }: { name: string; value: string }) {
    const displayName = formatMetadataFieldName(name);

    return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            <span className="font-semibold mr-1">{displayName}:</span>
            {value}
        </span>
    );
}

// Canonical display order
const FIELD_ORDER = ['doc_id', 'doc_type', 'effective_date', 'version', 'keywords'];

function sortTags(tags: DocumentMetadataTag[]) {
    return [...tags].sort((a, b) => {
        const ai = FIELD_ORDER.indexOf(a.name);
        const bi = FIELD_ORDER.indexOf(b.name);
        if (ai === -1 && bi === -1) return 0;
        if (ai === -1) return 1;
        if (bi === -1) return -1;
        return ai - bi;
    });
}

export function DocumentMetadataDisplay({
    tags,
    metadata,
    variant = 'full',
    className = ''
}: DocumentMetadataDisplayProps) {
    // Extract tags from metadata if provided, otherwise use tags prop
    let displayTags: DocumentMetadataTag[] = [];

    if (metadata?.documentTags) {
        displayTags = metadata.documentTags;
    } else if (tags) {
        displayTags = tags;
    }

    if (!displayTags || displayTags.length === 0) {
        return null;
    }

    const sortedTags = sortTags(displayTags);

    if (variant === 'tags') {
        return (
            <div className={`flex flex-wrap gap-1 ${className}`}>
                {sortedTags.map((tag, index) => (
                    <MetadataTag
                        key={index}
                        name={tag.name}
                        value={tag.value}
                    />
                ))}
            </div>
        );
    }

    if (variant === 'compact') {
        return (
            <div className={`space-y-1 ${className}`}>
                {sortedTags.map((tag, index) => (
                    <div key={index} className="flex justify-between text-sm">
                        <span className="font-medium text-gray-600">{formatMetadataFieldName(tag.name)}:</span>
                        <span className="text-gray-900">{tag.value}</span>
                    </div>
                ))}
            </div>
        );
    }

    // Full variant
    return (
        <div className={`space-y-2 ${className}`}>
            <h4 className="text-sm font-semibold text-gray-900 border-b border-gray-200 pb-2 mb-3">
                Document Metadata
            </h4>
            <div className="space-y-2">
                {sortedTags.map((tag, index) => {
                    const isReadOnly = tag.name === 'version';
                    return (
                        <div key={index} className="flex items-start gap-3">
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider min-w-[110px] pt-1 shrink-0">
                                {formatMetadataFieldName(tag.name)}
                                {isReadOnly && (
                                    <span className="normal-case font-normal text-gray-400 ml-1">(read-only)</span>
                                )}
                            </span>
                            <span className={`text-sm px-2.5 py-1 rounded-md flex-1 min-w-0 break-words ${isReadOnly ? 'text-gray-500 bg-gray-50' : 'text-gray-900 bg-gray-50'}`}>
                                {tag.value}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
