import { Outlet } from 'react-router-dom';
import { AppSidebar } from '../components/sidebar/AppSidebar';
import { SidebarProvider, useSidebar } from '../context/SidebarContext';

function MainLayoutContent() {
    const { isOpen, isMobile, close } = useSidebar();

    return (
        <div className="flex h-screen bg-app overflow-hidden">
            {isMobile && isOpen && (
                <button
                    type="button"
                    aria-label="Close sidebar"
                    className="fixed inset-0 z-40 bg-black/60 lg:hidden"
                    onClick={close}
                />
            )}

            <div
                className={`fixed inset-y-0 left-0 z-50 transition-transform duration-300 lg:static lg:translate-x-0 ${
                    isOpen ? 'translate-x-0' : '-translate-x-full'
                }`}
            >
                <AppSidebar />
            </div>

            <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
                <Outlet />
            </div>
        </div>
    );
}

export function MainLayout() {
    return (
        <SidebarProvider>
            <MainLayoutContent />
        </SidebarProvider>
    );
}
