import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { addReference, fetchReferencesByCollection } from '../../store/reference.slice';
import { uploadReference } from '../../services/api/reference';
import { UploadFilesModal } from '../file-upload/FileModal';
import { useState } from 'react';

interface Props {
    isOpen: boolean;
    onClose: () => void;
}

export function ReferenceUploadFilesModal({ isOpen, onClose }: Props) {
    const dispatch = useAppDispatch();
    const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
    const selectedCollectionId = useAppSelector(
        (state) => state.collection.selectedCollectionId,
    );

    const handleUpload = async (files: File[]) => {
        if (!selectedCollectionId) return;

        for (const file of files) {
            setUploadProgress((prev) => ({ ...prev, [file.name]: 30 }));
            try {
                const ref = await uploadReference(file, selectedCollectionId);
                dispatch(addReference(ref));
                setUploadProgress((prev) => ({ ...prev, [file.name]: 100 }));
            } catch (err) {
                console.error(err);
                setUploadProgress((prev) => ({ ...prev, [file.name]: -1 }));
            }
        }

        dispatch(fetchReferencesByCollection(selectedCollectionId));
    };

    return (
        <UploadFilesModal
            isOpen={isOpen}
            onClose={onClose}
            onUpload={handleUpload}
            uploadProgress={uploadProgress}
        />
    );
}
