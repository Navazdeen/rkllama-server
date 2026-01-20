# RKLLM Chat UI - Quick Visual Guide

## 3-Panel Layout Overview

```
═══════════════════════════════════════════════════════════════════════════
                    🤖 RKLLM Advanced Chat Interface
                    QWEN2.5-3B-INSTRUCT-RK3588 • RK3588
═══════════════════════════════════════════════════════════════════════════
│                                                                          │
│  ┌──────────────────────┬───────────────────────────┬─────────────────┐ │
│  │                      │                           │                 │ │
│  │   📋 SESSIONS        │   💬 CONVERSATION        │  ⚙️ SETTINGS    │ │
│  │   ─────────────      │   ──────────────────     │  ──────────────  │ │
│  │                      │                           │                 │ │
│  │  Current Session:    │                           │  🌊 Streaming   │ │
│  │  [session_1 ──▼]     │  ╔═════════════════════╗ │  ☑ Enabled      │ │
│  │                      │  ║ 👤 User message    ║ │                 │ │
│  │  ➕ New              │  ║ here...            ║ │  🧠 Use Context │ │
│  │  🗑️ Delete           │  ║                    ║ │  ☑ Enabled      │ │
│  │                      │  ╠═════════════════════╣ │                 │ │
│  │  ─────────────       │  ║ 🤖 Assistant       ║ │  ──────────────  │ │
│  │                      │  ║ response here...   ║ │                 │ │
│  │  Messages: 5         │  ║                    ║ │  Model Info     │ │
│  │  Last: 14:32:15      │  ║                    ║ │  ℹ️ Show Details│ │
│  │                      │  ║                    ║ │  ┌─────────────┐ │ │
│  │  ─────────────       │  ║ 👤 Another user    ║ │  │ Model:      │ │ │
│  │                      │  ║ message...         ║ │  │ Qwen 2.5-3B │ │ │
│  │  All Sessions        │  ║                    ║ │  │ Platform:   │ │ │
│  │  • session_1 ✓       │  ║ 🤖 Another assist. ║ │  │ RK3588      │ │ │
│  │  • session_2         │  ║ response...        ║ │  │ Status: ✅  │ │ │
│  │  • session_3         │  ║                    ║ │  │ Sessions: 3 │ │ │
│  │                      │  ║                    ║ │  └─────────────┘ │ │
│  │                      │  ║                    ║ │                 │ │
│  │                      │  ╠═════════════════════╣ │  ──────────────  │ │
│  │                      │  ║ [Type message...  ] ║ │                 │ │
│  │                      │  ║ [cont'd if needed ] ║ │  🧹 Clear Chat  │ │
│  │                      │  ║ [for long input  ] ║ │                 │ │
│  │                      │  ║        [📤 Send]   ║ │  ──────────────  │ │
│  │                      │  ╚═════════════════════╝ │                 │ │
│  │                      │                           │  Status:        │ │
│  │                      │                           │  Ready          │ │
│  │                      │                           │  ────────       │ │
│  │                      │                           │                 │ │
│  └──────────────────────┴───────────────────────────┴─────────────────┘ │
│                                                                          │
│  Scale:  1/5         3/5          1/5                      5/5 Total   │
│         16%          60%          16%                                   │
│                                                                          │
═══════════════════════════════════════════════════════════════════════════
```

---

## Component Locations

### LEFT SIDEBAR - Session Management
```
┌─────────────────────────────┐
│ 📋 Sessions                 │
├─────────────────────────────┤
│ Current Session:            │
│ [Dropdown ────────────────▼]│
│ ┌─────────────┬────────────┐│
│ │ ➕ New      │ 🗑️ Delete ││
│ └─────────────┴────────────┘│
├─────────────────────────────┤
│ Session Info                │
│ ┌─────────────────────────┐ │
│ │ Messages: 5             │ │
│ │ Last: 14:32:15          │ │
│ └─────────────────────────┘ │
├─────────────────────────────┤
│ All Sessions                │
│ ┌─────────────────────────┐ │
│ │ • session_1             │ │
│ │ • session_2             │ │
│ │ • session_3             │ │
│ │                         │ │
│ │                         │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
     (Scrollable list)
     Scale 1/5 = 16%
```

### CENTER PANEL - Chat (Main Focal Point)
```
┌───────────────────────────────────────────┐
│ 💬 Conversation                           │
├───────────────────────────────────────────┤
│ 👤 User: Tell me about Python            │
│ 🤖 Assistant: Python is a programming... │
│    ...multiple lines of response...      │
│ 👤 User: What about async/await?        │
│ 🤖 Assistant: Async/await provides...    │
│    ...more response content...           │
│                                           │
│ [Chat area continues...]                 │
│ [Height: 600px - Plenty of space]       │
│                                           │
├───────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐   │
│ │ Type your message here...           │   │
│ │                                     │   │
│ │ (3 lines for longer messages)       │   │
│ │                           [📤 Send] │   │
│ └─────────────────────────────────────┘   │
│                                           │
└───────────────────────────────────────────┘
    Scale 3/5 = 60% (Main chat area)
```

### RIGHT SIDEBAR - Settings & Info
```
┌──────────────────────────┐
│ ⚙️ Settings              │
├──────────────────────────┤
│ 🌊 Streaming             │
│ ☑ Enable streaming       │
│                          │
│ 🧠 Use Context           │
│ ☑ Include history        │
├──────────────────────────┤
│ Model Info               │
│ ┌────────────────────┐   │
│ │ ℹ️ Show Details    │   │
│ └────────────────────┘   │
│ ┌────────────────────┐   │
│ │ Model: Qwen 2.5-3B│   │
│ │ Platform: RK3588   │   │
│ │ Status: ✅ Running │   │
│ │ Sessions: 3        │   │
│ │ Context: 4000 chars│   │
│ │ Max History: 20    │   │
│ └────────────────────┘   │
├──────────────────────────┤
│ Actions                  │
│ ┌────────────────────┐   │
│ │ 🧹 Clear Chat      │   │
│ └────────────────────┘   │
├──────────────────────────┤
│ Status                   │
│ ┌────────────────────┐   │
│ │ Ready              │   │
│ │ ────────           │   │
│ └────────────────────┘   │
└──────────────────────────┘
    Scale 1/5 = 16%
```

---

## Workflow Examples

### Creating a New Session

```
START
  │
  └─→ Click [➕ New] button
      │
      ├─→ Backend creates "session_4"
      │
      ├─→ Update Left Sidebar:
      │   ├─ Dropdown now shows "session_4"
      │   ├─ Session info: "Messages: 0"
      │   └─ List shows all sessions + new one
      │
      ├─→ Update Center Panel:
      │   └─ Chatbot cleared (empty)
      │
      └─→ Status: "✅ Created session_4"
```

### Sending a Message

```
START
  │
  └─→ Type message in Center input box
      │
      ├─→ Click [📤 Send] or press Enter
      │
      ├─→ Message appears in Center chat area
      │   (User message shown)
      │
      ├─→ Backend generates response
      │   (Streaming: Shows token by token)
      │
      ├─→ Response appears in Center chat area
      │   (Assistant message shown)
      │
      ├─→ Update Left Sidebar:
      │   ├─ Session info updates count
      │   └─ Timestamp changes
      │
      └─→ Status: "Ready"
```

### Switching Sessions

```
START
  │
  └─→ Click different session in Left dropdown
      │
      ├─→ Backend loads session history
      │
      ├─→ Update Center Panel:
      │   └─ Shows previous messages from that session
      │
      ├─→ Update Left Sidebar:
      │   ├─ Session info reflects new session
      │   └─ Dropdown shows selected session
      │
      └─→ Continue chatting in new context
```

### Page Refresh (Persistence)

```
START
  │
  └─→ User closes and reopens browser
      │ (or refreshes page)
      │
      ├─→ Page loads
      │
      ├─→ Backend loads default session
      │
      ├─→ Left Sidebar populated:
      │   ├─ All sessions shown
      │   ├─ Previous session info restored
      │   └─ Message count restored
      │
      ├─→ Center Panel shows:
      │   └─ All previous messages still there!
      │
      └─→ Ready to continue conversation
```

---

## Keyboard Shortcuts

| Action | Key |
|--------|-----|
| Send message | Enter |
| New message | Shift+Enter (multiline) |
| Focus input | Tab |

---

## Visual Indicators

| Symbol | Meaning |
|--------|---------|
| ✅ | Enabled/Active/Ready |
| ☑ | Checked/Enabled |
| ☐ | Unchecked/Disabled |
| ➕ | Add new |
| 🗑️ | Delete |
| 📤 | Send |
| 🧹 | Clear |
| ℹ️ | Information |
| 🤖 | Assistant |
| 👤 | User |
| 💬 | Chat |
| 📋 | Sessions |
| ⚙️ | Settings |
| 🌊 | Streaming |
| 🧠 | Context |

---

## Tips & Features

### Left Sidebar Tips
- 👆 Click session names to quickly switch
- 📊 Watch message count grow as you chat
- 🗑️ Delete old sessions to keep organized
- ➕ Create separate sessions for different topics

### Center Panel Tips
- 💬 Scroll to see entire conversation
- 📝 Use Enter for new line, Shift+Enter for submit
- ⏱️ Streaming shows responses in real-time
- 🔄 Messages sync immediately (no delay)

### Right Sidebar Tips
- 🌊 Disable streaming for faster responses
- 🧠 Disable context for independent responses
- ℹ️ Check model info for details
- 🧹 Clear chat to start fresh in session

---

## Component Dimensions

| Component | Size | Notes |
|-----------|------|-------|
| Chatbot | 600px height | Increased for visibility |
| Message input | 3 lines | Supports multiline |
| Sessions list | 8 lines | Scrollable |
| Session info | 2 lines | Compact display |
| Model info | 6 lines | Detailed display |
| Status | 2 lines | Compact display |

---

## Theme & Colors

| Element | Color |
|---------|-------|
| Border (dividers) | #e0e0e0 (light gray) |
| Background (hover) | rgba(0,0,0,0.05) (subtle) |
| Text (dark) | Default (theme) |
| Text (light) | Soft theme (Gradio) |
| Buttons | Theme colors |

---

## Responsive Behavior

### On Different Screens

| Screen Size | Layout | Behavior |
|-------------|--------|----------|
| Desktop | 3-panel | Full width, optimized |
| Tablet | 3-panel | Scales down, still visible |
| Phone | 3-panel | May need horizontal scroll |

---

## Accessibility

- ✅ All buttons have clear labels
- ✅ Color contrasts meet standards
- ✅ Keyboard navigation supported
- ✅ Screen reader compatible (Gradio built-in)
- ✅ No flashing or animations

---

## Performance Notes

- ⚡ Fast panel transitions
- ⚡ Smooth message streaming
- ⚡ Responsive input
- ⚡ No unnecessary redraws

---

**This visual guide provides quick reference for the RKLLM Chat 3-Panel Interface.**

For detailed documentation, see:
- `UI_REDESIGN_3PANEL_LAYOUT.md` - Full specifications
- `UI_DESIGN_VERIFICATION.md` - Technical details
- `UI_REDESIGN_SUMMARY.md` - Implementation summary
