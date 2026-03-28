# Step 1: App Shell, Navigation & Routing

> Paste this into Lovable as your **first prompt** after setting the knowledge file.

---

Build the app shell for Pawsed — a student engagement analytics platform. The name is a play on "paused + paws" — for when attention pauses. Dark mode, modern SaaS look.

## What to build

### 1. Layout
- A sidebar navigation on the left (collapsible on mobile into a hamburger menu)
- Main content area on the right
- Sidebar width: 240px on desktop

### 2. Sidebar contents
- App logo at top: the text "Pawsed" with a small paw icon from Lucide (use `PawPrint` icon)
- Nav items with icons:
  - **Home** (Upload icon) → `/`
  - **Sessions** (History icon) → `/sessions`
  - **Profile** (User icon) → `/profile`
- Active nav item highlighted with the primary indigo color
- Bottom of sidebar: a subtle "v0.1 — Hackathon" label in muted text

### 3. Routing
Set up React Router with these routes — just render placeholder pages for now (a centered heading with the page name):
- `/` → Upload page
- `/live` → Live Session page
- `/session/:id/timeline` → Timeline page
- `/session/:id/analytics` → Analytics page
- `/session/:id/report` → Focus Report page
- `/session/:id/insights` → AI Coach page
- `/sessions` → Session History page
- `/profile` → Gamification page

### 4. Theme
- Dark background: `#0f172a`
- Card surfaces: `#1e293b`
- Text: `#f8fafc`
- Muted text: `#94a3b8`
- Store these as custom Tailwind colors under `engage` namespace in tailwind config

### 5. Style
- Clean and minimal. No gradients. Subtle 1px borders on cards (`border-slate-700`).
- Inter font if available, otherwise system font stack.
- Smooth page transitions are a bonus but not required.

Do not add any page content yet — just the shell with placeholder headings. We will build each page in subsequent prompts.
