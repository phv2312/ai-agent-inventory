import { createSlice, type PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import type { Collection } from '../types/collections';
import type { Reference } from '../types/references';
import { getReferencesByCollections } from '../services/api/collection';
import {
    getCollectionIdsForConversation,
    setCollectionIdsForConversation,
} from '../utils/conversationCollectionsStorage';

interface ConversationSelectionState {
    collections: Collection[];
    references: Reference[];
}

interface ChatCollectionManagerState {
    byConversationId: Record<string, ConversationSelectionState>;
}

const initialState: ChatCollectionManagerState = {
    byConversationId: {},
};

export const fetchReferencesByCollections = createAsyncThunk<
    { conversationId: string; references: Reference[] },
    { conversationId: string; collectionIds: string[] }
>(
    'chatCollectionManager/fetchReferencesByCollections',
    async ({ conversationId, collectionIds }, { rejectWithValue }) => {
        try {
            const references = collectionIds.length
                ? await getReferencesByCollections(collectionIds)
                : [];
            return { conversationId, references };
        } catch (error) {
            return rejectWithValue(
                error instanceof Error ? error.message : 'Failed to fetch references',
            );
        }
    },
);

function persistCollectionIds(conversationId: string, collections: Collection[]): void {
    setCollectionIdsForConversation(
        conversationId,
        collections.map((c) => c.id),
    );
}

export const chatCollectionManagerSlice = createSlice({
    name: 'chatCollectionManager',
    initialState,
    reducers: {
        hydrateConversationCollections(
            state,
            action: PayloadAction<{ conversationId: string; allCollections: Collection[] }>,
        ) {
            const { conversationId, allCollections } = action.payload;
            const ids = getCollectionIdsForConversation(conversationId);
            const collections = allCollections.filter((c) => ids.includes(c.id));
            const existing = state.byConversationId[conversationId] ?? {
                collections: [],
                references: [],
            };
            state.byConversationId[conversationId] = { ...existing, collections };
        },
        toggleCollectionForConversation(
            state,
            action: PayloadAction<{ conversationId: string; collection: Collection }>,
        ) {
            const { conversationId, collection } = action.payload;
            const existing = state.byConversationId[conversationId] ?? {
                collections: [],
                references: [],
            };
            const exists = existing.collections.some((c) => c.id === collection.id);
            const collections = exists
                ? existing.collections.filter((c) => c.id !== collection.id)
                : [...existing.collections, collection];
            state.byConversationId[conversationId] = { ...existing, collections };
            persistCollectionIds(conversationId, collections);
        },
        setCollectionsForConversation(
            state,
            action: PayloadAction<{ conversationId: string; collections: Collection[] }>,
        ) {
            const { conversationId, collections } = action.payload;
            const existing = state.byConversationId[conversationId] ?? {
                collections: [],
                references: [],
            };
            state.byConversationId[conversationId] = { ...existing, collections };
            persistCollectionIds(conversationId, collections);
        },
        clearCollectionsForConversation(
            state,
            action: PayloadAction<{ conversationId: string }>,
        ) {
            const { conversationId } = action.payload;
            const existing = state.byConversationId[conversationId] ?? {
                collections: [],
                references: [],
            };
            state.byConversationId[conversationId] = { ...existing, collections: [] };
            persistCollectionIds(conversationId, []);
        },
    },
    extraReducers: (builder) => {
        builder.addCase(fetchReferencesByCollections.fulfilled, (state, action) => {
            const { conversationId, references } = action.payload;
            const existing = state.byConversationId[conversationId] ?? {
                collections: [],
                references: [],
            };
            state.byConversationId[conversationId] = { ...existing, references };
        });
    },
});

export const {
    hydrateConversationCollections,
    toggleCollectionForConversation,
    setCollectionsForConversation,
    clearCollectionsForConversation,
} = chatCollectionManagerSlice.actions;

export default chatCollectionManagerSlice.reducer;
