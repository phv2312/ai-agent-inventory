import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import type { Collection, CollectionCreateRequest, CollectionId } from '../types/collections';
import {
    createCollection,
    listCollections
} from '../services/api/collection';


export const fetchCollections = createAsyncThunk(
    'collection/fetchCollections',
    async (_, { rejectWithValue }) => {
        try {
            const collections = await listCollections();
            return collections;
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch collections');
        }
    }
);


export const createNewCollection = createAsyncThunk(
    'collection/createNewCollection',
    async (payload: CollectionCreateRequest, { rejectWithValue }) => {
        try {
            const newCollection = await createCollection(payload);
            return newCollection;
        } catch (error) {
            return rejectWithValue(error instanceof Error ? error.message : 'Failed to create collection');
        }
    }
)


export interface CollectionState {
    collections: Collection[];
    selectedCollectionId: CollectionId | null;
    isLoading: boolean;
    error: string | null;
    isCreateModalOpen: boolean;
}

const initialState: CollectionState = {
    collections: [],
    selectedCollectionId: null,
    isLoading: false,
    error: null,
    isCreateModalOpen: false,
};

export const collectionSlice = createSlice({
    name: 'collection',
    initialState,
    reducers: {
        // Loading states
        setLoading(state, action: PayloadAction<boolean>) {
            state.isLoading = action.payload;
            if (action.payload) {
                state.error = null;
            }
        },

        setError(state, action: PayloadAction<string>) {
            state.error = action.payload;
            state.isLoading = false;
        },

        setCollectionID(state, action: PayloadAction<CollectionId>) {
            state.selectedCollectionId = action.payload;
        },

        // Collections CRUD
        setCollections(state, action: PayloadAction<Collection[]>) {
            state.collections = action.payload;
            state.isLoading = false;
            state.error = null;
        },

        updateCollection(state, action: PayloadAction<Collection>) {
            const index = state.collections.findIndex(
                col => col.id === action.payload.id
            );
            if (index !== -1) {
                state.collections[index] = action.payload;
            }
        },

        removeCollection(state, action: PayloadAction<CollectionId>) {
            state.collections = state.collections.filter(
                col => col.id !== action.payload
            );
            if (state.selectedCollectionId === action.payload) {
                state.selectedCollectionId = null;
            }
        },

        // Selection
        selectCollection(state, action: PayloadAction<CollectionId | null>) {
            state.selectedCollectionId = action.payload;
        },

        // UI state
        openCreateModal(state) {
            state.isCreateModalOpen = true;
        },

        closeCreateModal(state) {
            state.isCreateModalOpen = false;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchCollections.pending, (state) => {
                state.isLoading = true;
                state.error = null;
            })
            .addCase(fetchCollections.fulfilled, (state, action) => {
                state.isLoading = false;
                state.collections = action.payload;
                state.selectedCollectionId = action.payload.length > 0 ? action.payload[0].id : null;
                state.error = null;
            })
            .addCase(fetchCollections.rejected, (state, action) => {
                state.isLoading = false;
                state.error = action.payload as string;
            })
            .addCase(createNewCollection.fulfilled, (state, action) => {
                state.collections.push(action.payload);
                state.selectedCollectionId = action.payload.id;
            });
    }
});

export const {
    setLoading,
    setError,
    setCollections,
    updateCollection,
    removeCollection,
    selectCollection,
    setCollectionID,
    openCreateModal,
    closeCreateModal,
} = collectionSlice.actions;

export default collectionSlice.reducer;
