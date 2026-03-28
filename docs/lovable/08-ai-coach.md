# Step 8: AI Coach Suggestions Page

> Paste this into Lovable. **Do not modify existing pages.**

---

Build the AI Coach page at route `/session/:id/insights`. This renders AI-generated study recommendations in a friendly, conversational format.

## Mock data

Add to `lib/mock-data.ts`:

```typescript
export const mockInsights = {
  session_id: "demo",
  recommendations: [
    {
      title: "Schedule study sessions earlier",
      body: "Your yawn frequency peaked around the 14-minute mark (4:30pm equivalent). Research shows alertness drops in the late afternoon. Try scheduling your most demanding study sessions before 2pm when your natural energy is higher.",
      category: "timing",
    },
    {
      title: "Break up theory-heavy sections",
      body: "You lost focus 3 times between minutes 12–18, which is the danger zone we identified. This coincided with sustained passive engagement. Try the Pomodoro technique — review that segment in 10-minute focused bursts with 2-minute breaks.",
      category: "technique",
    },
    {
      title: "Build on your focus strength",
      body: "Your longest focus streak was 11 minutes — that's a solid foundation! Try extending it to 15 minutes by removing phone notifications during study blocks. Even small distractions reset your focus timer.",
      category: "encouragement",
    },
    {
      title: "Address the 'looking away' pattern",
      body: "Looking away was your most common distraction (7 times). This often happens when the material isn't engaging visually. Try taking handwritten notes during these sections — it forces active engagement with the content.",
      category: "technique",
    },
    {
      title: "Your improvement trajectory",
      body: "You recovered from your danger zone (minutes 12–18) and finished the session strong with 80%+ engagement in the final 10 minutes. This shows resilience — you're able to re-engage after dips, which is a skill that improves with practice.",
      category: "encouragement",
    },
  ],
  generated_at: "2026-03-28T14:35:00Z",
};
```

## Layout

### Top: Header
- Icon: Lucide `Sparkles` or `Bot`
- Heading: "Your AI Study Coach"
- Subtext: "Personalized recommendations based on your session data"

### Main: Recommendation Cards
- Each recommendation is a **card** — vertical stack with generous spacing between cards
- Card contents:
  - **Category badge** in top-left: colored pill
    - "timing" → blue badge
    - "technique" → purple badge
    - "encouragement" → green badge
  - **Title**: bold, 1.25rem
  - **Body**: regular text, muted color, good line height for readability
  - Left border accent: 3px solid, color matches the category

### Bottom: Actions
- "Regenerate Suggestions" button (outlined, with a `RefreshCw` icon) — for now just show a loading spinner for 2 seconds and then redisplay the same data
- Muted text: "Powered by Claude AI"

### Loading state
- Before recommendations "load" (simulate 1.5s delay on page mount):
  - Show 3 skeleton cards with pulsing animation
  - Small text: "Your AI coach is analyzing your session..."

## Style
- Cards should feel conversational and approachable — not clinical
- Good typography: body text should have `leading-relaxed` for readability
- The left border accent on each card adds visual interest without being loud
- Use the session sub-navigation tabs (AI Coach tab active)
