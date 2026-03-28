# Building the Pawsed Frontend with Lovable

## How Lovable Works

Lovable is an AI web app builder — you describe what you want in plain English and it generates a full React + TypeScript + Tailwind + shadcn/ui app. It gives you a live preview and you iterate by giving follow-up prompts.

**Key things to know:**
- It outputs real, exportable React/TypeScript code (not proprietary)
- Built-in stack: React + Vite + Tailwind CSS + shadcn/ui
- You can sync the output to GitHub and continue development in VS Code
- Build **one component/page at a time** — don't dump everything in one prompt
- It understands screenshots, design references, and OpenAPI specs

## Strategy for Pawsed

We're building **frontend-first** — get the UI looking right with mock data, then wire up the FastAPI backend later. This is the recommended approach because:
- Backend and frontend can be developed in parallel
- You can demo the UI before the API is fully ready
- Lovable is strongest at generating frontend code

## Step-by-Step Build Order

Feed these prompts to Lovable **one at a time**, in order. Each step builds on the previous one.

| Step | File | What It Builds | Priority |
|------|------|----------------|----------|
| 0 | [00-knowledge-file.md](./00-knowledge-file.md) | Paste into Lovable's Knowledge File (sent with every prompt) | Setup |
| 1 | [01-layout-and-nav.md](./01-layout-and-nav.md) | App shell, navigation, routing, theme | P0 |
| 2 | [02-upload-page.md](./02-upload-page.md) | Upload / Capture landing page | P0 |
| 3 | [03-timeline-page.md](./03-timeline-page.md) | Session Timeline with video + color-coded bar | P0 |
| 4 | [04-dashboard-page.md](./04-dashboard-page.md) | Analytics Dashboard with charts | P0 |
| 5 | [05-api-client.md](./05-api-client.md) | TypeScript API client + wire up to real backend | P0 |
| 6 | [06-live-overlay.md](./06-live-overlay.md) | Live webcam session with engagement overlay | P1 |
| 7 | [07-focus-report.md](./07-focus-report.md) | Personal Focus Report ("Spotify Wrapped" style) | P1 |
| 8 | [08-ai-coach.md](./08-ai-coach.md) | AI Coach Suggestions page | P2 |
| 9 | [09-history-and-gamification.md](./09-history-and-gamification.md) | Session History + Gamification | P2 |

## Tips for Working with Lovable

1. **First prompt matters most** — Step 0 (knowledge file) sets the tone for everything
2. **Be specific about what NOT to change** — when adding a new page, say "do not modify existing pages"
3. **Use screenshots** — if something looks wrong, screenshot it and say "fix this"
4. **Don't fight loops** — if Lovable gets stuck, revert to the last working state and rephrase
5. **One feature per prompt** — resist the urge to ask for 5 things at once
6. **Use real data** — the mock data in these prompts is realistic, which produces better layouts
7. **Export to GitHub** early — sync your project so you have a backup

## Connecting to the FastAPI Backend

When you're ready to connect (Step 5), you'll need:
1. Your FastAPI backend running (locally with ngrok, or deployed)
2. The OpenAPI spec from `http://localhost:8000/openapi.json`
3. CORS configured on the backend to allow Lovable's preview domain

## After Export

Once you export from Lovable to GitHub, the code lives in `frontend/` and can be developed with standard tooling:
```bash
cd frontend
npm install
npm run dev
```
