# Step 2: Upload / Capture Page

> Paste this into Lovable. This builds the landing page. **Do not modify the sidebar or routing from Step 1.**

---

Build the Upload / Capture page at route `/`. This is the first thing users see. Two modes: upload a recorded video, or start a live webcam session.

## Layout

A centered card layout with two options side by side (stacked on mobile).

### Left card: "Upload Video"
- Large dashed-border dropzone area (at least 200px tall)
- Cloud upload icon (Lucide `Upload`) centered in the dropzone
- Text: "Drag & drop your lecture video here" in muted color
- Below that: "or" divider, then a "Browse Files" button (primary indigo)
- Accepted formats shown in small text: MP4, WebM, MOV — Max 100MB
- When a file is selected:
  - Show the filename and file size
  - Show a video thumbnail preview if possible (use a `<video>` element with the local file URL)
  - Show an "Analyze" button (primary, prominent)
- When "Analyze" is clicked:
  - Show a processing state: progress bar (animated, indeterminate for now) with text "Analyzing engagement patterns..."
  - After 3 seconds (simulated), redirect to `/session/demo/timeline`

### Right card: "Live Session"
- Large icon: Lucide `Video` icon
- Heading: "Start Live Session"
- Subtext: "Use your webcam to track engagement in real-time"
- A big "Start Session" button (outlined style, green/engaged color)
- When clicked, redirect to `/live`

### Top of page
- Heading: "Analyze Your Focus"
- Subtext: "Upload a lecture recording or start a live session to understand your engagement patterns"

## Mock behavior
- File upload should work locally (read the file with `URL.createObjectURL`)
- The "Analyze" button simulates processing with a 3-second delay, then navigates to `/session/demo/timeline`
- Store the selected file info in a mock data store or React state — we'll connect to the real API later

## Style
- Cards should use the `surface` background color with subtle border
- Dropzone border should be dashed, and highlight on drag-over (change border color to primary)
- Keep the page clean and spacious — this is the first impression
