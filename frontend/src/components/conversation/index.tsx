import { useAppDispatch } from '../../hooks/redux';
import { addConversation } from '../../store/conversation.slice';
import { ConversationList } from './ConversationList';
import { type ConversationCreateRequest } from '../../types/conversations';
import { PlusIcon, ChatBubbleLeftRightIcon } from '../../config/icons';

export function Sidebar() {
    const dispatch = useAppDispatch();

    const handleNewChat = () => {
        const newConversationRequest: ConversationCreateRequest = {
            title: '',
        };
        dispatch(addConversation(newConversationRequest));
    };

    return (
        <aside className="w-64 bg-white flex flex-col border-r border-slate-200">
            <div className="p-4 border-slate-200">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <ChatBubbleLeftRightIcon className="w-5 h-5 shrink-0 text-slate-600" />
                        <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                            Conversations
                        </span>
                    </div>
                    <button
                        type="button"
                        title="New conversation"
                        aria-label="New conversation"
                        className="shrink-0 flex items-center justify-center rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 hover:text-blue-600 transition-colors cursor-pointer"
                        onClick={handleNewChat}
                    >
                        <PlusIcon className="w-5 h-5" />
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto">
                <p className="px-4 py-2 text-xs font-semibold text-slate-500">Recents</p>
                <ConversationList />
            </div>

            <div className="p-3 border-t border-slate-200">
                <div className="text-xs text-slate-500 text-center">Agent Chat</div>
            </div>
        </aside>
    );
}
