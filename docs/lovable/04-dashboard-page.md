# Step 4: Analytics Dashboard Page

> Paste this into Lovable. **Do not modify existing pages.** Reuse the mock data from `lib/mock-data.ts`.

---

Build the Analytics Dashboard page at route `/session/:id/analytics`. This shows charts and metrics for the session. Use the `mockSession` data already created in `lib/mock-data.ts`.

## Layout

### Top: Headline Metric
- A large, prominent card centered at the top
- Shows: "You were focused **72.5%** of this session"
- The percentage should be large (3-4rem), colored green if > 70%, yellow if 50-70%, red if < 50%
- Below it: session date and duration in muted text

### Row 1: Engagement Over Time (full width)
- **Area chart** using Recharts `AreaChart`
- X-axis: minutes (1 through 30, from `engagement_curve`)
- Y-axis: engagement score (0 to 1.0)
- Fill color: use a gradient — green at top fading to transparent at bottom
- Line color: green-500
- Overlay the danger zones as semi-transparent red rectangles using Recharts `ReferenceArea`
- Card title: "Engagement Over Time"
- Tooltip on hover showing the exact score for each minute

### Row 2: Two charts side by side (stacked on mobile)

**Left: State Distribution (Pie Chart)**
- Recharts `PieChart` showing time spent in each state
- Calculate from `engagement_states`: sum up the duration of each state
- Three slices: Engaged (green), Passive (yellow), Disengaged (red)
- Show percentages on the chart or in a legend below
- Card title: "Time Distribution"

**Right: Distraction Types (Bar Chart)**
- Recharts `BarChart` showing count of each distraction type
- From `distraction_breakdown`: yawn (3), looked_away (7), eyes_closed (2), zoned_out (1)
- Bars colored red-400
- Labels on x-axis should be human-readable: "Yawn", "Looked Away", "Eyes Closed", "Zoned Out"
- Card title: "Distraction Types"

### Row 3: Two metric cards side by side

**Left: Focus Streak**
- Icon: Lucide `Flame` or `Zap`
- Heading: "Longest Focus Streak"
- Value: "11 min" (660 seconds = 11 minutes)
- Subtext: "Without any distraction events"

**Right: Danger Zones**
- Icon: Lucide `AlertTriangle`
- Heading: "Danger Zones"
- List the danger zones: "12:00 — 18:00 (avg score: 35%)"
- Subtext: "Time ranges where engagement dropped significantly"

## Reuse
- Use the same session sub-navigation tabs from the Timeline page (Timeline, Analytics, Report, AI Coach) — Analytics tab should be active
- Use the same `mockSession` data — do not create new mock data

## Style
- All charts inside shadcn `Card` components with padding
- Charts should be at least 300px tall
- Use consistent card styling with the rest of the app
- Responsive: charts stack vertically on mobile
