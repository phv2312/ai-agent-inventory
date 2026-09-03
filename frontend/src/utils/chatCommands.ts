const GLOBAL_QUERY_PREFIX = /^\/global(?:\s+|$)/i;

export interface ParsedChatCommand {
    message: string;
    globalQuery: boolean;
}

export function parseChatCommand(input: string): ParsedChatCommand {
    const trimmed = input.trim();
    if (!GLOBAL_QUERY_PREFIX.test(trimmed)) {
        return { message: trimmed, globalQuery: false };
    }
    return {
        message: trimmed.replace(GLOBAL_QUERY_PREFIX, '').trim(),
        globalQuery: true,
    };
}
