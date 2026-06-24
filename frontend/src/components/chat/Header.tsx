import { useState } from 'react';
import { CollectionManager } from './CollectionManager';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { fetchReferencesByCollections } from '../../store/chat.collection.slice';
import { useConversationSelections } from '../../hooks/useConversationSelections';
import { useSidebar } from '../../context/SidebarContext';
import { FolderIcon, ArrowPathIcon } from '../../config/icons';

interface HeaderProps {
    compact?: boolean;
}

export function Header({ compact = false }: HeaderProps) {
    const dispatch = useAppDispatch();
    const { isMobile, toggle } = useSidebar();
    const { selectedConversationId, conversations } = useAppSelector(
        (state) => state.conversation,
    );
    const { collections: selectedCollections } =
        useConversationSelections(selectedConversationId);
    const [isOpenCollectionManager, setIsOpenCollectionManager] = useState(false);

    const selectedConversation = conversations.find(
        (conv) => conv.id === selectedConversationId,
    );
    const title = selectedConversation
        ? selectedConversation.title || 'New Conversation'
        : 'Select a conversation to get started';

    const isManageButtonDisabled = !selectedConversationId;
    const isRefreshButtonDisabled =
        !selectedConversationId || selectedCollections.length === 0;

    const handleRefresh = () => {
        if (selectedConversationId && selectedCollections.length > 0) {
            dispatch(
                fetchReferencesByCollections({
                    conversationId: selectedConversationId,
                    collectionIds: selectedCollections.map((c) => c.id),
                }),
            );
        }
    };

    return (
        <>
            <header
                className={`shrink-0 bg-app ${compact ? 'py-2.5' : 'border-b border-app py-3'}`}
            >
                <div className="flex w-full items-center justify-between gap-4 px-4 sm:px-6">
                    <div className="flex min-w-0 items-center gap-2">
                        {isMobile && (
                            <button
                                type="button"
                                onClick={toggle}
                                aria-label="Toggle sidebar"
                                className="shrink-0 cursor-pointer rounded-lg p-2 text-[var(--color-text-muted)] hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text)] lg:hidden"
                            >
                                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                                </svg>
                            </button>
                        )}
                        <button
                            type="button"
                            className="flex min-w-0 items-center gap-1 rounded-sm py-1 px-2 text-left hover:bg-[var(--color-surface-elevated)]"
                            title={title}
                        >
                            <h1 className="truncate text-sm font-medium text-[var(--color-text)]">
                                {title}
                            </h1>
                        </button>
                    </div>

                    <div className="flex shrink-0 items-center gap-1">
                        <button
                            type="button"
                            onClick={handleRefresh}
                            disabled={isRefreshButtonDisabled}
                            className={`rounded-lg p-2 transition-all duration-200 ${
                                isRefreshButtonDisabled
                                    ? 'cursor-not-allowed text-[var(--color-text-faint)]'
                                    : 'cursor-pointer text-muted hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text)]'
                            }`}
                            title="Refresh references for selected collections"
                        >
                            <ArrowPathIcon className="h-4 w-4" />
                        </button>

                        <button
                            type="button"
                            onClick={() => setIsOpenCollectionManager(true)}
                            disabled={isManageButtonDisabled}
                            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm transition-all duration-200 ${
                                isManageButtonDisabled
                                    ? 'cursor-not-allowed text-[var(--color-text-faint)]'
                                    : 'cursor-pointer text-muted hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text)]'
                            }`}
                            title="Manage collections for this conversation"
                        >
                            <FolderIcon className="h-4 w-4" />
                            {!compact && (
                                <span className="hidden sm:inline">Collections</span>
                            )}
                        </button>
                    </div>
                </div>
            </header>

            <CollectionManager
                isOpen={isOpenCollectionManager}
                onClose={() => setIsOpenCollectionManager(false)}
            />
        </>
    );
}
