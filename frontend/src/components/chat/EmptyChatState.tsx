import { getGreeting } from '../../utils/greeting';
import { MessageInput } from './MessageInput';
import { QuickPromptPills } from './QuickPromptPills';

interface Props {
    inputText: string;
    onInputTextChange: (value: string) => void;
}

export function EmptyChatState({ inputText, onInputTextChange }: Props) {
    return (
        <div className="flex flex-1 flex-col items-center justify-center px-4 pb-8">
            <h2 className="font-display mb-8 text-center text-3xl sm:text-4xl text-[var(--color-text)]">
                {getGreeting()}
            </h2>
            <div className="w-full max-w-2xl">
                <MessageInput
                    variant="centered"
                    text={inputText}
                    onTextChange={onInputTextChange}
                />
            </div>
            <div className="mt-4 w-full max-w-2xl">
                <QuickPromptPills onSelect={onInputTextChange} />
            </div>
        </div>
    );
}
