import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from 'react';

const LG_BREAKPOINT = 1024;

interface SidebarContextValue {
    isOpen: boolean;
    isMobile: boolean;
    open: () => void;
    close: () => void;
    toggle: () => void;
}

const SidebarContext = createContext<SidebarContextValue | null>(null);

function useIsMobile(): boolean {
    const [isMobile, setIsMobile] = useState(
        () => typeof window !== 'undefined' && window.innerWidth < LG_BREAKPOINT,
    );

    useEffect(() => {
        const mq = window.matchMedia(`(max-width: ${LG_BREAKPOINT - 1}px)`);
        const onChange = () => setIsMobile(mq.matches);
        onChange();
        mq.addEventListener('change', onChange);
        return () => mq.removeEventListener('change', onChange);
    }, []);

    return isMobile;
}

export function SidebarProvider({ children }: { children: ReactNode }) {
    const isMobile = useIsMobile();
    const [isOpen, setIsOpen] = useState(() => !isMobile);

    useEffect(() => {
        setIsOpen(!isMobile);
    }, [isMobile]);

    const open = useCallback(() => setIsOpen(true), []);
    const close = useCallback(() => setIsOpen(false), []);
    const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

    const value = useMemo(
        () => ({ isOpen, isMobile, open, close, toggle }),
        [isOpen, isMobile, open, close, toggle],
    );

    return (
        <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>
    );
}

export function useSidebar(): SidebarContextValue {
    const ctx = useContext(SidebarContext);
    if (!ctx) {
        throw new Error('useSidebar must be used within SidebarProvider');
    }
    return ctx;
}
