import { Link, useLocation } from 'react-router-dom';
import logoUrl from '../../assets/logo.png';
import { FolderIcon, ChatBubbleLeftRightIcon } from '../../config/icons';


export function Navigation() {
    const location = useLocation();

    const navItems = [
        {
            path: '/chat',
            label: 'Chat',
            icon: ChatBubbleLeftRightIcon
        },
        {
            path: '/documents',
            label: 'Documents',
            icon: FolderIcon
        }
    ];

    return (
        <div className="bg-slate-900 text-white w-14 flex flex-col border-r border-slate-700/50">
            {/* Logo */}
            <div className="p-2 border-b border-slate-700/50 flex justify-center py-3">
                <div className="w-10 h-10 rounded-full bg-white overflow-hidden shadow-lg shadow-blue-900/50">
                    <img src={logoUrl} alt="App Logo" className="w-full h-full object-cover" />
                </div>
            </div>

            {/* Navigation Items */}
            <nav className="flex-1 p-2">
                <ul className="space-y-1">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;

                        return (
                            <li key={item.path}>
                                <Link
                                    to={item.path}
                                    className={`flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-200 cursor-pointer ${isActive
                                            ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/25'
                                            : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                                        }`}
                                    title={item.label}
                                >
                                    <Icon className="w-5 h-5" />
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>

            {/* Bottom spacer */}
            <div className="p-2 border-t border-slate-700/50">
                <div className="w-10 h-10 rounded-lg bg-slate-800/50 flex items-center justify-center">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-slate-600 to-slate-700" />
                </div>
            </div>
        </div>
    );
}
