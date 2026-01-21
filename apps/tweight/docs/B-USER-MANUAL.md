# tweight User Manual

## Getting Started

### Login
1. Open tweight
2. Enter your authentication token
3. Tap "Login"

Your token is saved locally - you stay logged in until you explicitly log out.

---

## Main Screen (Items List)

### Top Bar Icons (left to right)
| Icon | Name | Action |
|------|------|--------|
| Inbox | Quick Capture | Open multi-line input for rapid capture |
| List/Article | View Toggle | Switch between Card View and Text View |
| Logout | Logout | Clear token and return to login |

### Search Bar
- Type to search items by label (case-insensitive)
- Results filter in real-time
- Clear button appears when filter is active

### Tag Filter Row
- **"Tags" chip**: Tap to open full tag picker dialog
- **Individual tags**: Tap to toggle filter on/off
- Multiple tags can be selected (AND logic)
- Long-press anywhere on row: Opens tag picker

### Item List
- **Card View**: Shows label, content type, and tags
- **Text View**: Shows only labels, clean document style
- **Tap item**: Opens editor
- **Pull down**: Refresh list

### Floating Action Button (+)
Creates a new item with full editor.

---

## Quick Capture

The fastest way to add multiple items:

1. Tap **Inbox icon** in top bar
2. Enter items, **one per line**
3. Tap **Save**

**Result**: Each non-empty line becomes a new item with:
- Label = the line text
- Content Type = "note"
- Tags = ["inbox"]

**Use case**: Brain dump, morning thoughts, meeting notes.

---

## Tag Picker Dialog

Accessible from:
- "Tags" chip on main screen (for filtering)
- Tags field in item editor (for assignment)

### Features
- **Search field**: Filter tags by name
- **Selected tags**: Shown as chips at top, tap X to remove
- **Checkbox list**: All available tags, alphabetically sorted
- **Cancel**: Discard changes
- **Apply**: Confirm selection

---

## Item Editor

### Fields
| Field | Description |
|-------|-------------|
| Label | The main text/title of your item (required) |
| Content Type | Dropdown: note, task, link, other |
| Tags | Tap to open tag picker, or add new tags manually |
| New tag | Type + press add button to create new tag |

### Actions
- **Save/Create**: Saves item and returns to list
- **Back arrow**: Discards changes and returns to list

---

## Tips

### Inbox Zero Workflow
1. Use Quick Capture throughout the day
2. Filter by "inbox" tag
3. Process each item: assign proper tags, change type, or delete
4. Remove "inbox" tag when processed

### Tag Naming
- Tags are lowercase
- Keep them short: "work", "idea", "urgent"
- Be consistent: decide on singular vs plural

### Keyboard
- In tag input: Press Enter to add tag
- In Quick Capture: Each line break creates separation

---

## Troubleshooting

### App shows white screen
- Wait a few seconds (initial load)
- Check internet connection
- Try force-closing and reopening

### Items not loading
- Pull down to refresh
- Check if filters are active (clear them)
- Verify server is reachable

### Can't login
- Verify token is correct
- Check server URL in app config
