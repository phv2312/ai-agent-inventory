export type AttachmentId = string;

export interface Attachment {
    id: AttachmentId;
    name: string;
    contentType: string;
    size: number;
    uri: string;
    extension: string;
}

export interface AttachmentUploadRequest {
    file: File;
}
