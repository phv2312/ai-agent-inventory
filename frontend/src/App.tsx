import { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import "./App.css"
import { ChatLayout } from "./layout/ChatLayout"
import { DocManagementLayout } from "./layout/DocManagement"
import { MainLayout } from "./layout/MainLayout"
import { useAppDispatch } from "./hooks/redux";
import { fetchCollections } from "./store/collection.slice";
import { fetchConversations } from "./store/conversation.slice";


export default function App() {
    const dispatch = useAppDispatch();

    useEffect(() => {
        dispatch(fetchCollections());
        dispatch(fetchConversations());
    }, [dispatch]);

    return (
        <Router>
            <Routes>
                <Route path="/" element={<MainLayout />}>
                    <Route index element={<Navigate to="/chat" replace />} />
                    <Route path="/chat" element={<ChatLayout />} />
                    <Route path="/documents" element={<DocManagementLayout />} />
                </Route>
            </Routes>
        </Router>
    )
}
