import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { selectConversation, deleteConversation } from '../../store/conversation.slice';
import { clearMessages, fetchMessagesByConversation } from '../../store/chat.slice';
import type { Conversation } from '../../types/conversations';
import { TrashIcon } from '../../config/icons';

interface Props {
    conversation: Conversation;
    onNavigate?: () => void;
}

export function ConversationItem({ conversation, onNavigate }: Props) {
    const dispatch = useAppDispatch();
    const selectedConversationId = useAppSelector(
        (state) => state.conversation.selectedConversationId,
    );
    const isSelected = selectedConversationId === conversation.id;
    const title = conversation.title || 'New Conversation';

    const handleClick = () => {
        dispatch(selectConversation(conversation.id));
        dispatch(clearMessages());
        void dispatch(fetchMessagesByConversation(conversation.id));
        onNavigate?.();
    };

    const handleDelete = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (confirm(`Are you sure you want to delete "${conversation.title}"?`)) {
            dispatch(deleteConversation(conversation.id));
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffDays = Math.floor(
            Math.abs(now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24),
        );
        if (diffDays === 0) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return date.toLocaleDateString([], { weekday: 'short' });
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    };

    return (
        <div
            className={`group relative mx-2 my-0.5 cursor-pointer rounded-lg px-3 py-2.5 transition-all duration-200 ${
                isSelected
                    ? 'bg-[var(--color-sidebar-active)]'
                    : 'hover:bg-[var(--color-sidebar-hover)]'
            }`}
            onClick={handleClick}
        >
            <div className="flex items-start justify-between gap-2 pr-6">
                <div className="min-w-0 flex-1">
                    <div
                        className={`truncate text-sm font-medium ${
                            isSelected
                                ? 'text-[var(--color-text)]'
                                : 'text-[var(--color-sidebar-text)]'
                        }`}
                        title={title}
                    >
                        {title}
                    </div>
                    <div className="mt-0.5 text-xs text-[var(--color-sidebar-text-muted)]">
                        {formatDate(conversation.updatedAt)}
                    </div>
                </div>
            </div>
            <button
                type="button"
                onClick={handleDelete}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-[var(--color-sidebar-text-muted)] opacity-0 transition-opacity hover:bg-red-950/50 hover:text-[var(--color-danger)] group-hover:opacity-100 cursor-pointer"
                title="Delete conversation"
            >
                <TrashIcon className="h-4 w-4" />
            </button>
        </div>
    );
}
