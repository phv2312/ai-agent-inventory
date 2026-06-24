import { Chat } from '../components/chat';
import { Inspector } from '../components/inspector';

export function ChatLayout() {
    return (
        <div className="flex h-full bg-app">
            <Chat />
            <Inspector />
        </div>
    );
}
