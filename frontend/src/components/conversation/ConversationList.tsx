import { useAppSelector } from '../../hooks/redux';
import { ConversationItem } from './ConversationItem';

interface Props {
    onNavigate?: () => void;
}

export function ConversationList({ onNavigate }: Props) {
    const conversations = useAppSelector((state) => state.conversation.conversations);

    const sortedConversations = [...conversations].sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
    );

    return (
        <div className="flex-1 overflow-y-auto pb-2">
            {sortedConversations.map((conv) => (
                <ConversationItem
                    key={conv.id}
                    conversation={conv}
                    onNavigate={onNavigate}
                />
            ))}
        </div>
    );
}
