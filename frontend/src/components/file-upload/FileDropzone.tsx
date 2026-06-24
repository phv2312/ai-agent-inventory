import { useCallback } from "react";
import { useDropzone, type DropzoneOptions } from "react-dropzone";

interface FileDropzoneProps {
    onDrop: (acceptedFiles: File[]) => void;
    multiple?: boolean;
    accept?: Record<string, string[]>;
    disabled?: boolean;
    className?: string;
    children?: React.ReactNode;
    variant?: 'default' | 'compact';
}

const DEFAULT_ACCEPT = {
    'application/pdf': ['.pdf'],
    'text/plain': ['.txt'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'text/csv': ['.csv'],
    'application/json': ['.json'],
    'text/markdown': ['.md'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
};

export function FileDropzone({
    onDrop,
    multiple = true,
    accept = DEFAULT_ACCEPT,
    disabled = false,
    className = '',
    children,
    variant = 'default'
}: FileDropzoneProps) {
    const handleDrop = useCallback((acceptedFiles: File[]) => {
        onDrop(acceptedFiles);
    }, [onDrop]);

    const dropzoneOptions: DropzoneOptions = {
        onDrop: handleDrop,
        multiple,
        accept,
        disabled
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone(dropzoneOptions);

    const baseClasses = `transition-colors cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`;

    const variantClasses = {
        default: `border-2 border-dashed rounded-lg p-8 text-center ${
            isDragActive
                ? 'border-blue-400 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
        }`,
        compact: `p-1 rounded ${
            isDragActive
                ? 'bg-blue-50'
                : 'hover:bg-gray-100'
        }`
    };

    const finalClassName = `${baseClasses} ${variantClasses[variant]} ${className}`;

    if (variant === 'compact') {
        return (
            <div {...getRootProps()} className={finalClassName}>
                <input {...getInputProps()} />
                {children}
            </div>
        );
    }

    return (
        <div {...getRootProps()} className={finalClassName}>
            <input {...getInputProps()} />
            {children || (
                <div className="space-y-2">
                    <div className="text-4xl">📄</div>
                    <div>
                        <p className="text-sm font-medium text-gray-900">
                            {isDragActive
                                ? "Drop the files here..."
                                : "Drop files here or click to browse"
                            }
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                            Supports PDF, DOC, TXT, CSV, JSON, images and more
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
