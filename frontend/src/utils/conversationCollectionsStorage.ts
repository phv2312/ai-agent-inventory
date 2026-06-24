const STORAGE_KEY = 'agent-ui:conversation-collections:v1';

export type ConversationCollectionsMap = Record<string, string[]>;

export function loadConversationCollections(): ConversationCollectionsMap {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return {};
        const parsed = JSON.parse(raw) as ConversationCollectionsMap;
        return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
        return {};
    }
}

export function saveConversationCollections(map: ConversationCollectionsMap): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
}

export function getCollectionIdsForConversation(conversationId: string): string[] {
    return loadConversationCollections()[conversationId] ?? [];
}

export function setCollectionIdsForConversation(
    conversationId: string,
    collectionIds: string[],
): void {
    const map = loadConversationCollections();
    map[conversationId] = collectionIds;
    saveConversationCollections(map);
}
