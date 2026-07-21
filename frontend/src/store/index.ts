import { configureStore } from '@reduxjs/toolkit';
import ChatReducer from './chat.slice';
import InspectorReducer from './inspector.slice';
import CollectionReducer from './collection.slice';
import ReferenceReducer from './reference.slice';
import ConversationReducer from './conversation.slice';
import ChatCollectionManageReducer from './chat.collection.slice';
import DocumentChunksReducer from './documentChunks.slice';

export const store = configureStore({
    reducer: {
        chat: ChatReducer,
        chatCollectionManager: ChatCollectionManageReducer,
        conversation: ConversationReducer,
        collection: CollectionReducer,
        inspector: InspectorReducer,
        reference: ReferenceReducer,
        documentChunks: DocumentChunksReducer,
    },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export type AppStore = typeof store;
