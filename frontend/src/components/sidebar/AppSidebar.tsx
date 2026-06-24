import { Link, useLocation } from 'react-router-dom';
import { useAppDispatch } from '../../hooks/redux';
import { addConversation } from '../../store/conversation.slice';
import { openCreateModal } from '../../store/collection.slice';
import { ConversationList } from '../conversation/ConversationList';
import { CollectionList } from '../collection/CollectionList';
import { CreateModal } from '../collection/CreateModal';
import { useSidebar } from '../../context/SidebarContext';
import type { ConversationCreateRequest } from '../../types/conversations';
import {
    ChatIcon,
    FolderIcon,
    FolderPlusIcon,
    SparklesIcon,
} from '../../config/icons';

export function AppSidebar() {
    const dispatch = useAppDispatch();
    const location = useLocation();
    const { isMobile, close } = useSidebar();
    const isDocuments = location.pathname === '/documents';

    const handleNewChat = () => {
        const newConversationRequest: ConversationCreateRequest = {
            title: '',
        };
        dispatch(addConversation(newConversationRequest));
        if (isMobile) close();
    };

    const handleCreateCollection = () => {
        dispatch(openCreateModal());
        if (isMobile) close();
    };

    const navItems = [
        { path: '/chat', label: 'Chat', icon: ChatIcon },
        { path: '/documents', label: 'Documents', icon: FolderIcon },
    ];

    const onNavigate = isMobile ? close : undefined;

    const navItemClass =
        'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors';

    const ctaButtonClass = `${navItemClass} cursor-pointer text-[var(--color-text)] hover:bg-[var(--color-cta-hover)] hover:text-[var(--color-text)]`;

    return (
        <aside className="flex h-full w-[260px] shrink-0 flex-col border-r border-[var(--color-sidebar-border)] bg-[var(--color-sidebar-bg)] text-[var(--color-sidebar-text)]">
            <div className="px-2 pb-1 pt-3">
                {isDocuments ? (
                    <button
                        type="button"
                        onClick={handleCreateCollection}
                        className={ctaButtonClass}
                    >
                        <FolderPlusIcon className="h-5 w-5 shrink-0" />
                        Create collection
                    </button>
                ) : (
                    <button
                        type="button"
                        onClick={handleNewChat}
                        className={ctaButtonClass}
                    >
                        <SparklesIcon className="h-5 w-5 shrink-0" />
                        New conversation
                    </button>
                )}
            </div>

            <nav className="px-2 py-1">
                <ul className="space-y-0.5">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;
                        return (
                            <li key={item.path}>
                                <Link
                                    to={item.path}
                                    onClick={() => {
                                        if (isMobile) close();
                                    }}
                                    className={`${navItemClass} ${
                                        isActive
                                            ? 'bg-[var(--color-sidebar-active)] text-[var(--color-text)]'
                                            : 'text-[var(--color-sidebar-text-muted)] hover:bg-[var(--color-sidebar-hover)] hover:text-[var(--color-sidebar-text)]'
                                    }`}
                                >
                                    <Icon className="h-5 w-5 shrink-0" />
                                    {item.label}
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>

            <div className="mt-2 flex min-h-0 flex-1 flex-col overflow-hidden">
                <p className="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-sidebar-text-muted)]">
                    {isDocuments ? 'Collections' : 'Recents'}
                </p>
                {isDocuments ? (
                    <CollectionList onNavigate={onNavigate} />
                ) : (
                    <ConversationList onNavigate={onNavigate} />
                )}
            </div>

            {isDocuments && <CreateModal />}
        </aside>
    );
}
