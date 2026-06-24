import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Chunk } from '../types/chunks';
import { getChunksByIds } from '../services/api/chunks';

export const fetchChunkByID = createAsyncThunk(
    'inspector/fetchChunkByID',
    async (
        payload: { chunkId: string; messageId: string },
        { rejectWithValue },
    ) => {
        try {
            const chunks = await getChunksByIds(
                [payload.chunkId],
                payload.messageId,
            );
            return chunks[0] ?? null;
        } catch (error) {
            return rejectWithValue(
                error instanceof Error ? error.message : 'Failed to fetch chunk',
            );
        }
    },
);

export interface InspectorState {
    isOpen: boolean;
    selectedChunk: Chunk | null;
    loading: boolean;
    error: string | null;
}

const initialState: InspectorState = {
    isOpen: false,
    selectedChunk: null,
    loading: false,
    error: null,
};

export const inspectorSlice = createSlice({
    name: 'inspector',
    initialState,
    reducers: {
        closeInspector(state) {
            state.isOpen = false;
            state.selectedChunk = null;
            state.loading = false;
            state.error = null;
        },
        setInspectorError(state, action: PayloadAction<string>) {
            state.error = action.payload;
            state.loading = false;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchChunkByID.pending, (state) => {
                state.loading = true;
                state.error = null;
                state.isOpen = true;
            })
            .addCase(fetchChunkByID.fulfilled, (state, action) => {
                state.loading = false;
                if (action.payload) {
                    state.selectedChunk = action.payload;
                } else {
                    state.error = 'Source not available';
                }
            })
            .addCase(fetchChunkByID.rejected, (state, action) => {
                state.loading = false;
                state.error = (action.payload as string) ?? 'Failed to load source';
            });
    },
});

export const { closeInspector, setInspectorError } = inspectorSlice.actions;

export default inspectorSlice.reducer;
