# Step 8: AI Insights — Lecture Section Scoring

> Paste this into Lovable. **Do not modify existing pages.** This replaces the old AI Coach page at `/session/:id/insights`.

---

Rebuild the AI Insights page at route `/session/:id/insights`. This is for **lecturers** analyzing their class — not students. The page shows an automated section-by-section breakdown of how the lecture went, with AI-generated teaching advice per section.

## Mock data

Replace the old `mockInsights` in `lib/mock-data.ts` with this:

```typescript
export const mockSectionScoring = {
  session_id: "demo",
  overall_summary:
    "Your lecture had a strong opening and close, but lost the class between minutes 12–18. That 6-minute danger zone brought your overall score down from what could have been 80%+ to 72.5%. The fix is structural — break that middle section with an interactive moment.",
  sections: [
    {
      label: "Introduction",
      start: 0,
      end: 300,
      engagement_pct: 89.2,
      state_breakdown: { engaged: 82, passive: 14, disengaged: 4 },
      top_event: null,
      ai_note:
        "Strong opening — students were attentive. Whatever you did here (greeting, agenda overview, hook question), keep doing it.",
    },
    {
      label: "Core Content A",
      start: 300,
      end: 720,
      engagement_pct: 71.5,
      state_breakdown: { engaged: 60, passive: 28, disengaged: 12 },
      top_event: "looked_away (4 times)",
      ai_note:
        "Gradual drift starting around minute 7. Students were passive but not fully checked out — a mid-point check-in question or quick poll could reset attention here.",
    },
    {
      label: "Danger Zone",
      start: 720,
      end: 1080,
      engagement_pct: 38.4,
      state_breakdown: { engaged: 25, passive: 30, disengaged: 45 },
      top_event: "zoned_out (45s), yawn (2 times)",
      ai_note:
        "This was the lowest-engagement stretch. 45% of the time was spent disengaged. This often happens during extended theory without interaction. Consider breaking this into two shorter blocks with an active learning exercise (think-pair-share, quick problem) in between.",
    },
    {
      label: "Recovery",
      start: 1080,
      end: 1500,
      engagement_pct: 74.8,
      state_breakdown: { engaged: 65, passive: 25, disengaged: 10 },
      top_event: "looked_away (3 times)",
      ai_note:
        "The class re-engaged here. If this section involved a demo, worked example, or change of pace, that's likely what brought them back. Try to bring that energy earlier next time.",
    },
    {
      label: "Wrap-up",
      start: 1500,
      end: 1800,
      engagement_pct: 80.1,
      state_breakdown: { engaged: 72, passive: 22, disengaged: 6 },
      top_event: null,
      ai_note:
        "Solid finish. Students were mostly attentive through the closing. Ending strong helps with retention of the final points.",
    },
  ],
};
```

## Layout

### Top: Overall Summary Card
- A highlighted card at the top, slightly different from the rest (subtle indigo left border or a light indigo background tint)
- Icon: Lucide `Sparkles`
- Heading: "Lecture Summary"
- Body: the `overall_summary` text
- Below the text: two inline stats — "Overall: **72.5%** engaged" and "Danger zones: **1**"

### Main: Section Cards (vertical stack)
Each section is a card. Show them in chronological order.

**Card contents:**
- **Header row:**
  - Left: section label in bold (e.g., "Introduction")
  - Right: time range formatted as "0:00 – 5:00"
- **Engagement score:** large number with color
  - Green if >= 70%
  - Yellow if 50–69%
  - Red if < 50%
- **State breakdown bar:** a thin horizontal stacked bar (8px tall, full card width) showing the three states as colored segments proportional to their percentages. Green = engaged, yellow = passive, red = disengaged.
- **Top event:** if not null, show as a small muted pill: "looked_away (4 times)" with a relevant icon
- **AI note:** the coaching text, in regular weight, `leading-relaxed`, slightly muted color
- **Danger zone styling:** if `engagement_pct < 50`, the card gets a red left border (3px solid red-500) and a very subtle red background tint

**Card interaction:**
- Clicking a section card navigates to `/session/:id/timeline` (ideally scrolling to that time range — but for now just navigate to the timeline page)

### Sub-navigation
Use the session sub-navigation tabs. Rename the "AI Coach" tab to "Insights" and make it active on this page.

## Style
- Section cards should have generous padding and spacing between them
- The state breakdown bar should have rounded ends and look like a miniature version of the timeline bar
- AI notes should feel like a colleague giving feedback — warm typography, not clinical
- Keep the page scannable — a lecturer should be able to glance at the colors and scores to know which sections need work, then read the AI notes for the ones that matter
- Muted footer text: "Analysis powered by Claude AI"
