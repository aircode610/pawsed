# Step 6: Live Engagement Overlay Page

> Paste this into Lovable. **Do not modify existing pages.**

---

Build the Live Session page at route `/live`. This shows the user's webcam feed with a real-time engagement indicator overlay. This is the demo-day showstopper.

## Layout

### Main: Webcam Feed
- Center of the page: a large video element showing the user's webcam feed
- Use `navigator.mediaDevices.getUserMedia({ video: true })` to access the camera
- Aspect ratio: 16:9 or match the camera's native ratio
- **Colored border** around the video that changes based on engagement state:
  - 4px solid green (`#22c55e`) = engaged
  - 4px solid yellow (`#eab308`) = passive
  - 4px solid red (`#ef4444`) = disengaged
  - Smooth transition between colors (CSS transition on border-color, 0.5s)

### Top-right overlay: Status Badge
- Floating on top of the video, top-right corner with some padding
- Shows the current state as a pill/badge: "Engaged" / "Passive" / "Disengaged"
- Background color matches the state color
- White text, rounded, slight backdrop blur

### Bottom-left overlay: Live Metrics
- Small semi-transparent panel (backdrop-blur, dark background at 70% opacity)
- Shows in compact format:
  - EAR: 0.28 (with a small eye icon)
  - Gaze: "On screen" or "Away" (with an arrow icon)
  - Head: "Forward" or "Tilted 15°" (with a user icon)
- Update these values every second (simulated for now)

### Top-left overlay: Session Timer
- Shows elapsed time since session started: "00:00" counting up
- Small, muted text with a recording dot (red pulsing circle) next to it

### Bottom: Controls Bar
- "Stop Session" button — prominent, red/destructive style
- When clicked: stop the webcam, show a brief "Processing..." state, then redirect to `/session/live-demo/timeline`

## Mock behavior (before WebSocket is connected)

Since the WebSocket backend isn't ready yet, simulate state changes:
- Create a `useMockEngagement` hook that cycles through states:
  - Start as "engaged" for 5 seconds
  - Switch to "passive" for 3 seconds
  - Switch to "disengaged" for 2 seconds
  - Back to "engaged"
  - Repeat
- Generate realistic mock metric values that correspond to each state:
  - Engaged: EAR 0.28, Gaze "On screen", Head "Forward"
  - Passive: EAR 0.24, Gaze "Drifting", Head "Tilted 12°"
  - Disengaged: EAR 0.12, Gaze "Away", Head "Turned 35°"

## Camera permission handling
- If permission denied: show a friendly message with instructions to enable camera
- If no camera available: show an error state with a "Go back" button

## Style
- The video should take up most of the viewport (80-90% width, max 900px)
- Overlays should not obstruct the face area (keep them in corners)
- Dark page background so the video stands out
- The colored border should feel prominent — this is the visual hook for demos
