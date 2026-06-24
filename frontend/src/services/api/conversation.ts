import type { Conversation, ConversationCreateRequest, ConversationUpdateRequest } from '../../types/conversations';
import { apiFetch } from './client';

const API = '/api/v1';

export async function createConversation(
    payload: ConversationCreateRequest,
): Promise<Conversation> {
    return apiFetch(`${API}/conversations/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: payload.title ?? '' }),
    });
}

export async function listConversations(): Promise<Conversation[]> {
    return apiFetch(`${API}/conversations/`);
}

export async function getConversation(id: string): Promise<Conversation> {
    return apiFetch(`${API}/conversations/${id}`);
}

export async function updateConversation(
    payload: ConversationUpdateRequest,
): Promise<Conversation> {
    return apiFetch(`${API}/conversations/${payload.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: payload.title ?? '' }),
    });
}

export async function deleteConversation(id: string): Promise<void> {
    await apiFetch(`${API}/conversations/${id}`, { method: 'DELETE' });
}

export async function getMessagesByConversation(id: string) {
    return apiFetch<import('../../types/messages').ApiMessage[]>(
        `${API}/conversations/${id}/messages`,
    );
}
