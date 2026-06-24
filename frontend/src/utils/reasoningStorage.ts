const KEY_PREFIX = 'agent-chat-reasoning:';

export function saveMessageReasoning(messageId: string, reasoning: string): void {
    try {
        if (reasoning.trim()) {
            sessionStorage.setItem(`${KEY_PREFIX}${messageId}`, reasoning);
        } else {
            sessionStorage.removeItem(`${KEY_PREFIX}${messageId}`);
        }
    } catch {
        // sessionStorage unavailable or full
    }
}

export function loadMessageReasoning(messageId: string): string | null {
    try {
        return sessionStorage.getItem(`${KEY_PREFIX}${messageId}`);
    } catch {
        return null;
    }
}
