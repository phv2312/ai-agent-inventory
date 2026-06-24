import { useState } from "react";
import { UploadFilesModal } from "../../file-upload/FileModal";


interface Props {
    isOpen: boolean;
    onClose: () => void;
    onFilesAdded: (files: File[]) => void;
}

export const UploadStep = {
    Uploading: "Uploading",
    Done: "Done",
} as const;


export type UploadStep =
    typeof UploadStep[keyof typeof UploadStep];


const MP_UPLOAD_PROGRESS: Record<UploadStep, number> = {
    Uploading: 10,
    Done: 100,
};


export function AttachmentsUploadFilesModal({ isOpen, onClose, onFilesAdded }: Props) {
    const [ uploadProgress, setUploadProgress ] = useState<{ [filename: string]: number }>({});

    const handleSingleUpload = async (file: File) => {
        setUploadProgress(prev => ({
            ...prev,
            [file.name]: MP_UPLOAD_PROGRESS[UploadStep.Uploading]
        }));

        // pass file to parent local state
        onFilesAdded([file]);

        setUploadProgress(prev => ({
            ...prev,
            [file.name]: MP_UPLOAD_PROGRESS[UploadStep.Done]
        }));
    }

    const handleUpload = async (files: File[]) => {
        await Promise.all(
            files.map(file => handleSingleUpload(file))
        );
    };

    const handleOnClose = () => {
        setUploadProgress({});
        onClose();
    }

    return (
        <UploadFilesModal
            isOpen={isOpen}
            onClose={handleOnClose}
            onUpload={handleUpload}
            uploadProgress={uploadProgress}
        />
    );
}
