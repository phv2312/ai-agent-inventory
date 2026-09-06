import { useEffect, useState } from 'react';
import { Header } from './Header';
import { MessageInput } from './MessageInput';
import { MessageList } from './MessageList';
import { EmptyChatState } from './EmptyChatState';
import { InterruptionDialog } from './InterruptionDialog';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import {
    clearPendingInterruption,
    fetchPendingInterruption,
} from '../../store/chat.slice';

export function Chat() {
    const dispatch = useAppDispatch();
    const { selectedConversationId } = useAppSelector((state) => state.conversation);
    const { messages, isStreaming, isLoadingMessages } = useAppSelector(
        (state) => state.chat,
    );
    const [inputText, setInputText] = useState('');

    useEffect(() => {
        setInputText('');
        if (selectedConversationId) {
            void dispatch(fetchPendingInterruption(selectedConversationId));
        } else {
            dispatch(clearPendingInterruption());
        }
    }, [dispatch, selectedConversationId]);

    const showEmpty =
        Boolean(selectedConversationId) &&
        !isLoadingMessages &&
        messages.length === 0 &&
        !isStreaming;

    return (
        <main className="flex min-w-0 flex-1 flex-col bg-app">
            <Header compact={!showEmpty} />
            {showEmpty ? (
                <EmptyChatState
                    inputText={inputText}
                    onInputTextChange={setInputText}
                />
            ) : (
                <>
                    <MessageList />
                    <MessageInput
                        variant="bottom"
                        text={inputText}
                        onTextChange={setInputText}
                    />
                </>
            )}
            <InterruptionDialog />
        </main>
    );
}
