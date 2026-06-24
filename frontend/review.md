# Code Review - src/ Folder Analysis

## 🔴 Critical Issues

### App.tsx - Routing & Navigation
- **Hard-coded layout switching**: Currently switches between `DocManagementLayout` and `ChatLayout` via comments. Implement proper routing with React Router.
- **No error boundaries**: Add ErrorBoundary components to catch and handle component errors gracefully.

### State Management Issues
- **Scattered state**: Multiple slices (`chatSlice`, `chatCollectionManager`, `conversation`, etc.) manage related data separately, leading to potential inconsistency.
- **Non-normalized state**: Messages array in chatSlice should be normalized with `byId` pattern for better performance.
- **Missing selectors**: Direct state access in components instead of memoized selectors causes unnecessary re-renders.

### MessageInput.tsx - Critical Problems
- **Massive component (200+ lines)**: Violates single responsibility principle. Split into smaller components.
- **Direct API calls in component**: Business logic mixed with UI. Move to custom hooks or thunks.
- **File state management**: Files stored in local state but also passed to Redux - potential sync issues.
- **No error handling**: Stream errors logged but not shown to users.
- **Hardcoded values**: `collection_name: "default"` and other magic strings.

## 🟡 Major Issues

### Services/API Layer
- **Minimal error handling**: `client.ts` throws raw errors without proper error types or retry logic.
- **No request/response validation**: Missing runtime type validation for API responses.
- **No loading states**: API calls don't provide loading indicators consistently.
- **Hardcoded BASE_URL**: Should come from environment variables.

### Components Architecture
- **Mixed concerns**: Components like `MessageInput` handle both UI and business logic.
- **No prop validation**: Missing PropTypes or proper TypeScript interface validation.
- **Inline styles and logic**: Conditional styling and business logic mixed in JSX.

### Type Safety
- **Inconsistent typing**: Some files use proper types, others use `any` or loose typing.
- **Missing runtime validation**: Types exist but no runtime validation of API responses.
- **Enum-like objects**: Using objects for constants instead of proper TypeScript enums.

## 🟢 Positive Aspects

### Good Structure
- **Feature-based organization**: Good separation by features (chat, collection, reference, etc.).
- **Consistent naming**: File and component naming follows React conventions.
- **TypeScript usage**: Most code uses TypeScript with proper interfaces.

### Redux Implementation
- **Modern Redux Toolkit**: Using RTK with proper slice patterns.
- **Async thunks**: Proper implementation for async operations.
- **Immutable updates**: Correctly using Immer through RTK.

## 🛠️ Specific Recommendations

### Immediate Fixes (High Priority)

1. **Split MessageInput.tsx**:
   ```typescript
   // Extract hooks
   const useMessageStreaming = () => { /* streaming logic */ }
   const useFileAttachments = () => { /* file management */ }

   // Split components
   <AttachmentPanel />
   <MentionInput />
   <SendButton />
   ```

2. **Add Error Boundaries**:
   ```typescript
   // In App.tsx and major layout components
   <ErrorBoundary fallback={<ErrorFallback />}>
     <ChatLayout />
   </ErrorBoundary>
   ```

3. **Normalize Redux State**:
   ```typescript
   // In chatSlice.ts
   interface ChatState {
     messages: { byId: Record<string, ChatMessage>; allIds: string[] }
     // ... other state
   }
   ```

4. **Environment Configuration**:
   ```typescript
   // In client.ts
   const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001"
   ```

### Medium Priority

5. **Add Proper Routing**:
   ```typescript
   // In App.tsx
   import { BrowserRouter, Routes, Route } from 'react-router-dom'

   <BrowserRouter>
     <Routes>
       <Route path="/chat" element={<ChatLayout />} />
       <Route path="/documents" element={<DocManagementLayout />} />
     </Routes>
   </BrowserRouter>
   ```

6. **Create Selectors**:
   ```typescript
   // Create selectors/index.ts
   export const selectMessages = createSelector(
     (state: RootState) => state.chat.messages,
     (messages) => messages
   )
   ```

7. **Error Handling Service**:
   ```typescript
   // services/error.ts
   export class ApiError extends Error {
     constructor(public status: number, message: string) {
       super(message)
     }
   }
   ```

### Code Quality Improvements

8. **Component Extraction**:
   - Extract `AttachedFile`, `AttachmentUploadIcon` into separate files
   - Create reusable UI components library under `/components/ui/`
   - Separate container components from presentational components

9. **Custom Hooks**:
   - `useChat()` - Chat operations and state
   - `useFileUpload()` - File management logic
   - `useConversation()` - Conversation management

10. **Constants Management**:
    ```typescript
    // constants/api.ts
    export const API_ENDPOINTS = {
      MESSAGES: '/messages',
      CONVERSATIONS: '/conversations'
    } as const
    ```

### Performance Optimizations

11. **Memoization**:
    - Wrap expensive components in `React.memo()`
    - Use `useMemo()` for expensive computations
    - Use `useCallback()` for event handlers passed as props

12. **Virtual Scrolling**:
    - Implement virtualization for message lists and large data sets
    - Consider `react-window` for performance

### Testing Strategy

13. **Add Unit Tests**:
    - Test Redux slices with proper mock data
    - Test components with React Testing Library
    - Test custom hooks in isolation

14. **Integration Tests**:
    - Test complete user flows (send message, file upload)
    - Mock API responses with MSW

## Summary Score: 6.5/10

**Strengths**: Good TypeScript usage, modern Redux implementation, feature-based organization
**Main Concerns**: Large components, mixed concerns, limited error handling, missing routing
**Priority**: Focus on splitting large components and adding proper error handling first

---

- Project structure
  - Good separation by feature folders (chat, chunkViewer, collection, reference, sidebar). Consider colocating slice + services + components per feature with an index barrel to reduce cross-folder coupling.
  - Add a /routes or /pages layer if you use React Router to make navigation explicit.

- State management
  - Ensure all slices derive UI from state only; avoid duplicate state between slices that can drift. Centralize IDs for selected conversation/collection.
  - Memoize selectors with reselect to prevent unnecessary re-renders.
  - Normalize entity state (collections, references, chunks) with ids/byId patterns in slices.
  - Keep async thunks or RTK Query for API calls; prefer RTK Query for cache, dedup, and lifecycle.

- Services (api)
  - Consolidate client.ts with typed API layer, interceptors, and error handling. Define a base client that injects auth headers and handles retries/backoff.
  - Use Zod or TypeScript types + runtime validation for API responses; fail fast on schema mismatches.
  - Define request/response types alongside endpoints; export a single SDK per domain (collection, conversation, message, reference).

- Components
  - Prefer Presentational vs Container components. Logic hooks (useX) in /hooks per feature; components should be stateless where possible.
  - Use controlled inputs in MessageInput and FileDropzone; debounce user inputs that trigger queries.
  - Split large components and avoid inline anonymous functions in JSX; memoize with React.memo where props are stable.
  - Ensure accessibility: aria labels, keyboard navigation, focus management for modals.

- Modals & Uploads
  - Centralize modal state in a modal slice or use a modal manager hook. Trap focus, close on ESC, and restore focus.
  - For uploads, show progress, cancellation, and error states. Validate file types and size on client.

- Performance
  - Virtualize long lists (MessageList, ChunkList, Reference Table) with react-window or react-virtual.
  - Use Suspense boundaries and lazy load heavy feature modules.
  - Memoize expensive derived data and avoid recomputation in render.
  - Split vendor bundles via Vite dynamic imports; analyze with rollup-plugin-visualizer.

- Styling
  - Tailwind: extract reusable components and class patterns via @apply or component wrappers. Use design tokens in tailwind.config (colors, spacing).
  - Maintain a theme system (light/dark) via CSS variables and Tailwind.

- Error & Empty states
  - Provide consistent loading, empty, and error states for each async view.
  - Use an ErrorBoundary for fatal UI errors.

- Testing
  - Add unit tests for slices (reducers/selectors) and components with react-testing-library + vitest.
  - Mock API with MSW for integration tests.

- Types
  - Ensure strict TypeScript settings ("strict": true). Avoid any; prefer unknown + narrowing.
  - Co-locate types with domain and export minimal public interfaces.

- Accessibility & i18n
  - Audit with axe and Lighthouse. Ensure contrast and keyboard support.
  - Abstract strings for i18n readiness; avoid hardcoded text in components.

- DX & Quality
  - ESLint with recommended + react hooks + typescript rules. Prettier for formatting.
  - Add Husky + lint-staged to enforce pre-commit checks and typecheck.
  - CI: run build, typecheck, test, lint. Upload coverage.

- Routing & URL state
  - Reflect selected conversation/collection in URL params; enable deep links and shareable state.

- Caching
  - Define cache invalidation policies per resource. Prefer RTK Query tags.

- Security
  - Sanitize user content in messages and attachments; avoid XSS via dangerouslySetInnerHTML.
  - Use Content Security Policy and secure headers if deployed statically.

- Documentation
  - Keep diagrams up to date; add high-level architecture README per feature.
  - Document payload contracts with examples and versioning.

- Build & Env
  - Use .env files with typed env parsing (vite-env). Validate required vars at startup.

- Observability
  - Add logging utilities and user-event telemetry. Instrument API failures.

- Code conventions
  - Enforce file naming consistency (PascalCase for components, camelCase for hooks). Barrel files per folder.
  - Prefer index.ts barrels only for public exports; avoid deep relative imports with path aliases.
