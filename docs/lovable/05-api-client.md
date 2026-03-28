# Step 5: TypeScript API Client

> Paste this into Lovable **after the backend is running**. This wires up real data. **Do not modify any UI components — only add the API client and swap mock data for real API calls.**

---

Create a TypeScript API client in `lib/api.ts` that connects to our FastAPI backend. Then update existing pages to use real data instead of mock data.

## API Client (`lib/api.ts`)

Create a typed API client using `fetch`. The base URL should be configurable:

```typescript
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
```

### Functions to create:

**`analyzeVideo(file: File): Promise<{ session_id: string }>`**
- `POST /analyze` with the file as multipart form data
- Returns the session ID

**`getSession(id: string): Promise<SessionData>`**
- `GET /session/${id}`
- Returns the full session data (events, analytics, engagement states)

**`getInsights(id: string): Promise<InsightData>`**
- `GET /session/${id}/insights`
- Returns AI-generated recommendations

**`getSessions(): Promise<SessionSummary[]>`**
- `GET /sessions`
- Returns list of past sessions

### Types

Create types in `lib/types.ts` that match the API response shapes from the knowledge file. Export them so all pages can use them.

## Pages to update

### Upload page (`/`)
- When "Analyze" is clicked, call `analyzeVideo(file)` instead of the 3-second timeout
- Show a real progress state (or an indeterminate spinner while waiting)
- On success, redirect to `/session/${response.session_id}/timeline`
- On error, show an error toast using shadcn Toast

### Timeline page (`/session/:id/timeline`)
- On mount, call `getSession(id)` using the route param
- Show a loading skeleton while data is fetching
- Replace mock data with real API response
- If the API call fails, fall back to mock data and show a subtle warning banner: "Using demo data — backend not connected"

### Dashboard page (`/session/:id/analytics`)
- Same pattern: fetch real data, loading skeleton, fallback to mock

## Environment
- Add `VITE_API_URL` to a `.env` file (not committed)
- Default to `http://localhost:8000` when not set

## Do NOT
- Do not modify any visual styling or layout
- Do not remove the mock data file — keep it as a fallback
- Do not add authentication headers (not needed yet)
