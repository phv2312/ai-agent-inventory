import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import type { Reference, ReferenceId } from '../types/references';
import { getReferencesByCollection } from '../services/api/collection';

export const fetchReferencesByCollection = createAsyncThunk(
    'reference/fetchReferencesByCollection',
    async (collectionId: string, { rejectWithValue }) => {
        try {
            return await getReferencesByCollection(collectionId);
        } catch (error) {
            return rejectWithValue(
                error instanceof Error ? error.message : 'Failed to fetch references',
            );
        }
    },
);

export interface ReferenceState {
    references: Reference[];
    selectedReferenceId: ReferenceId | null;
}

const initialState: ReferenceState = {
    references: [],
    selectedReferenceId: null,
};

export const referenceSlice = createSlice({
    name: 'reference',
    initialState,
    reducers: {
        setReferences(state, action: PayloadAction<Reference[]>) {
            state.references = action.payload;
        },
        addReference(state, action: PayloadAction<Reference>) {
            state.references.unshift(action.payload);
        },
        removeReference(state, action: PayloadAction<ReferenceId>) {
            state.references = state.references.filter(
                (reference) => reference.id !== action.payload,
            );
            if (state.selectedReferenceId === action.payload) {
                state.selectedReferenceId = null;
            }
        },
        selectReference(state, action: PayloadAction<ReferenceId | null>) {
            state.selectedReferenceId = action.payload;
        },
    },
    extraReducers: (builder) => {
        builder.addCase(fetchReferencesByCollection.fulfilled, (state, action) => {
            state.references = action.payload;
        });
    },
});

export const { setReferences, addReference, removeReference, selectReference } =
    referenceSlice.actions;

export default referenceSlice.reducer;
