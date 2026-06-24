import { ExclamationCircleIcon, XCircleIcon } from '../../config/icons';

interface Props {
    error: string | null;
    onClose: () => void;
}

export function ErrorBanner({ error, onClose }: Props) {
    if (!error) return null;

    return (
        <div className="bg-red-50 border border-red-200 rounded-sm p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
                <div className="flex-shrink-0">
                    <ExclamationCircleIcon className="w-5 h-5 text-red-400" />
                </div>
                <div>
                    <h3 className="text-sm font-medium text-red-800">
                        Streaming Error
                    </h3>
                    <p className="text-sm text-red-700 mt-1">
                        {error}
                    </p>
                </div>
            </div>
            <button
                onClick={onClose}
                className="flex-shrink-0 text-red-400 hover:text-red-600 transition-colors"
            >
                <span className="sr-only">Dismiss</span>
                <XCircleIcon className="w-5 h-5" />
            </button>
        </div>
    );
}
