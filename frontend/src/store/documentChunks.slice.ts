import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';
import {
    getReferenceChunkDetail,
    getReferenceChunkPreviews,
} from '../services/api/reference';
import type { Reference } from '../types/references';
import type {
    ReferenceChunkDetail,
    ReferenceChunkPreview,
} from '../types/referenceChunks';

const PAGE_SIZE = 50;

export interface DocumentChunksState {
    reference: Reference | null;
    previews: ReferenceChunkPreview[];
    total: number;
    selectedChunkId: string | null;
    selectedChunk: ReferenceChunkDetail | null;
    isLoadingPreviews: boolean;
    isLoadingDetail: boolean;
    previewError: string | null;
    detailError: string | null;
}

const initialState: DocumentChunksState = {
    reference: null,
    previews: [],
    total: 0,
    selectedChunkId: null,
    selectedChunk: null,
    isLoadingPreviews: false,
    isLoadingDetail: false,
    previewError: null,
    detailError: null,
};

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : 'Unable to load document chunks.';
}

export const loadDocumentChunkPreviews = createAsyncThunk(
    'documentChunks/loadPreviews',
    async (
        { referenceId, offset }: { referenceId: string; offset: number },
        { rejectWithValue },
    ) => {
        try {
            return await getReferenceChunkPreviews(referenceId, offset, PAGE_SIZE);
        } catch (error) {
            return rejectWithValue(errorMessage(error));
        }
    },
);

export const loadDocumentChunkDetail = createAsyncThunk(
    'documentChunks/loadDetail',
    async (
        { referenceId, chunkId }: { referenceId: string; chunkId: string },
        { rejectWithValue },
    ) => {
        try {
            return await getReferenceChunkDetail(referenceId, chunkId);
        } catch (error) {
            return rejectWithValue(errorMessage(error));
        }
    },
);

export const documentChunksSlice = createSlice({
    name: 'documentChunks',
    initialState,
    reducers: {
        openDocumentChunks(state, action: PayloadAction<Reference>) {
            state.reference = action.payload;
            state.previews = [];
            state.total = 0;
            state.selectedChunkId = null;
            state.selectedChunk = null;
            state.previewError = null;
            state.detailError = null;
        },
        closeDocumentChunks: () => initialState,
        selectDocumentChunk(state, action: PayloadAction<string>) {
            state.selectedChunkId = action.payload;
            state.selectedChunk = null;
            state.detailError = null;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(loadDocumentChunkPreviews.pending, (state) => {
                state.isLoadingPreviews = true;
                state.previewError = null;
            })
            .addCase(loadDocumentChunkPreviews.fulfilled, (state, action) => {
                state.isLoadingPreviews = false;
                const offset = action.meta.arg.offset;
                if (offset === 0) {
                    state.previews = action.payload.items;
                } else {
                    state.previews.push(...action.payload.items);
                }
                state.total = action.payload.total;
            })
            .addCase(loadDocumentChunkPreviews.rejected, (state, action) => {
                state.isLoadingPreviews = false;
                state.previewError = String(action.payload ?? 'Unable to load chunks.');
            })
            .addCase(loadDocumentChunkDetail.pending, (state, action) => {
                state.isLoadingDetail = true;
                state.selectedChunkId = action.meta.arg.chunkId;
                state.selectedChunk = null;
                state.detailError = null;
            })
            .addCase(loadDocumentChunkDetail.fulfilled, (state, action) => {
                state.isLoadingDetail = false;
                if (state.selectedChunkId === action.payload.id) {
                    state.selectedChunk = action.payload;
                }
            })
            .addCase(loadDocumentChunkDetail.rejected, (state, action) => {
                state.isLoadingDetail = false;
                state.detailError = String(action.payload ?? 'Unable to load chunk.');
            });
    },
});

export const { closeDocumentChunks, openDocumentChunks, selectDocumentChunk } =
    documentChunksSlice.actions;

export default documentChunksSlice.reducer;
