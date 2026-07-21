import { useState, useCallback } from "react";
import { FileDropzone } from "./FileDropzone";


interface Props {
    isOpen: boolean;
    onClose: () => void;
    onUpload: (files: File[]) => Promise<void>;

    uploadProgress: Record<string, number>; // filename -> progress percentage
}


interface FileItemProps {
    file: File;
    index: number;
    progress?: number;
    onRemove: (index: number) => void;
    isLoading: boolean;
}


function FileItem({ file, index, progress, onRemove, isLoading }: FileItemProps) {
    const formatFileSize = (bytes: number) => {
        return (bytes / 1024).toFixed(1) + ' KB';
    };

    return (
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
                <div className="text-sm">📄</div>
                <div>
                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">
                        {formatFileSize(file.size)} • {file.type || 'Unknown type'}
                    </p>
                </div>
            </div>

            {progress !== undefined ? (
                <ProgressBar progress={progress} />
            ) : (
                <RemoveButton onRemove={() => onRemove(index)} disabled={isLoading} />
            )}
        </div>
    );
}

function ProgressBar({ progress }: { progress: number }) {
    return (
        <div className="flex items-center space-x-2">
            <div className="w-20 bg-gray-200 rounded-full h-2">
                <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-200"
                    style={{ width: `${progress}%` }}
                />
            </div>
            <span className="text-xs text-gray-500">
                {Math.round(progress)}%
            </span>
        </div>
    );
}

function RemoveButton({ onRemove, disabled }: { onRemove: () => void; disabled: boolean }) {
    return (
        <button
            onClick={onRemove}
            className="text-gray-400 hover:text-red-500 text-sm"
            disabled={disabled}
        >
            ✕
        </button>
    );
}

function FileList({ files, uploadProgress, onRemoveFile, isLoading }: {
    files: File[];
    uploadProgress: Record<string, number>;
    onRemoveFile: (index: number) => void;
    isLoading: boolean;
}) {
    if (files.length === 0) return null;

    return (
        <div className="space-y-2 mb-4">
            <h3 className="text-sm font-medium text-gray-900">
                Selected Files ({files.length})
            </h3>
            <div className="space-y-2 max-h-40 overflow-y-auto">
                {files.map((file, index) => (
                    <FileItem
                        key={`${file.name}-${index}`}
                        file={file}
                        index={index}
                        progress={uploadProgress[file.name]}
                        onRemove={onRemoveFile}
                        isLoading={isLoading}
                    />
                ))}
            </div>
        </div>
    );
}

export function UploadFilesModal({
    isOpen,
    onClose,
    onUpload,
    uploadProgress
}: Props) {
    const [ selectedFiles, setSelectedFiles ] = useState<File[]>([]);
    const [ isLoading, setLoading ] = useState(false);
    const [ error, setError ] = useState<string | null>(null);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        setSelectedFiles(prev => [...prev, ...acceptedFiles]);
    }, []);

    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleUpload = async () => {
        if (selectedFiles.length === 0) return;
        try {
            setLoading(true);

            await onUpload(selectedFiles);

            // Reset form
            setSelectedFiles([]);
            onClose();
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Failed to upload files";
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        if (!isLoading) {
            setSelectedFiles([]);
            onClose();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="mx-4 max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-lg bg-surface shadow-xl">
                <div className="border-b border-app px-6 py-4">
                    <h2 className="text-lg font-semibold text-[var(--color-text)]">Upload Files</h2>
                    <p className="mt-1 text-sm text-muted">
                        Select files to upload and index for your knowledge base
                    </p>
                </div>

                {error && (
                    <div className="border-b border-[var(--color-danger)]/30 bg-red-950/30 px-6 py-3">
                        <p className="text-sm text-[var(--color-danger)]">{error}</p>
                    </div>
                )}

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
                    {/* File Drop Zone using the reusable component */}
                    <FileDropzone
                        onDrop={onDrop}
                        multiple={true}
                        disabled={isLoading}
                        className="mb-4"
                        variant="default"
                    />

                    {/* Selected Files List */}
                    <FileList
                        files={selectedFiles}
                        uploadProgress={uploadProgress}
                        onRemoveFile={removeFile}
                        isLoading={isLoading}
                    />
                </div>

                {/* Actions */}
                <div className="flex justify-end space-x-3 border-t border-app bg-[var(--color-surface-elevated)] px-6 py-4">
                    <button
                        type="button"
                        onClick={handleClose}
                        className="rounded-lg border border-app bg-surface px-4 py-2 text-sm font-medium text-[var(--color-text)] transition-colors hover:bg-[var(--color-sidebar-hover)]"
                        disabled={isLoading}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleUpload}
                        disabled={selectedFiles.length === 0 || isLoading}
                        className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-primary-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isLoading ? 'Uploading...' : `Upload ${selectedFiles.length} File${selectedFiles.length !== 1 ? 's' : ''}`}
                    </button>
                </div>
            </div>
        </div>
    );
}
