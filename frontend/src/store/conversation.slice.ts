import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { Conversation, ConversationUpdateRequest, ConversationCreateRequest, ConversationId } from "../types/conversations";
import {
    createConversation as createConversationAPI,
    listConversations as listConversationsAPI,
    updateConversation as updateConversationAPI,
    deleteConversation as deleteConversationAPI,
} from "../services/api/conversation";


export const addConversation = createAsyncThunk(
    "conversation/addConversation",
    async (payload: ConversationCreateRequest, { rejectWithValue }) => {
        try {
            const newConversation = await createConversationAPI(payload);
            return newConversation;
        } catch (error) {
            return rejectWithValue(
                error instanceof Error ? error.message : "Failed to create conversation"
            );
        }
    }
);


export const fetchConversations = createAsyncThunk(
    "conversation/fetchConversations",
    async (_, { rejectWithValue }) => {
        try {
            const conversations = await listConversationsAPI();
            return conversations;
        } catch (error) {
            return rejectWithValue(
                error instanceof Error ? error.message : "Failed to fetch conversations"
            );
        }
    }
);

export const updateConversation = createAsyncThunk(
    "conversation/updateExistedConversation",
    async (payload: ConversationUpdateRequest, { rejectWithValue }) => {
        try {
            const updatedConversation = await updateConversationAPI(payload);
            return updatedConversation;
        } catch (error) {
            return rejectWithValue(
                error instanceof Error ? error.message : "Failed to update conversation"
            );
        }
    }
);

export const deleteConversation = createAsyncThunk(
    "conversation/deleteConversation",
    async (id: ConversationId, { rejectWithValue }) => {
        try {
            await deleteConversationAPI(id);
            return id;
        } catch (error) {
            return rejectWithValue(
                error instanceof Error ? error.message : "Failed to delete conversation"
            );
        }
    }
);


interface ConversationState {
    conversations: Conversation[];
    selectedConversationId: ConversationId | null;
}


const initialState: ConversationState = {
    conversations: [],
    selectedConversationId: null,
};


export const conversationSlice = createSlice({
    name: "conversation",
    initialState,
    reducers: {
        setConversations(state, action: PayloadAction<Conversation>) {
            const index = state.conversations.findIndex(
                conv => conv.id === action.payload.id
            );
            if (index !== -1) {
                state.conversations[index] = action.payload;
            }
        },
        selectConversation(state, action) {
            state.selectedConversationId = action.payload;
        },
        deselectConversation(state) {
            state.selectedConversationId = null;
        },
        clearConversations(state) {
            state.conversations = [];
            state.selectedConversationId = null;
        },
        patchConversationTitle(
            state,
            action: PayloadAction<{ id: ConversationId; title: string }>,
        ) {
            const index = state.conversations.findIndex(
                (conv) => conv.id === action.payload.id,
            );
            if (index !== -1) {
                state.conversations[index].title = action.payload.title;
            }
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(addConversation.fulfilled, (state, action) => {
                state.conversations.push(action.payload);
                state.selectedConversationId = action.payload.id;
            })
            .addCase(fetchConversations.fulfilled, (state, action) => {
                state.conversations = action.payload;
            })
            .addCase(updateConversation.fulfilled, (state, action) => {
                const index = state.conversations.findIndex(
                    conv => conv.id === action.payload.id
                );
                if (index !== -1) {
                    state.conversations[index] = action.payload;
                }
            })
            .addCase(deleteConversation.fulfilled, (state, action) => {
                state.conversations = state.conversations.filter(
                    conv => conv.id !== action.payload
                );
                // If the deleted conversation was selected, clear selection
                if (state.selectedConversationId === action.payload) {
                    state.selectedConversationId = null;
                }
            });
    }
});

export const {
    setConversations,
    selectConversation,
    deselectConversation,
    clearConversations,
    patchConversationTitle,
} = conversationSlice.actions;

export default conversationSlice.reducer;
