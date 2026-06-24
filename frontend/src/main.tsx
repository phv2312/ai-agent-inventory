import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import './index.css'
import App from './App.tsx'
import { StrictMode } from 'react'
import { store } from './store/index.ts'


createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <Provider store={store}>
            <App />

        </Provider>
    </StrictMode>
)
