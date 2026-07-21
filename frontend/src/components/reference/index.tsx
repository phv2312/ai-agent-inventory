import { Header } from './Header';
import { Table } from './Table';
import { DocumentChunksModal } from './DocumentChunksModal';

export function Reference() {
    return (
        <div className="flex h-full flex-col bg-app">
            <Header />
            <div className="flex-1 overflow-y-auto p-8">
                <Table />
            </div>
            <DocumentChunksModal />
        </div>
    );
}
