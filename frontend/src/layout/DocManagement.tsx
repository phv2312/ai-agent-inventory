import { useSidebar } from '../context/SidebarContext';
import { Reference } from '../components/reference';

export function DocManagementLayout() {
    const { isMobile, toggle } = useSidebar();

    return (
        <div className="flex h-full flex-col bg-app">
            {isMobile && (
                <div className="flex shrink-0 items-center border-b border-app px-3 py-2 lg:hidden">
                    <button
                        type="button"
                        onClick={toggle}
                        aria-label="Toggle sidebar"
                        className="cursor-pointer rounded-lg p-2 text-[var(--color-text-muted)] hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text)]"
                    >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                        </svg>
                    </button>
                    <span className="ml-2 text-sm font-medium text-[var(--color-text)]">Documents</span>
                </div>
            )}
            <div className="min-h-0 flex-1">
                <Reference />
            </div>
        </div>
    );
}
