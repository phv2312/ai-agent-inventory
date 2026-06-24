import { useEffect, useState } from 'react';
import { Header } from './Header';
import { MessageInput } from './MessageInput';
import { MessageList } from './MessageList';
import { EmptyChatState } from './EmptyChatState';
import { useAppSelector } from '../../hooks/redux';

export function Chat() {
    const { selectedConversationId } = useAppSelector((state) => state.conversation);
    const { messages, isStreaming, isLoadingMessages } = useAppSelector(
        (state) => state.chat,
    );
    const [inputText, setInputText] = useState('');

    useEffect(() => {
        setInputText('');
    }, [selectedConversationId]);

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
        </main>
    );
}
