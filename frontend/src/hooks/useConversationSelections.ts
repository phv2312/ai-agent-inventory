import { useEffect, useMemo } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import type { Collection } from '../types/collections';
import type { Reference } from '../types/references';
import {
    fetchReferencesByCollections,
    hydrateConversationCollections,
} from '../store/chat.collection.slice';

const EMPTY_COLLECTIONS: Collection[] = [];
const EMPTY_REFERENCES: Reference[] = [];

export function useConversationSelections(conversationId: string | null) {
    const dispatch = useAppDispatch();
    const allCollections = useAppSelector((state) => state.collection.collections);
    const { collections, references } = useAppSelector((state) => {
        if (!conversationId) {
            return { collections: EMPTY_COLLECTIONS, references: EMPTY_REFERENCES };
        }
        const conversationState =
            state.chatCollectionManager.byConversationId[conversationId];
        return {
            collections: conversationState?.collections ?? EMPTY_COLLECTIONS,
            references: conversationState?.references ?? EMPTY_REFERENCES,
        };
    });

    useEffect(() => {
        if (conversationId && allCollections.length > 0) {
            dispatch(
                hydrateConversationCollections({
                    conversationId,
                    allCollections,
                }),
            );
        }
    }, [conversationId, allCollections, dispatch]);

    useEffect(() => {
        if (conversationId && collections.length > 0) {
            dispatch(
                fetchReferencesByCollections({
                    conversationId,
                    collectionIds: collections.map((c) => c.id),
                }),
            );
        }
    }, [conversationId, collections, dispatch]);

    return useMemo(() => ({ collections, references }), [collections, references]);
}
