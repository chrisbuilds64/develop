# UC-FE-002: PressRoom (Editorial Dashboard)

**Created:** 2026-02-13
**Last Updated:** 2026-04-15
**Type:** Frontend
**Status:** v2 DONE (Phase 6, deployed). Open source playground strategy in planning.
**Owner:** Christian Moser
**Phase:** 6 (Deployment), v2 complete
**Provenance:** Migrated from the private control repo and translated to English, 2026-07-19. Prior revision history remains in the control repo.

---

## Meta

**Provides:**
- Visual command center for the content pipeline (content/flow/)
- 6-column Kanban board with drag & drop
- Article detail view with Markdown rendering
- Production workflow screen (notes + rules + deliverables checklist)
- Rules viewer/editor for content guidelines
- Idea editor for creating new pipeline entries
- Move functionality (physically relocates article folders between stages)
- Completeness tracking per article (11 deliverables)

**Runtime:** Flutter Desktop (macOS only), local, no sandbox

**Relates to:** UC-AG-002 (Editorial System) -- PressRoom is the UI, UC-AG-002 defines the agents

---

## Dependencies

| Component | Required | Status |
|-----------|----------|--------|
| UC-AG-002 Editorial System | Pipeline structure definition | IN PROGRESS |
| content/flow/ directory structure | 6 stage directories must exist | DONE |
| content/rules/ directory | Rule files for production guidelines | DONE |
| Flutter SDK 3.x | macOS Desktop support | DONE |
| flutter_markdown ^0.7.6+2 | Only external dependency | DONE |

---

## 1. Business Understanding

**Problem:**
Content pipeline (6 stages, ~40+ articles) is purely filesystem-based. No visual overview, no quick navigation, status only visible by browsing directories manually.

**Stakeholder:** Christian (single user)

**Success Criteria:**
- Pipeline status visible at a glance (Kanban board)
- Article details + files reachable in 2 clicks
- Move articles between stages without terminal
- New ideas captured directly in UI
- Production rules accessible while producing content
- Drag & drop for quick stage changes

**Scope:**
- IN: Kanban Board, Article Detail, File Viewer, Move, Drag & Drop, Idea Editor, Rules Viewer/Editor, Produce Screen, Markdown Rendering
- IN: Dark Theme (Material 3), macOS Desktop only
- OUT: Content editing (VS Code remains the editor)
- OUT: Agent integration (comes with UC-AG-002)
- OUT: Analytics dashboard (later)
- OUT: Multi-user / Auth

---

## 2. Data Understanding

**Data Source:** Filesystem

| Path | Purpose |
|------|---------|
| `content/flow/` | Pipeline with 6 stage directories |
| `content/rules/` | Production guidelines (.md files) |

**Pipeline Stages:**

| Directory | Stage | Order | Color (Hex) | Content |
|-----------|-------|-------|-------------|---------|
| 10-ideas/ | Ideas | 10 | #7C4DFF (Purple) | Folders (each with source.md) |
| 20-produce/ | Produce | 20 | #448AFF (Blue) | Article folders |
| 30-review/ | Review | 30 | #FF9800 (Orange) | Article folders + reviews |
| 40-review-human/ | Human Review | 40 | #FF5722 (Deep Orange) | Article folders + reviews |
| 50-ready-to-publish/ | Ready to Publish | 50 | #4CAF50 (Green) | Complete articles |
| 60-published/ | Published | 60 | #78909C (Blue-Grey) | Archived articles |

**Article Folder Structure:** Up to 11 deliverables + meta.json

| Deliverable | Alternatives |
|-------------|-------------|
| substack.md | source.md (legacy) |
| substack.html | source.html (legacy) |
| linkedin-post.txt | -- |
| first-comment.txt | -- |
| linkedin-article.txt | -- |
| linkedin-article.html | -- |
| tiktok-script.txt | -- |
| dalle-prompt.txt | -- |
| title-dark.svg | -- |
| title-light.svg | -- |
| meta.json | -- |

**meta.json:** Schema varies significantly across articles (DAY-001 has none, DAY-032 has everything). Parser MUST be fully tolerant -- all fields nullable, try-catch around JSON decode.

**Rules Files:** 6 Markdown files in content/rules/:
- CONTENT-PROCESS.md
- CONTENT-STRATEGY.md
- LINKEDIN-POST-PATTERNS.md
- PLATFORM-PLAYBOOKS.md
- TAGS.md
- WEEKLY-WORKFLOW.md

---

## 3. Architecture

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | Flutter 3.x (macOS Desktop) | Existing stack, native performance |
| State Management | ChangeNotifier + setState | Flutter built-in, 0 dependencies |
| Storage | Filesystem direct (dart:io) | ~40 articles, <100ms scan, DB = overhead |
| Theme | Material 3 Dark | Dashboard aesthetic |
| Markdown | flutter_markdown ^0.7.6+2 | Only external dependency |
| Window | 1400x800 default, 1000x600 minimum | Kanban needs horizontal space |

### macOS Configuration

**Sandbox:** DISABLED (both Debug and Release entitlements)
- `com.apple.security.app-sandbox` = false
- Required for filesystem access to content/ directory

**Window Setup** (MainFlutterWindow.swift):
- Default size: 1400x800
- Minimum size: 1000x600
- Centered on screen
- Title: "PressRoom"

### Project Structure

```
develop/apps/pressroom/
├── pubspec.yaml                    # flutter, cupertino_icons, flutter_markdown
├── assets/
│   └── dalle-logo-prompt.txt       # DALL-E prompt for app logo
├── lib/
│   ├── main.dart                   # App entry, theme configuration
│   ├── config.dart                 # Paths + stage color constants
│   ├── models/
│   │   ├── pipeline_stage.dart     # Enum: 6 stages with order, label, dirName, color
│   │   ├── article.dart            # Article model with completeness calculation
│   │   └── article_meta.dart       # Tolerant JSON parser for meta.json
│   ├── services/
│   │   ├── filesystem_service.dart # Scan, read, write, move, create, rules
│   │   └── pipeline_notifier.dart  # ChangeNotifier wrapping FilesystemService
│   ├── screens/
│   │   ├── dashboard_screen.dart   # Main Kanban board (6 columns)
│   │   ├── article_detail_screen.dart # Detail view with file list + viewer
│   │   ├── idea_editor_screen.dart # Form to create new ideas
│   │   ├── produce_screen.dart     # Production view (notes + rules + checklist)
│   │   └── rules_screen.dart       # Rules viewer/editor
│   └── widgets/
│       ├── article_card.dart       # Card with 3-dot menu, track badge, completeness
│       ├── stage_column.dart       # Kanban column with DragTarget
│       ├── file_viewer.dart        # Text/Markdown viewer (flutter_markdown for .md)
│       ├── completeness_indicator.dart # Linear progress bar + percentage
│       └── move_buttons.dart       # Prev/Next stage buttons with confirmation
└── macos/
    └── Runner/
        ├── DebugProfile.entitlements  # sandbox = false
        ├── Release.entitlements       # sandbox = false
        └── MainFlutterWindow.swift    # 1400x800, min 1000x600
```

---

## 4. Data Model

### PipelineStage (enum)

```
enum PipelineStage {
  ideas(10, 'Ideas', '10-ideas', StageColors.ideas),
  produce(20, 'Produce', '20-produce', StageColors.produce),
  review(30, 'Review', '30-review', StageColors.review),
  reviewHuman(40, 'Human Review', '40-review-human', StageColors.reviewHuman),
  readyToPublish(50, 'Ready to Publish', '50-ready-to-publish', StageColors.readyToPublish),
  published(60, 'Published', '60-published', StageColors.published);

  Properties: order (int), label (String), dirName (String), color (Color)
  Navigation: next, previous (nullable, index-based)
}
```

### Article

| Property | Type | Source | Notes |
|----------|------|--------|-------|
| folderName | String | Directory/file name | e.g. "DAY-032-40-Years-Same-Bugs" |
| absolutePath | String | Full filesystem path | For read/move operations |
| stage | PipelineStage | Parent directory | Which pipeline stage |
| meta | ArticleMeta? | meta.json | Nullable, tolerant parsing |
| files | List\<String\> | Directory listing | Sorted, hidden files excluded |
| isStandaloneFile | bool | Entity type check | Legacy, should be false (all ideas are folders now) |

**Computed Properties:**
- `displayTitle`: meta.title ?? title parsed from folder name (strip prefix + day number)
- `dayNumber`: meta.day ?? regex from folder name (DAY-XXX pattern)
- `prefix`: regex match for PREFIX-NUMBER pattern (DAY-032, VID-001, etc.)
- `completeness`: ratio of found deliverables / 11 expected (grouped alternatives)
- `track`: meta.track (used for color-coded badge)
- `mood`: meta.mood

**Title Parsing Logic:** `DAY-032-40-Years-Same-Bugs` → strip `DAY-032-` → `40 Years Same Bugs`
Supported prefixes: DAY, VID, TOP, SPECIAL, FEATURED, WEEK

### ArticleMeta

All fields nullable. Parsed from meta.json with try-catch around jsonDecode.

| Field | Type | Notes |
|-------|------|-------|
| day | int? | Article number |
| title | String? | Display title |
| subtitle | String? | Subheading |
| slug | String? | URL slug |
| created | String? | Creation date |
| publishDate | String? | Publish date |
| status | String? | Current status text |
| track | String? | Content track (deep-tech, clarity, security, tech) |
| theme | String? | Topic theme |
| mood | String? | Writing mood |
| location | String? | Where written |
| tags | List\<String\> | Default empty |
| platforms | Map\<String, bool\> | Platform publish status, default empty |
| boost | bool? | Promotion flag |
| coreMessage | String? | Key takeaway |
| ctaType | String? | Call-to-action type |

### RuleFile

Simple data class: `name` (String), `path` (String). Used by FilesystemService.listRules().

---

## 5. Services

### FilesystemService

| Method | Signature | Behavior |
|--------|-----------|----------|
| scanPipeline | `Future<Map<PipelineStage, List<Article>>>` | Iterates all 6 stage dirs, returns sorted articles |
| readFile | `Future<String> readFile(String path)` | Returns content or '[File not found]' |
| moveArticle | `Future<void> moveArticle(Article, PipelineStage)` | Directory.rename() or File.rename() for standalone |
| createIdea | `Future<void> createIdea(String folderName, String content)` | Creates folder + source.md in 10-ideas/ |
| listRules | `Future<List<RuleFile>>` | Lists .md files in content/rules/, sorted by name |
| writeFile | `Future<void> writeFile(String path, String content)` | Writes string to file (for rules editing) |

**Core Concept: Folder = Container**
Each article is a folder that acts as a container. It starts with just `source.md` (the idea) and accumulates deliverables (linkedin-post.txt, substack.md, etc.) as it moves through the pipeline. PressRoom moves the entire folder between stages via drag & drop -- the folder IS the unit of work.

**Scan Logic:**
- Skip hidden files (starting with '.')
- Directories → Article with file list + optional meta.json
- Sort: by dayNumber descending, then by folderName ascending

### PipelineNotifier (ChangeNotifier)

| Property | Type | Purpose |
|----------|------|---------|
| _pipeline | Map\<PipelineStage, List\<Article\>\> | All articles by stage |
| _loading | bool | Loading indicator |
| _error | String? | Error message display |

| Method | Behavior |
|--------|----------|
| refresh() | Scans pipeline, notifies listeners |
| moveArticle(article, target) | Moves + refreshes |
| readFile(path) | Delegates to FS |
| createIdea(folderName, content) | Creates + refreshes |
| listRules() | Delegates to FS |
| writeFile(path, content) | Delegates to FS |
| articlesForStage(stage) | Returns list for stage |
| totalArticles | Sum of all articles |

---

## 6. Screens

### DashboardScreen (main entry)

**Layout:** Scaffold with AppBar + body
**AppBar:** Newspaper icon + "PressRoom" title + article count + "+ New Idea" button (purple) + Rules icon (menu_book) + Refresh icon
**Body:** Error bar (red, shown when error != null) + 6 Expanded StageColumns in a Row

**Navigation:**
- Card tap → ArticleDetailScreen
- Card 3-dot menu → Produce → ProduceScreen
- Card 3-dot menu → Move Next/Prev → direct move via notifier
- "+ New Idea" button → IdeaEditorScreen
- Rules icon → RulesScreen
- Drag & Drop → direct move via notifier

**Action Handler:** Receives `ArticleAction` enum (produce, moveNext, movePrev) from ArticleCard popup menu.

### ArticleDetailScreen

**Layout:** Two-panel (Row)
- **Left panel (280px):** Info panel (prefix badge, subtitle, track, mood, location, created, completeness indicator, tags, platform badges) + Move buttons + File list (ListView)
- **Right panel (Expanded):** FileViewer showing selected file content

**Behavior:**
- Auto-selects first readable file on open (skips images: .jpg, .jpeg, .png, .svg)
- Move buttons use confirmation dialog
- After move, pops back to dashboard

### IdeaEditorScreen

**Layout:** SingleChildScrollView with 600px wide form
**Fields:**
- Title (TextField, autofocus)
- Track (ChoiceChips: deep-tech, clarity, security, tech)
- Notes (TextField, 12 lines)

**Save Logic:**
- Folder name = title slugified (strip special chars, spaces to hyphens)
- Creates folder in 10-ideas/ with notes.md containing title, track, and notes as Markdown
- Returns true on success (triggers dashboard refresh)

### ProduceScreen

**Layout:** Two-panel (Row)
- **Left panel (360px):**
  - ARTICLE NOTES section: Markdown-rendered notes.md from article folder
  - DELIVERABLES section: Checklist of 11 expected files with green checkmark (exists) or grey circle (missing)
- **Right panel (Expanded):**
  - PRODUCTION RULES section: FilterChip tabs for each rule file, Markdown-rendered content below

**Button:** "Move to Produce" (if article is in Ideas stage) or "In Production" label

### RulesScreen

**Layout:** Two-panel (Row)
- **Left panel (260px):** ListTile for each rule file, selected state with indigo highlight
- **Right panel (Expanded):** Markdown rendering (view mode) or TextField (edit mode)

**Edit Mode:** Toggle via edit icon in AppBar. Save button writes file, shows SnackBar confirmation.

---

## 7. Widgets

### ArticleCard

**Content:** Prefix badge (colored) + 3-dot PopupMenu OR file count + Title (2 lines, ellipsis) + Track badge (color-coded) + Completeness bar

**3-Dot Menu (PopupMenuButton\<ArticleAction\>):**
- "Produce" (rocket icon) -- shown for Ideas + Produce stages only
- "Move to [next stage]" (arrow forward) -- if next exists
- "Move to [prev stage]" (arrow back) -- if previous exists

**Track Badge Colors:** deep-tech=#2196F3, clarity=#FFC107, security=#F44336, tech=#00BCD4

### StageColumn

**Wraps DragTarget\<Article\>:** Accepts articles from other stages (rejects same-stage drops)
**Visual feedback:** Brighter background + thicker colored border when hovering with draggable
**Empty state:** "Drop here" when hovering, "Empty" otherwise

**Each article wrapped in Draggable\<Article\>:**
- feedback: 200px wide, 85% opacity ArticleCard
- childWhenDragging: 30% opacity ArticleCard
- child: Full ArticleCard with onTap + onAction

### FileViewer

**Header:** Grey bar with monospace filename
**Content:**
- `.md` files → flutter_markdown Markdown widget with custom dark theme stylesheet
- Other files → SelectableText (monospace for .json, .html, .svg, .sh)

**Markdown StyleSheet:** Custom dark theme -- grey[300] text, grey[100-200] headings, amber[200] inline code, grey[850] code blocks, grey[600] blockquote border, blue links (#448AFF)

### CompletenessIndicator

Linear progress bar (stage color foreground, 20% alpha background) + percentage text

### MoveButtons

Conditional Prev/Next buttons with confirmation AlertDialog. OutlinedButton for previous, FilledButton for next.

---

## 8. Theme

**Material 3 Dark Theme:**

| Property | Value |
|----------|-------|
| Seed color | Colors.indigo |
| Brightness | Brightness.dark |
| scaffoldBackgroundColor | #121212 |
| Card color | #1E1E1E |
| Card elevation | 0 |
| AppBar backgroundColor | #1A1A1A |
| AppBar elevation | 0 |
| AppBar scrolledUnderElevation | 0 |
| Divider color | Colors.grey[800] |
| Divider thickness | 1 |
| Debug banner | false |

---

## 9. Configuration

**config.dart:**
```dart
class Config {
  static const String contentRoot = '/Users/christianmoser/ChrisBuilds64/content';
  static const String contentFlowPath = '$contentRoot/flow';
  static const String contentRulesPath = '$contentRoot/rules';
}

class StageColors {
  static const ideas = Color(0xFF7C4DFF);
  static const produce = Color(0xFF448AFF);
  static const review = Color(0xFFFF9800);
  static const reviewHuman = Color(0xFFFF5722);
  static const readyToPublish = Color(0xFF4CAF50);
  static const published = Color(0xFF78909C);
}
```

---

## 10. Evaluation

**Acceptance Criteria:**

- [x] App starts, shows Kanban board with 6 columns
- [x] All articles from content/flow/ correctly assigned to stages
- [x] Articles without meta.json display correctly (fallback to folder name)
- [x] Detail view shows file list + file content
- [x] Move button physically relocates folder + refreshes board
- [x] Completeness bar shows correct progress (11 deliverables)
- [x] Markdown files rendered with styled flutter_markdown
- [x] Idea Editor creates folder + source.md in 10-ideas/
- [x] Drag & drop moves articles between stages with visual feedback
- [x] 3-dot menu with Produce, Move Next, Move Prev actions
- [x] Produce screen shows notes + deliverables checklist + rules reference
- [x] Rules screen lists all rule files with Markdown rendering + edit mode
- [ ] App logo (DALL-E generated, pending)

---

## 11. Deployment

**Environment:** Local, macOS Desktop
**Location:** `develop/apps/pressroom/`
**Start:** `cd develop/apps/pressroom && flutter run -d macos`
**Build:** `flutter build macos`

**Setup from scratch:**
```bash
cd develop/apps
flutter create --platforms=macos pressroom
cd pressroom
# Remove unnecessary platforms (android, ios, linux, web, windows)
# Add flutter_markdown to pubspec.yaml
flutter pub get
# Disable macOS sandbox in both entitlements files
# Set window size in MainFlutterWindow.swift
# Implement all files per project structure above
flutter run -d macos
```

---

## 12. Sprint History

### Sprint 1 (2026-02-13) -- DONE
- Flutter project creation (macOS only)
- Models: PipelineStage, Article, ArticleMeta
- Services: FilesystemService, PipelineNotifier
- Widgets: ArticleCard, StageColumn, CompletenessIndicator, FileViewer, MoveButtons
- Screens: DashboardScreen (Kanban), ArticleDetailScreen
- Dark theme, Material 3, 1400x800 window
- macOS sandbox disabled

### Sprint 2 (2026-02-14) -- DONE
- flutter_markdown dependency + Markdown rendering in FileViewer
- IdeaEditorScreen (form → saves to 10-ideas/)
- Drag & Drop between Kanban columns (Draggable + DragTarget)
- 3-dot PopupMenu on ArticleCard (Produce, Move Next, Move Prev)
- ProduceScreen (article notes + deliverables checklist + rules reference)
- RulesScreen (view + edit content/rules/ files with Markdown rendering)
- Rules button in AppBar
- config.dart extended with contentRulesPath
- FilesystemService extended with listRules(), writeFile()
- PipelineNotifier extended with createIdea(), listRules(), writeFile()

### Sprint 3 (planned)
- App logo integration
- Keyboard shortcuts
- Integration with UC-AG-002 agents (trigger, status)

---

## 13. Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-13 | Name: PressRoom | Newsroom vibe, content creator connection |
| 2026-02-13 | No SQLite, filesystem only | ~40 articles, scan <100ms, KISS |
| 2026-02-13 | ChangeNotifier (no Provider/Riverpod) | Flutter built-in, 0 dependencies |
| 2026-02-13 | macOS only | Personal tool, no App Store |
| 2026-02-13 | No content editing in UI | VS Code remains editor, PressRoom = cockpit |
| 2026-02-14 | flutter_markdown as only external dep | Markdown rendering essential for .md files |
| 2026-02-14 | Rules editable in-app | Production guidelines must be accessible during workflow |
| 2026-02-14 | 3-dot menu over swipe gestures | Desktop UX, extensible for future actions |
| 2026-02-14 | ProduceScreen = notes + rules + checklist | All context needed for production in one view |
