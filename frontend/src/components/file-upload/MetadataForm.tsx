import { useState } from 'react';
import type { DocumentMetadata } from '../../types/metadata';
import { TagChipsInput } from './TagChipsInput';
import { useMetadataSuggestions } from '../../hooks/useMetadataSuggestions';

interface MetadataFormProps {
    onMetadataChange: (metadata: DocumentMetadata | null) => void;
    disabled?: boolean;
    fileNames?: string[];
}

export function MetadataForm({ onMetadataChange, disabled = false }: MetadataFormProps) {
    const { suggestions } = useMetadataSuggestions();
    const [showMetadata, setShowMetadata] = useState(false);
    const [metadata, setMetadata] = useState<DocumentMetadata>({
        doc_type: '',
        doc_id: '',
        effective_date: '',
        version: '',
        keywords: '',
    });

    const handleChange = (field: keyof DocumentMetadata, value: string) => {
        const newMetadata = { ...metadata, [field]: value };
        setMetadata(newMetadata);
        if (showMetadata) {
            onMetadataChange(newMetadata);
        }
    };

    const toggleExpand = () => {
        if (disabled) return;
        const nextState = !showMetadata;
        setShowMetadata(nextState);
        onMetadataChange(nextState ? metadata : null);
    };

    return (
        <div className="border border-gray-200 rounded-lg overflow-hidden mb-4 bg-white shadow-sm">
            <button
                type="button"
                onClick={toggleExpand}
                disabled={disabled}
                className={`w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition-colors ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
                <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-900">
                        Document Metadata
                    </span>
                </div>
                <svg
                    className={`w-5 h-5 text-slate-400 transform transition-transform duration-200 ${showMetadata ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {showMetadata && (
                <div className="flex flex-col gap-4 p-4 border-t border-gray-200">

                    {/* Dropdown Suggestions */}
                    {!disabled && (
                        <>
                            <datalist id="doc-type-suggestions">
                                {(suggestions['doc_type'] || []).map(val => (
                                    <option key={val} value={val} />
                                ))}
                            </datalist>
                            <datalist id="doc-id-suggestions">
                                {(suggestions['doc_id'] || []).map(val => (
                                    <option key={val} value={val} />
                                ))}
                            </datalist>
                            <datalist id="version-suggestions">
                                {(suggestions['version'] || []).map(val => (
                                    <option key={val} value={val} />
                                ))}
                            </datalist>
                        </>
                    )}

                    {/* Document ID */}
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                            Document ID
                        </label>
                        <input
                            type="text"
                            value={metadata.doc_id}
                            onChange={(e) => handleChange('doc_id', e.target.value)}
                            placeholder="e.g., travel_reimburse"
                            disabled={disabled}
                            list="doc-id-suggestions"
                            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:border-slate-400"
                        />
                    </div>

                    {/* Document Type */}
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                            Document Type
                        </label>
                        <input
                            type="text"
                            value={metadata.doc_type}
                            onChange={(e) => handleChange('doc_type', e.target.value)}
                            placeholder="e.g., policy, standard, spec"
                            disabled={disabled}
                            list="doc-type-suggestions"
                            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:border-slate-400"
                        />
                    </div>

                    {/* Effective Date */}
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                            Effective Date
                        </label>
                        <input
                            type="date"
                            value={metadata.effective_date}
                            onChange={(e) => handleChange('effective_date', e.target.value)}
                            disabled={disabled}
                            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:border-slate-400"
                        />
                    </div>

                    {/* Version */}
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                            Version
                        </label>
                        <input
                            type="text"
                            value={metadata.version}
                            onChange={(e) => handleChange('version', e.target.value)}
                            placeholder="e.g., 1.0"
                            disabled={disabled}
                            list="version-suggestions"
                            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:border-slate-400"
                        />
                    </div>

                    {/* Keywords */}
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                            Keywords
                        </label>
                        <TagChipsInput
                            value={metadata.keywords}
                            onChange={(val) => handleChange('keywords', val)}
                            placeholder="e.g., hr, compensation (Press `Enter` to add)"
                            disabled={disabled}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
