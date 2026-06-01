# File Manager — Full Technical Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Module-Level Constants and Global State](#3-module-level-constants-and-global-state)
4. [Theming System](#4-theming-system)
5. [Icon System](#5-icon-system)
6. [Persistence Layer](#6-persistence-layer)
7. [Data Model Layer](#7-data-model-layer)
8. [Delegate Classes](#8-delegate-classes)
9. [View Widgets](#9-view-widgets)
10. [UI Component Widgets](#10-ui-component-widgets)
11. [Dialog Classes](#11-dialog-classes)
12. [Background Worker Classes](#12-background-worker-classes)
13. [TabPane — The Core Browser Pane](#13-tabpane--the-core-browser-pane)
14. [FileExplorer — The Main Window](#14-fileexplorer--the-main-window)
15. [Terminal Subsystem](#15-terminal-subsystem)
16. [Signal Map](#16-signal-map)
17. [Keyboard Shortcuts Reference](#17-keyboard-shortcuts-reference)
18. [Persistence Files Reference](#18-persistence-files-reference)
19. [External Tool Dependencies](#19-external-tool-dependencies)
20. [Application Entry Point](#20-application-entry-point)

---

## 1. Project Overview

A fully-featured desktop **file manager** for Linux, built entirely in Python using **PyQt6**. It replicates the Windows 11 Fluent Design language faithfully, including both light and dark themes sourced from official WinUI 3 design tokens. The entire application is a single self-contained file (~7,700 lines) with no external Python dependencies beyond PyQt6.

**Feature summary:**
- Multi-tab browsing with per-tab navigation history
- List (detail) view and icon/grid view, togglable per folder
- Automatic icon-view switch for media-heavy folders
- Real image thumbnails in icon view (loaded asynchronously)
- Video thumbnail generation via `ffmpeg`
- Breadcrumb address bar with chevron dropdown menus
- Sidebar: pinned folders, Quick Access (favorites), detected drives, Trash
- Search: live proxy filter and recursive deep search via `find`
- Full file operations: copy, cut, paste, rename, delete (to Trash), permanent delete, new folder, new file, compress
- Trash management: view, restore, empty
- Drive management: auto-mount removable devices via `udisksctl`, unmount, properties
- Built-in VT100 terminal emulator (PTY-based)
- Light/dark theme toggle, persisted across sessions
- Per-folder view-mode memory
- FreeDesktop Trash spec compliant
- "Open With" dialog parsing installed `.desktop` files

---

## 2. Architecture Diagram

```
main()
 └── QApplication (Fusion style + Win11 palette + QSS)
      └── FileExplorer (QMainWindow, frameless)
           ├── _PlusTabBar (visible custom tab bar in title row)
           ├── _WinCtrlButton x3 (min/max/close, painted)
           ├── Nav bar QWidget
           │    ├── back / forward / up QToolButtons
           │    ├── favorite star QToolButton
           │    ├── address bar container  ← active BreadcrumbBar reparented here
           │    ├── SearchBar
           │    └── theme toggle QToolButton
           ├── QTabWidget (hidden pane container)
           │    └── TabPane x N  (one per browser tab)
           │         ├── BreadcrumbBar (hidden until active tab)
           │         ├── Command bar QWidget
           │         │    └── QPushButton x12 (new folder/file, cut/copy/paste,
           │         │                         rename, delete, sort, view mode,
           │         │                         empty trash, restore, details)
           │         ├── QSplitter (horizontal)
           │         │    ├── SidebarWidget
           │         │    │    ├── Pinned folder buttons
           │         │    │    ├── Quick Access (favorites) buttons
           │         │    │    ├── Devices & Drives buttons (polled every 2s)
           │         │    │    └── Trash button
           │         │    ├── QStackedWidget
           │         │    │    ├── FileView (QTreeView) — list mode
           │         │    │    └── IconFileView (QListView) — icon mode
           │         │    └── Details panel QWidget (collapsible)
           │         └── Background workers (QThread x up to 5 per tab)
           └── _TerminalPanel (vertical QSplitter, toggled Ctrl+`)
                ├── Header bar (Clear, Close, expand hint)
                └── _TerminalView (QPlainTextEdit + PTY + _VTScreen)
```

---

## 3. Module-Level Constants and Global State

### File path constants

| Constant | Value | Purpose |
|---|---|---|
| `HOME` | `os.path.expanduser("~")` | Default start path |
| `TRASH_PATH` | `~/.local/share/Trash/files` | FreeDesktop Trash files dir |
| `RECENT_JSON` | `~/.local/share/file_explorer_recent.json` | Recent files store |
| `FAVORITES_JSON` | `~/.local/share/file_explorer_favorites.json` | Favorites store |
| `VIEW_PREFS_JSON` | `~/.local/share/file_explorer_view_prefs.json` | Per-folder view mode |
| `THEME_JSON` | `~/.local/share/file_explorer_theme.json` | Light/dark setting |
| `RECENT_SENTINEL` | `"__RECENT__"` | Signals "show recent view" in history/navigation |
| `MAX_RECENT` | `50` | Maximum recent files entries |
| `THUMB_SIZE` | `96` | Icon-view thumbnail pixel size |

### Extension sets and icon maps

`_IMAGE_EXTS` — set of lowercase image extensions (`.jpg`, `.png`, `.svg`, `.webp`, etc.)

`_VIDEO_EXTS` — set of lowercase video extensions (`.mp4`, `.mkv`, `.avi`, etc.)

`EXT_ICON_MAP` — `dict[extension → XDG theme icon name]` covering images, video, audio, documents, code files, archives, and executables. Used as the first lookup step in `resolve_icon`.

`GENERIC_FALLBACKS` — list of `(mime_prefix, icon_name)` pairs. Used when the extension is not in `EXT_ICON_MAP` but the MIME category is known.

`PINNED` — static list of `(label, path)` pairs for the sidebar pinned section (Home, Desktop, Documents, Downloads, Music, Pictures, Videos).

`DESKTOP_DIRS` — XDG application directories scanned for `.desktop` files (`/usr/share/applications`, `~/.local/share/applications`).

### Global caches and registries

`_icon_cache: dict[str, QIcon]` — icons keyed by file extension; computed once and never evicted. Shared across all tabs.

`_thumb_cache: dict[str, QPixmap]` — image thumbnails keyed by absolute path; populated by `IconThumbWorker`; survives tab switches and folder navigations.

`_icon_provider: QFileIconProvider` — singleton, used for OS icon theme lookups as a fallback in `resolve_icon`.

`_live_threads: set` — global registry keeping `QThread` objects alive until their OS thread has fully exited. Prevents "QThread destroyed while running" crashes. Threads add themselves before start and remove via a `finished` signal lambda.

`_PALETTE16` — 16-entry list of hex color strings defining the standard xterm color palette (indices 0–15), used by the terminal emulator.

---

## 4. Theming System

### Stylesheets: `WIN11_LIGHT_QSS` / `WIN11_DARK_QSS`

Two large multi-section Qt Stylesheet strings. Color values are sourced directly from the official WinUI 3 `themeresources.xaml` and Fluent 2 design token documentation. Opacity variants (e.g. `rgba(0,0,0,0.0578)`) are pre-resolved to their opaque equivalents against the relevant surface color, so Qt stylesheets can use them without alpha compositing surprises.

Sections covered by both stylesheets:

- Global `QWidget` reset — font stack: "Segoe UI Variable Text" → "Segoe UI" → system-ui → sans-serif; selection colors; no borders/outlines by default.
- `QMainWindow` and `QMainWindow::separator`
- `QWidget#navBar` and its `QToolButton` states (hover, pressed, disabled)
- `QToolBar` and its `QToolButton` states
- `QWidget#titleBar` and `QLabel#titleLabel`
- `QToolButton#winMin`, `#winMax` (standard hover), `QToolButton#winClose` (red hover `#C42B1C`)
- `QTabWidget::pane` and `QTabBar` — tabs with 2px bottom-border indicator (accent blue `#0078D4` when selected)
- `QWidget#commandBar` — buttons, separators, checked state
- `QSplitter::handle` variants
- `QWidget#sidebar` — section labels, navigation buttons, hover/pressed states
- `QScrollBar` — 6px thin, handle-only, no arrows
- `QTreeView` — item height 32px, selection colors `#CCE4F7` / `#E0EEFA`, alternate row same as base
- `QHeaderView` sections with hover
- `QWidget#crumbPage` — breadcrumb container and its `QPushButton` crumbs
- `QLineEdit` — 2px blue border when focused
- `QMenu` — 8px border radius, separator, disabled item color, checked indicator
- `QDialog`, `QDialogButtonBox` — accent-blue default button
- `QMessageBox`
- `QWidget#searchBar` — with `[active="true"]` property variant for blue border
- `QInputDialog`
- `QListWidget` — used by OpenWithDialog
- `QWidget#detailsPanel`
- `QToolTip`

### Palette functions

**`_apply_win11_palette(app)`** and **`_apply_win11_dark_palette(app)`** set `QPalette.ColorRole` entries for the entire application. This ensures native Qt widgets that read the palette rather than QSS (e.g. `QMessageBox`, `QAbstractItemView` selection colors) match the theme. Roles set include Window, WindowText, Base, AlternateBase, ToolTipBase/Text, Text, BrightText, PlaceholderText, Button, ButtonText, Highlight, HighlightedText, Mid, Midlight, Dark, Shadow, Light, and their Disabled group equivalents.

### Theme toggle

`FileExplorer._toggle_theme()`:
1. Flips `self._dark_mode`.
2. Applies the matching palette function on `QApplication.instance()`.
3. Swaps the application stylesheet.
4. Calls `refresh_icons()` on each tab pane's command bar and sidebar (re-renders palette-dependent icons since `_cmd_icon` uses `palette(WindowText)` for ink color).
5. Persists to `THEME_JSON` via `_save_theme()`.

`_load_theme()` reads `THEME_JSON` at startup and defaults to light mode on any read error.

---

## 5. Icon System

All icons are `QIcon` objects backed by `QPixmap`s painted at runtime with `QPainter`. No image assets are bundled with the application.

### 5.1 Built-in file-type icons

`_doc_base(painter, pixmap, size, body_color, fold_color)` is a shared helper that draws the common document body: a rounded rectangle with a folded top-right corner and a faint crease line. Returns `(m, w, h, fold)` measurements so subclasses can add badge content on top.

| Function | Visual |
|---|---|
| `_make_folder_icon(size)` | Two-tone flat folder: dark-gold back panel + tab, lighter-gold front panel |
| `_make_generic_file_icon(size)` | White document body with two grey content lines |
| `_make_pdf_icon(size)` | White document + red rounded pill badge labelled "PDF" |
| `_make_image_icon(size)` | White document + light-blue thumbnail area with mountain/sun landscape |
| `_make_video_icon(size)` | White document + indigo circle with white play triangle |
| `_make_iso_icon(size)` | White document + grey radial-gradient disc with center hole |
| `_make_audio_icon(size)` | White document + teal music note |
| `_make_archive_icon(size)` | White document + stacked horizontal layer stripes |
| `_make_code_icon(size)` | White document + `</>` glyph in indigo |
| `_make_text_icon(size)` | White document + three horizontal grey lines |

### 5.2 `resolve_icon(path, is_dir)` — the central resolver

Resolution chain (first non-null result wins; result cached by extension):

1. Return `_icon_cache[ext]` immediately if already resolved.
2. Directory: return `_make_folder_icon()`.
3. Extension in `EXT_ICON_MAP`: try `QIcon.fromTheme(xdg_name)`. If null, try `GENERIC_FALLBACKS` chain.
4. `QFileIconProvider.icon(QFileInfo(path))` — OS icon theme lookup.
5. Last resort: `_make_generic_file_icon()` — always non-null.

### 5.3 `_sidebar_icon(label)` — sidebar navigation icons

Returns a 16×16 `QIcon` painted in accent blue `#0078D4`. Palette-aware: uses `palette(Window)` for cutout fills so icons look correct in both themes.

| Label | Shape |
|---|---|
| Home | Solid house with white door cutout |
| Desktop | Monitor outline with stand and base |
| Documents | Doc outline with fold corner and two text lines |
| Downloads | Down-arrow with tray |
| Music | Music note (oval head, stem, flag) |
| Pictures | Framed landscape (mountain silhouette + sun circle) |
| Videos | Rounded rect outline + solid play triangle |
| Recent | Clock face with hour and minute hands |
| Trash | Bin outline with lid, handle, trapezoid body, two stripes |
| *(fallback)* | Folder outline with tab |

### 5.4 `_cmd_icon(key, ink)` — command bar icons

Returns a 16×16 `QIcon` painted with `ink` (defaults to `palette(WindowText)`, so automatically adapts to light/dark). All shapes use 1.4px strokes with round caps/joins unless noted.

| Key | Shape |
|---|---|
| `new_folder` | Folder outline + blue rounded `+` badge overlay |
| `new_file` | Document outline with fold + blue `+` badge overlay |
| `cut` | Scissors — two circles (handles) + crossing blade lines |
| `copy` | Two overlapping page outlines (back + front, front has window-color fill) |
| `paste` | Clipboard outline with clip tab + two content lines |
| `rename` | Pencil — diagonal body path + eraser crossline |
| `delete` | Trash bin — lid line, handle, trapezoid body, two stripes |
| `sort` | Three horizontal lines of decreasing width |
| `details` | Three equal horizontal lines |
| `icon_view` | 2×2 grid of filled rounded squares |
| `list_view` | Three small icon squares + three horizontal text lines |
| `restore` | Curved undo arrow with filled arrowhead |
| `pin_add` | Filled gold 5-point star with dark outline |
| `pin_remove` | Muted grey outline star (unfilled) |

### 5.5 `FileExplorer._make_nav_icon(kind, size, normal_color, disabled_color)`

Paints back/forward/up arrows as filled `QPolygonF` arrow-with-shaft shapes. Produces a `QIcon` with both Normal and Disabled pixmaps so Qt automatically greys them when the corresponding `QAction` is disabled.

### 5.6 `SidebarWidget._drive_icon(is_removable)`

Paints a 16×16 drive icon. USB stick shape (body + connector nub + highlight slots) for removable drives; hard-drive cylinder shape (rounded rect body + platter dot + slot line) for fixed drives.

### 5.7 Fluent font helpers

`_fluent_font(size)` — returns a `QFont` with family list `["Segoe Fluent Icons", "Segoe MDL2 Assets", "Segoe UI Symbol"]`. Degrades gracefully on Linux where these Windows fonts are typically absent.

`_apply_fluent_icon(widget, icon_cp, label, icon_size)` — sets widget text to `"{glyph}  {label}"` and applies the fluent font.

---

## 6. Persistence Layer

### `RecentFiles`

Backed by `RECENT_JSON` as a JSON array of absolute path strings. On load, entries that no longer exist on disk are silently discarded. `add(path)` moves the path to the front of the list and trims to `MAX_RECENT = 50` entries before saving. `entries()` returns a copy.

### `Favorites`

Backed by `FAVORITES_JSON` as a JSON array. Non-existent paths are discarded on load. `add(path)` / `remove(path)` modify and save. `contains(path)` is a membership test. `entries()` returns a copy.

### View preferences

`VIEW_PREFS_JSON` stores a `dict[abs_path → "list" | "icons"]`. Each `TabPane` loads this on construction via `_load_view_prefs()`. `_save_view_prefs()` serializes the entire dict on every view-mode toggle. `_apply_view_pref(path)` switches the current tab to the remembered mode when navigating to a known path.

### Theme setting

`THEME_JSON` stores `{"dark": true/false}`. Read at startup by `FileExplorer._load_theme()`; written by `_save_theme()` on every toggle.

---

## 7. Data Model Layer

### `QFileSystemModel`

Each `TabPane` creates one `QFileSystemModel` rooted at `/`. Rooting at `/` is intentional: it means the model watches the entire filesystem, so navigating between directories does not require re-rooting (which would reset the `Hidden` file filter). The model's `setFilter` includes `QDir.Filter.Hidden` so `~/.local/share/Trash` is always indexed — navigating to Trash relies on this being pre-indexed.

### `GroupByTypeProxy(QSortFilterProxyModel)`

Wraps `QFileSystemModel` and adds four behaviors.

**Group-by-type sorting.** `lessThan(left, right)` is overridden so directories always precede files. Within files, items are sorted by a type-class integer: images → 1, videos → 2, audio → 3, archives → 4, code → 5, documents → 6, everything else → 7. Within each class, the configured sort column and order applies. Toggled by `set_grouping(bool)` which calls `invalidate()`.

**Hidden file filter.** `filterAcceptsRow` hides entries whose filename starts with `.` when `_show_hidden` is False. Exception: any path that is an ancestor of `TRASH_PATH` is always shown, ensuring the Trash is always navigable regardless of the hidden-files setting.

**Inline search filter.** When `_search` is non-empty, `filterAcceptsRow` also checks whether the filename contains the query (case-insensitive). This is the fast in-directory filter; deep recursive search uses `SearchResultModel` instead.

**Date column formatting.** `data()` overrides column 3 (date modified) to return a 24-hour formatted string regardless of the system locale.

**Rename support.** `flags()` adds `Qt.ItemFlag.ItemIsEditable` to column 0.

### `RecentModel(QAbstractTableModel)`

A flat 4-column table (Name / Size / Type / Date Modified). `_build(entries)` calls `os.stat()` on each path to compute size and date. Column 4 (index 4 of the internal tuple, never displayed) holds the full path and is returned as `Qt.ItemDataRole.UserRole`. `filepath(row)` provides direct path access. Icons are resolved via `resolve_icon`. Instantiated fresh on every "show recent view" call to pick up any new additions.

### `SearchResultModel(QAbstractTableModel)`

A streamable 4-column table (Name / Location / Size / Date Modified). `append_paths(paths)` uses `beginInsertRows` / `endInsertRows` so the view updates in real time as batches arrive from `SearchWorker`. Column 0 returns the resolved icon. `Qt.ItemDataRole.UserRole` returns the full path. `filepath(row)` provides direct access.

---

## 8. Delegate Classes

### `IconDelegate(QStyledItemDelegate)`

Used in `FileView` (list mode). Only customizes column 0; other columns fall through to the default delegate.

**Why `paint()` is fully overridden**: on many Qt6 builds, `QFileSystemModel` re-fetches its own icon from the model inside `QStyle.drawControl(CE_ItemViewItem)`, silently overwriting any icon set in `initStyleOption`. `IconDelegate` drives the entire paint pass itself by calling `super().paint(painter, opt, index)` with an `opt` that already has the resolved icon installed — this is the only reliable approach.

**Inline rename editor** (`createEditor` / `setEditorData` / `setModelData` / `destroyEditor`):

`createEditor` marks the `QLineEdit` with `_committed = False`. `setEditorData` strips the file extension from the initial selection — files show only the stem highlighted (cursor lands before the dot), directories select the full name. `setModelData` calls `os.rename()`. If the target name already exists, `_unique_path()` appends `(1)`, `(2)`, … until a free name is found. An empty name causes the placeholder file/folder to be deleted. `destroyEditor` checks `_committed`: if False (user pressed Escape) and the item is a "New Folder" / "New File" placeholder (empty or zero bytes, matching the generated default name), it is deleted via `os.rmdir` or `os.remove`.

### `ImagePreviewDelegate(IconDelegate)`

Used in `IconFileView` (icon/grid mode). Inherits `IconDelegate`. Overrides `paint()` to render actual image thumbnails when the path's pixmap is in `_thumb_cache`.

Paint sequence for cached images:
1. Let the style draw the item background (hover/selection state) with the icon cleared to avoid double-drawing.
2. Fetch from `_thumb_cache`, scale to the decoration rect keeping aspect ratio with smooth transformation.
3. Draw a 1px offset drop shadow (alpha 35) at the pixmap position.
4. Apply a rounded clipping mask (4px corner radius) and draw the pixmap.
5. Draw a thin border (alpha 25) over the pixmap edges.
6. Draw the elided filename label centered below the thumbnail.

Falls back to `IconDelegate.paint()` for non-image files or cache misses.

---

## 9. View Widgets

### `FileView(QTreeView)`

Custom signals emitted:

| Signal | Trigger |
|---|---|
| `go_up` | Double-click on empty viewport area |
| `open_current` | Enter/Return key (not while editing) |
| `delete_sel` | Delete key |
| `perm_delete_sel` | Shift+Delete |
| `cut_sel` | Ctrl+X |
| `copy_sel` | Ctrl+C |
| `paste_sel` | Ctrl+V |
| `refresh_req` | Ctrl+R |
| `new_folder_req` | Ctrl+N |
| `new_file_req` | Ctrl+F |

**Icon-area drag detection.** `mousePressEvent` records the start position and whether the click landed in the leftmost 22px of a column-0 item (`_ICON_W = 22`). `mouseMoveEvent` starts a drag if the mouse travels ≥8px from the start. `_start_icon_drag` collects selected items, builds `QMimeData` with `file://` URIs, uses the first selected item's 32×32 icon as the drag pixmap, and calls `drag.exec()` with Copy+Move actions.

**Viewport event filter** (installed on `self.viewport()`): converts `MouseButtonDblClick` on an invalid index into `go_up`.

**F2** calls `self.edit(name_idx)` to start `IconDelegate`'s inline rename.

### `IconFileView(QListView)`

Identical signal set and keyboard handler to `FileView`. Uses `QListView.IconMode` with 110×110 grid, 60×60 icon size, `ResizeMode.Adjust`, uniform item sizes, word-wrap enabled. The viewport event filter provides the same double-click-to-go-up behavior.

A separate `ImagePreviewDelegate` instance is mandatory — sharing one delegate between two views causes Qt to raise "commitData called with an editor that does not belong to this view".

---

## 10. UI Component Widgets

### `BreadcrumbBar(QStackedWidget)`

**Page 0 — crumb view** (`QWidget#crumbPage`).

`_rebuild_crumbs(path)` splits the path into `(label, full_path)` pairs from filesystem root to the current directory, then inserts alternating crumb `QPushButton`s and `›` chevron `QPushButton`s into `_crumb_layout`. Clicking a crumb emits `navigate(full_path)`. Clicking a chevron calls `_show_chevron_menu(parent_path, button)`: uses `os.scandir` to list immediate subdirectories, builds a `QMenu` with a folder icon per entry, positioned below the chevron via `button.mapToGlobal(rect.bottomLeft())`. Clicking blank bar area calls `_enter_edit_mode()`.

Non-filesystem labels (e.g. "Recent Files") are displayed as a single disabled `QPushButton`.

**Page 1 — edit view** (`QLineEdit`).

Pre-filled with `_current_path`. Enter triggers `_commit_edit()`: `os.path.expanduser`, validates `os.path.isdir`, emits `navigate`, rebuilds crumbs. Escape or focus-out triggers `_cancel_edit()`: restores previous crumbs silently. Event filter on `_edit` catches `QEvent.Type.KeyPress` (Escape) and `QEvent.Type.FocusOut`.

**Signal:** `navigate(str)`.

### `SearchBar(QWidget)`

Contains a painted magnifier-icon `QPushButton` (acts as label), a `QLineEdit`, and a `×` clear button that is only visible when the field has content.

**Debouncing.** `textChanged` restarts a 150ms single-shot `QTimer`. When the timer fires it emits `search_changed(text)`. `returnPressed` stops the timer and emits immediately.

**Active border.** Toggles a `"active"` dynamic property and calls `style().unpolish()/polish()` to force re-evaluation of the `QWidget#searchBar[active="true"]` QSS rule.

**Signals:** `search_changed(str)`, `search_cleared()`.

### `SidebarWidget(QWidget)`

Fixed 210px wide. Contents scroll inside a `QScrollArea` with no horizontal scrollbar.

**Pinned folders** (static): buttons for Home, Desktop, Documents, Downloads, Music, Pictures, Videos, Recent. Only added if the directory exists. Each uses `_sidebar_icon(label)`.

**Quick Access** (dynamic): `_qa_container` holds a `QVBoxLayout` rebuilt by `_rebuild_favorites()`. Section header hidden when empty. Each favorite button has a right-click context menu offering "Remove from Quick Access".

**Devices & Drives** (polled every 2s):

`_refresh_devices()` runs on a `QTimer`:
- Reads `/sys/block/{disk}/removable` to find removable block devices. Checks `/proc/mounts` to identify unmounted ones. For devices not in `_mount_attempted` and not in `_ejected`, calls `_udisks_mount(device)` (fire-and-forget `udisksctl mount --block-device {dev} --no-user-interaction`). `_mount_attempted` prevents repeated calls; `_ejected` prevents remounting manually ejected devices. Both sets are cleared when a device physically disappears.
- Iterates `QStorageInfo.mountedVolumes()`, filters system mounts (`/`, `/boot`, tmpfs, squashfs, overlay, snap, etc.), compares against `_known_volumes`. If changed, clears and rebuilds drive buttons.
- Each drive button shows `{name}  ({size} GB)` with a painted drive icon. Right-click offers "Unmount" and "Properties".

`_do_unmount(root)`: resolves the block device via `_mount_point_to_device` (reads `/proc/mounts`), adds device to `_ejected`, calls `udisksctl unmount --block-device {dev}`.

**Trash** (always shown at the bottom): navigates to `TRASH_PATH`.

**Signals:** `navigate(str)` (path or `RECENT_SENTINEL`), `unmount_requested(str)` (mount root path).

### `_PlusTabBar(QTabBar)`

Overrides Qt's default tab bar for the title-row custom look.

**Painted `×` close buttons.** `paintEvent` draws a 16×16 close button at the right edge of each tab. `_close_rects` maps tab index to its `QRect`. On hover, a rounded background pill is drawn. `mousePressEvent` / `mouseReleaseEvent` intercept clicks inside these rects and emit `tabCloseRequested`. `tabCloseRequested` is connected to `FileExplorer._close_tab`.

**`+` new-tab button.** Painted immediately after the last tab. Click emits `new_tab_requested`, connected to `FileExplorer.new_tab(HOME)`.

**Window drag.** Clicking empty area (right of the `+` button) calls `mw.windowHandle().startSystemMove()` for native OS move. If the window is maximized, it is first un-maximized.

**Mouse tracking** enabled so hover effects repaint without a click.

All tabs are fixed 170px wide (`tabSizeHint` override). `setTabsClosable(False)` suppresses Qt's built-in close button.

### `_WinCtrlButton(QToolButton)`

Custom min/max/close buttons. Fixed 46×36px, no text. `paintEvent`:
1. Draws background via `style().drawPrimitive(PE_Widget)` so QSS hover/pressed colors from `QToolButton#winMin:hover` etc. are applied.
2. Picks ink color from `palette(WindowText)`.
3. Paints the glyph: `—` dash (min), hollow `□` square (max), `×` cross (close). All with 1px round-cap strokes.

---

## 11. Dialog Classes

### `OpenWithDialog(QDialog)`

**Construction.** Calls `_parse_desktop_files()` which scans all `.desktop` files in `DESKTOP_DIRS` using `configparser.RawConfigParser`. Only `Type=Application` entries without `NoDisplay=true` are included. MIME types are parsed from the semicolon-separated `MimeType` field. Entries are sorted by name.

**MIME detection.** `_get_mime(path)` first tries `xdg-mime query filetype {path}` (2s timeout via `subprocess`), falls back to Python's `mimetypes.guess_type`.

**App matching.** `_apps_for_mime(mime, all_apps)` matches apps where `MimeType` contains the exact MIME or the wildcard `{category}/*`.

**UI.** File label, search `QLineEdit` to filter apps, `QListWidget` with app icons and names, Cancel / Make Default / Open buttons. Double-click or "Open" accepts. "Make Default" calls `xdg-mime default {desktop_file} {mime_type}` via subprocess.

**Launch.** `_clean_exec(cmd)` strips `%f`, `%F`, `%u`, `%U`, and all other field codes from the `Exec` string. `_launch_app(exec_cmd, file_path)` runs `subprocess.Popen(f'{cmd} "{path}"', shell=True)`.

### `PropertiesDialog(QDialog)`

Simple single-file properties modal (`QFormLayout`). Calls `os.stat()` for size and modification date. For directories, `_dir_size(path)` walks the entire tree with `os.walk` and sums file sizes (blocking; acceptable since it's user-triggered).

### `DrivePropertiesDialog(QDialog)`

Displays: device path, mount point, filesystem type, total/used/free sizes, and a capacity bar. Bar turns red (`#C42B1C`) when usage exceeds 90%. Built from `QStorageInfo` data passed in by `SidebarWidget._show_drive_properties`.

---

## 12. Background Worker Classes

All workers are `QObject` subclasses moved to a dedicated `QThread` via `worker.moveToThread(thread)`. They communicate back to the main thread exclusively through Qt signals — no UI objects are touched from worker threads.

### `FolderScanWorker`

**Purpose.** Determine whether a newly navigated folder is "pure media" to decide whether to auto-switch to icon view.

**Algorithm.** Iterates `os.scandir(path)` up to `MAX_SAMPLE = 200` files. If any non-media file is found, emits `finished(path, False)` immediately (early exit). If all sampled files are images or videos and there are at least `MEDIA_MIN = 3` such files, emits `finished(path, True)`.

**Cancellation.** `_cancelled` flag checked between entries.

**Signal:** `finished(str path, bool is_media)`.

### `ThumbnailWorker`

**Purpose.** Generate a single video frame thumbnail for the details panel.

**Algorithm.**
1. `ffprobe -show_entries format=duration` to get video length (5s timeout).
2. Compute seek time = `max(0, duration * 0.10)`.
3. `ffmpeg -ss {seek} -i {path} -frames:v 1 -vf scale:{max}:{max}:force_original_aspect_ratio=decrease {tmpfile}` (10s timeout).
4. Load the JPEG temp file as `QPixmap`.
5. Delete the temp file unconditionally.

Returns `None` on any error or if ffmpeg/ffprobe is not installed.

**Signal:** `finished(str path, object pixmap_or_None)`.

### `IconThumbWorker`

**Purpose.** Batch-load image thumbnails for all image files in the current icon-view folder.

**Algorithm.** For each path in `_paths`: skip if in `_thumb_cache`; skip non-image or `.svg`. Use `QImageReader` with `setScaledSize()` (scales at decode time, avoiding loading multi-megabyte originals into memory). Scale result to `THUMB_SIZE × THUMB_SIZE` with smooth transformation. Store in `_thumb_cache` and emit `ready(path, pixmap)`. SVG files require `QSvgRenderer` on the main thread and are handled separately.

**Cancellation.** `_cancelled` flag checked between files.

**Signal:** `ready(str path, object pixmap)`.

### `DetailsWorker`

**Purpose.** Count the direct children of a folder for the details panel "Contents" row.

**Algorithm.** `len(os.listdir(path))` — simple and fast.

**Token pattern.** Each instance is constructed with an opaque `token = object()`. `TabPane._on_det_ready(token, contents)` applies the result only if `token is self._det_token`, discarding stale results from superseded selections.

**Signal:** `finished(object token, str contents_str)`.

### `SearchWorker`

**Purpose.** Recursively search the filesystem for filenames matching a query.

**Algorithm.** Spawns `find {HOME} -not -path "*/.*" -type f -iname "*{query}*"` as a subprocess (hidden files excluded). Reads stdout line by line. Emits batches of `BATCH_SIZE = 50` paths via `results_ready`. Emits `finished(total)` when done.

**Cancellation.** Sets `_cancelled = True` and calls `self._proc.kill()` to terminate the subprocess immediately.

**Signals:** `results_ready(list[str])`, `finished(int total)`.

---

## 13. `TabPane` — The Core Browser Pane

`TabPane(QWidget)` is entirely self-contained: it owns its own `QFileSystemModel`, proxy, views, address bar, sidebar, command bar, details panel, navigation history, clipboard fallback, and all worker references.

### 13.1 Construction

1. `_build_model()` — creates `QFileSystemModel` (root `/`, includes hidden files) wrapped by `GroupByTypeProxy` with grouping enabled.
2. `_build_ui()` — assembles all widgets.
3. `_connect_signals()` — connects all Qt signals to handler methods. Both `list_view` and `icon_view` are connected to the same handlers (navigate, context menu, keyboard shortcuts).

### 13.2 Layout

```
QVBoxLayout
├── BreadcrumbBar (address_bar) — hidden until this tab is active
├── Command bar QWidget
└── QSplitter (horizontal)
     ├── SidebarWidget (fixed 210px)
     ├── QStackedWidget
     │    ├── 0: FileView (list_view)
     │    └── 1: IconFileView (icon_view)
     └── Details panel (_details_panel, collapsible)
```

### 13.3 Navigation

**`navigate_to(path, push_history=True)`** is the main entry point:

1. Validates `os.path.isdir(path)`.
2. Cancels any running `FolderScanWorker` (`_cancel_scan`).
3. Calls `_leave_recent_view()` and `_leave_search_view()` if in those modes.
4. Maps path to a source index then proxy index. Sets as root on both `list_view` and `icon_view`.
5. Updates `address_bar.set_path(path)`.
6. Calls `_update_pin_button()` — toggles star icon and hides/shows Empty Trash / Restore buttons.
7. If `push_history`, calls `_push_history(path)`.
8. Emits `title_changed(label)` ("Trash" for `TRASH_PATH`, else `os.path.basename(path)`).
9. If details panel visible, calls `_update_details()`.
10. Calls `_apply_view_pref(path)` — switches view mode to remembered preference.
11. If no preference recorded, spawns `FolderScanWorker` to check for media.
12. Spawns `IconThumbWorker` to pre-load thumbnails (harmless if in list mode).

**History.** `self.history` is a list of strings (paths or `RECENT_SENTINEL`). `self.history_index` is the current position. `_push_history` truncates forward history before appending. `go_back` / `go_forward` decrement / increment `history_index` and call `_go_to_history`. `go_up` calls `os.path.dirname` on the current address.

**`_do_refresh()`** re-navigates to the current path with `push_history=False`. For Recent view, rebuilds the `RecentModel`.

### 13.4 View Mode Switching

`_toggle_view_mode()`: flips `_view_mode`, updates `_view_stack.setCurrentIndex`, syncs the other view's root index, updates button icon and tooltip, persists to `_view_prefs`, and if switching to icons starts `IconThumbWorker`.

`_apply_view_pref(path)`: if `_view_prefs.get(path)` differs from the current mode, calls `_toggle_view_mode()`.

`_on_scan_finished(path, is_media)`: auto-switches to icon view only if the user is still on that folder and is in list mode.

### 13.5 Search Modes

**Inline filter** via `set_search_filter(text)` forwards to `GroupByTypeProxy.set_search(text)`, narrowing the current directory without leaving the proxy model.

**Deep search** (`_start_search(query)`):
1. Cancels any running search.
2. Creates `SearchResultModel`, sets `_in_search = True`.
3. Swaps `list_view`'s model to `_search_model` and replaces the column-0 delegate with a plain `QStyledItemDelegate`.
4. Spawns `SearchWorker(HOME, query)`.
5. `_on_search_results(paths)` feeds batches to `_search_model.append_paths`.
6. `_on_search_finished(total)` updates the details panel with the total count.

`_leave_search_view()`: cancels worker, restores proxy and `_icon_delegate`, calls `_reconnect_selection()`.

**`_reconnect_selection()`**: model swaps create a new `selectionModel()`. This method disconnects old connections and reconnects `selectionChanged` on both views to `_on_selection_changed`.

### 13.6 Recent View

`_show_recent_view()`: builds a fresh `RecentModel`, swaps `list_view`'s model, sets `_in_recent = True`, updates address bar to "Recent Files", pushes `RECENT_SENTINEL` to history.

`_leave_recent_view()`: restores proxy model, clears `_in_recent`.

### 13.7 Trash View

`_show_trash_view()` ensures `TRASH_PATH` exists, then schedules `_do_navigate()` via `QTimer.singleShot(0)`. Inside `_navigate_to_trash()`: maps `TRASH_PATH` to a source index (connects `directoryLoaded` signal if not yet indexed), sets as root, updates address bar, shows "Empty Trash" and "Restore" command bar buttons.

**Empty Trash.** Confirmation dialog → `shutil.rmtree` / `os.remove` for each entry in `TRASH_PATH`. Errors are collected and shown in a warning dialog.

**Restore.** For each selected item, reads the corresponding `.trashinfo` file from `~/.local/share/Trash/info/` using `configparser`. Extracts and URL-decodes the original path. If the original parent directory still exists, moves the file there; otherwise falls back to `HOME`. Handles name collisions with `(1)`, `(2)`… suffix. Removes the `.trashinfo` file on success.

### 13.8 File Operations

**Open** (`_open(path, is_dir)`): directories → `navigate_to`; files → `subprocess.Popen('xdg-open "{path}"', shell=True)` + `self._recent.add(path)`.

**Open current** (`_open_current()`): handles multi-selection. Opens all files with `xdg-open`. Single folder → navigate in-place. Multiple folders → navigate to first, open rest in new tabs via `self.window().new_tab(d)`. Mixed selections open files and open each folder in a new tab.

**New folder** (`_new_folder(parent_dir)`):
1. Finds a unique name starting from "New Folder", incrementing "(2)", "(3)"…
2. Creates via `os.makedirs`.
3. Connects to `model.directoryLoaded` to start inline rename after the model indexes the new item.
4. Also fires via `QTimer.singleShot(0)` as a safety fallback for already-cached directories.

**New file** (`_new_file(parent_dir)`): same pattern, creates an empty file with `open(path, "w").close()`.

**Copy / Cut / Paste.** `_set_clipboard(mode, paths)` writes to `window()._shared_clipboard_mode` / `_shared_clipboard_paths` so the clipboard is shared across all tabs. `_paste(dest_dir)`: for each clipboard path, checks for name collision (confirms overwrite). Copy uses `shutil.copytree(dirs_exist_ok=True)` or `shutil.copy2`. Cut uses `shutil.move`. After a cut-paste, clears the clipboard.

**Delete** (`_delete(path)`):
- Already in Trash: permanent delete with confirmation. `shutil.rmtree` / `os.remove` + removes `.trashinfo`.
- Normal: FreeDesktop Trash spec. Finds a unique name in `TRASH_PATH`. Writes `[Trash Info]` section with `Path={url-encoded-original}` and `DeletionDate={ISO datetime}` before moving. Uses `urllib.parse.quote` for path encoding.

**Permanent delete** (`_cmd_perm_delete`): confirmation → `shutil.rmtree` or `os.remove` for all selected paths. Also removes any matching `.trashinfo` file if the file is already in Trash.

**Rename**: `_cmd_rename()` calls `list_view.edit(sel[0])` to start `IconDelegate`'s inline rename editor.

**Compress** (`_compress`): searches PATH for `file-roller`, `ark`, `xarchiver`, `peazip`, `engrampa` in order. Builds the appropriate command line for the found manager and launches via `subprocess.Popen`. Shows a warning if none is found.

**Open in Terminal** (`_open_in_terminal(path)`): candidate list: `$TERMINAL` env var, `x-terminal-emulator`, then gnome-terminal, konsole, xfce4-terminal, mate-terminal, tilix, alacritty, kitty, wezterm, xterm. Tries each in order until one succeeds.

### 13.9 Context Menu

**On a file/folder item:**
Single item: Open, Open in new tab (dirs), Open in Terminal (dirs), Open with submenu (files — lists MIME-matched apps, each as a direct action, plus "Other application…"), Compress, Cut, Copy, Paste (dir targets only), Rename (single), Delete, Properties (single).
Multiple items: count label, Compress, Cut, Copy, Delete.

**On empty space:**
New Folder, New File, Paste (if clipboard non-empty), Open in Terminal, Sort by submenu (Name/Size/Type/Date with checkmarks), Group by Type toggle, Refresh.

### 13.10 Details Panel

Right-side collapsible `QWidget#detailsPanel` showing icon/preview, Name, Type, Size, Contents, Modified, Location. The `_toggle_details` handler resizes the `QSplitter` to give the panel 260px or collapse it to 0.

`_update_details()` is debounced by a 120ms `QTimer` (so rapid shift-click selection changes don't hammer `os.stat`):
- No selection → `_show_folder_details(current_path)`.
- Multi-selection → "N items selected".
- Single item: fills stat fields immediately. For image files: `_load_preview_pixmap` (synchronous on main thread). For video: starts `ThumbnailWorker`. For folders: Contents shows "…" then `DetailsWorker` fills it asynchronously.

`_load_preview_pixmap(path, max_size)` (static method):
- Images (not `.svg`): `QPixmap(path)` scaled keeping aspect ratio.
- `.svg`: `QSvgRenderer` renders into a transparent `max_size × max_size` pixmap.
- Video: returns `None` (ThumbnailWorker handles it).

### 13.11 Sorting and Grouping

`_apply_sort(col)`: clicking the same column toggles ascending/descending; a new column resets to ascending. Calls `proxy.sort()` and `list_view.sortByColumn()`.

`_toggle_group_by_type(checked)`: `proxy.set_grouping(checked)`, re-sort, `list_view.scheduleDelayedItemsLayout()`.

`_toggle_show_hidden()`: `proxy.set_show_hidden()` — never touches `model.setFilter()` to preserve the Hidden flag needed for Trash indexing.

### 13.12 Favorites

`_toggle_favorite()`: reads current path. If `sidebar.has_favorite(path)` → remove; else add. Calls `_update_pin_button()` to refresh the star icon and tooltip.

### 13.13 Thread Lifecycle

**Graveyard pattern.** When a worker is superseded mid-run, the old thread/worker pair is appended to the appropriate graveyard list (`_thumb_graveyard`, `_det_graveyard`, `_search_graveyard`) rather than deleted. The worker's signal connections are disconnected so stale results are discarded, but the OS thread runs to natural completion.

**`cleanup_threads()`** is called on tab close or app exit:
1. Cancels all active workers: `_cancel_scan`, `_cancel_thumb_job`, `_cancel_det_job`, `_cancel_search`, `_cancel_icon_thumb`.
2. For each thread in the graveyard lists that is still running: `thread.quit()` then `thread.wait()` (blocking). This prevents Qt from destroying a `QThread` object while its OS thread is alive.

---

## 14. `FileExplorer` — The Main Window

### 14.1 Window Setup

`QMainWindow` with `Qt.WindowType.FramelessWindowHint` — no OS title bar or border. Minimum size 1200×600. Constructs `RecentFiles`, `Favorites`, and calls `_parse_desktop_files()` at startup. Shared clipboard stored at the window level: `_shared_clipboard_mode` and `_shared_clipboard_paths`.

### 14.2 Nav bar (`_build_toolbar`)

The nav bar is a plain `QWidget#navBar` placed below the tab strip. A hidden dummy `QToolBar` satisfies `QMainWindow.addToolBar()` without contributing visible UI.

Contents (left to right): back/forward/up `QToolButton`s (with painted arrow icons, enabled/disabled dynamically), favorite star `QToolButton`, address bar container (active tab's `BreadcrumbBar` reparented here by `_swap_address_bar`), `SearchBar`, theme toggle `QToolButton`.

**`_swap_address_bar(pane)`**: removes all widgets from `_tb_addr_layout`, reparents `pane.address_bar` into `_tb_addr_container`, shows it, stores reference in `_active_address_bar`.

### 14.3 Tab management (`_build_tabs`)

The central widget is a `QVBoxLayout` containing: title row (`_visible_tab_bar` + window control buttons), nav bar, and a vertical `QSplitter` holding the `QTabWidget` and `_TerminalPanel`.

**QTabWidget / _PlusTabBar sync.** The `QTabWidget`'s own tab bar is hidden. `_visible_tab_bar` mirrors all tab operations. `_on_tab_moved(from_idx, to_idx)` keeps them in sync on drag.

**`new_tab(path)`**: creates `TabPane`, hides its address bar, connects its signals, adds to both `_tabs` and `_visible_tab_bar`, calls `pane.navigate_to(path)`.

**`_close_tab(index)`**: prevents closing the last tab. Calls `pane.cleanup_threads()` before `deleteLater()`.

**`_on_tab_changed(index)`**: `_swap_address_bar(pane)`, `_refresh_nav_buttons()`, clears search bar.

### 14.4 Window chrome

**Title row.** `_visible_tab_bar` fills the horizontal space. Window control buttons are `_WinCtrlButton` instances: minimize → `showMinimized()`, maximize → `_toggle_maximize()`, close → `close()`.

**`_toggle_maximize()`**: `showMaximized()` or `showNormal()`, updates `_btn_max` text (□ / ❐), flips `_maximized`.

**Event filter on `_visible_tab_bar`** (for middle-click close): `MouseButtonRelease + middle button` → `_close_tab`.

**`closeEvent`**: calls `pane.cleanup_threads()` for every tab before `super().closeEvent(event)`.

### 14.5 Keyboard shortcuts

Registered via `QShortcut` in `_setup_shortcuts()`. See the [Keyboard Shortcuts Reference](#17-keyboard-shortcuts-reference) section for the full table.

---

## 15. Terminal Subsystem

### `_Attrs`

`__slots__`-optimized class holding character display attributes: `fg` and `bg` (hex color strings, defaults `#D4D4D4` / `#1E1E1E`), `bold`, `italic`, `underline`, `reverse` (booleans). `__eq__` compares all fields so adjacent cells with the same attributes can be merged into a single `QTextCharFormat` span in the renderer.

### `_xterm_color(n)`

Maps xterm-256 color index to a hex string. Indices 0–15: direct lookup in `_PALETTE16`. Indices 16–231: 6×6×6 RGB cube (`55 + x * 40` per channel, with 0 → 0). Indices 232–255: greyscale ramp `8 + (n - 232) * 10`.

### `_VTScreen`

A 2D grid of `[char, _Attrs]` cells representing the terminal's current screen, plus a scrollback buffer.

**State**: `_screen[row][col]` (list-of-lists), cursor position `(_cur_row, _cur_col)`, saved cursor `_saved`, current pending attributes `_attrs`, scroll region `(_scroll_top, _scroll_bot)`, `_dirty: set[int]` of rows changed since the last flush, `_scrollback` and `_new_scrollback` lists.

**`feed(data: bytes)`**: decodes as UTF-8 (replacing errors). Handles partial escape sequences at buffer boundaries by retaining the incomplete tail in `_buf`. Tokenizes with `_RE` compiled regex covering CSI, DCS/SOS/PM/APC, OSC, single ESC sequences, C0 controls, and plain text. Each token goes to `_dispatch`.

**C0 controls**: BEL (ignored), BS (cursor left 1), HT (tab to next 8-col stop), CR (column 0), LF/VT/FF (scroll if at scroll-bottom, else cursor down).

**ESC sequences**: ESC M (reverse index — scroll down), ESC 7 / 8 (save/restore cursor).

**CSI sequences implemented**:
`m` (SGR), `H`/`f` (CUP), `A`/`B`/`C`/`D` (CUU/CUD/CUF/CUB), `E`/`F` (CNL/CPL), `G` (CHA), `d` (VPA), `s`/`u` (SCP/RCP), `r` (DECSTBM), `J` (ED — 0/1/2/3), `K` (EL — 0/1/2), `L`/`M` (IL/DL), `S`/`T` (SU/SD), `P` (DCH), `@` (ICH). All `?…h`/`?…l` DEC private modes are silently consumed.

**SGR parsing** (`_sgr(params)`): handles reset (0), bold (1), italic (3), underline (4), reverse (7), their reset counterparts (22/23/24/27), standard colors 30–37/40–47, bright colors 90–97/100–107, and xterm-256 (`38;5;n` / `48;5;n`) and truecolor (`38;2;r;g;b` / `48;2;r;g;b`) formats.

**Scrollback**: lines pushed off the top of scroll region when `scroll_top == 0` are appended to `_scrollback` and `_new_scrollback`. `flush_scrollback()` returns and clears `_new_scrollback`, allowing the renderer to append only new history lines without rebuilding the entire scrollback.

### `_TerminalView(QPlainTextEdit)`

Owns the PTY and renders `_VTScreen` into the document.

**PTY lifecycle** (`start(cwd)`): `pty.fork()` — child `os.execvpe`s the shell with `TERM=xterm-256color`, `COLORTERM=truecolor`. Parent sets fd non-blocking, sends initial `TIOCSWINSZ (24, 80)`, starts a 16ms render timer, schedules `_sync_size_and_winch` after 50ms for the first real resize.

**Stop** (`stop()`): `_stopping = True`, `SIGTERM` to shell, `waitpid(WNOHANG)`, close fd.

**Render tick** (`_tick()`): drains up to 64KB in non-blocking mode (handles `BlockingIOError` as "no data"). On `OSError` or empty read: calls `_reap_and_restart()`.

**`_reap_and_restart()`**: cleans up the dead process. If `_stopping` is False (shell exited on its own, e.g. user typed `exit`), resets `_VTScreen`, clears the document, and restarts the shell via `QTimer.singleShot(50, lambda: self.start(self._cwd))`.

**`_render_dirty()`** — the incremental renderer:
1. **Scrollback flush**: appends newly-pushed-off lines to the `QTextDocument` end with per-run `QTextCharFormat`. Increments `_doc_offset`.
2. **Document growth**: ensures `_doc_offset + vt.rows` blocks exist.
3. **Dirty lines**: for each dirty row, finds the corresponding document block at `_doc_offset + row`, selects the entire line and clears it, then writes character runs grouped by `_Attrs` equality. Reverse video swaps fg/bg. Bold brightening: if fg is one of the first 8 palette entries and bold is True, maps to the bright variant (index + 8).
4. Scrolls the cursor line into view.

**`paintEvent`**: after `super().paintEvent`, draws a block cursor at the VT cursor position. Filled 2×char_height when focused; outlined 1×char_height when unfocused.

**Keyboard → PTY** (`keyPressEvent`): Ctrl+Shift+C → clipboard copy; Ctrl+Shift+V → clipboard paste to PTY; Ctrl+{char} → `ord(char) & 0x1F`; special keys (arrows, F1–F12, Home/End, PageUp/Down, Delete, Insert, Backspace) → VT escape sequences via `_KEY_MAP`; all other printable text → UTF-8 encoded and written to the PTY fd.

**Size sync**: `_sync_size()` computes `cols = viewport_width / char_width` and `rows = viewport_height / char_height`, calls `_vt.resize`, resets `_rendered`, and sends `TIOCSWINSZ`. `resizeEvent` debounces via an 80ms single-shot timer.

**`change_dir(path)`**: sends `cd '{safe_path}'\n` to the PTY (single-quotes escaped).

**Context menu**: Copy, Paste (clipboard to PTY), Clear (`_do_clear` resets `_VTScreen` and sends `\x0c`).

### `_TerminalPanel`

Container widget with a "TERMINAL" header bar (Clear `⊘` button, Close `✕` button, double-click hint text). `_TerminalView` sits below. Shell starts immediately on construction (`_view.start(HOME)`).

**`show_panel()`**: shows the widget and sizes the vertical splitter so the terminal takes `28 + 3 * line_height` pixels, giving remaining space to the file pane.

**`_toggle_expand()`**: saves splitter sizes on first expand (gives terminal the full height), restores them on collapse.

**`change_dir(path)`**: forwarded to `_view.change_dir(path)`.

**`closeEvent`**: `_view.stop()` (kills shell). Only on app close — hiding the panel does not stop the shell.

---

## 16. Signal Map

| Emitter | Signal | Connected To |
|---|---|---|
| `BreadcrumbBar` | `navigate(str)` | `TabPane.navigate_to` |
| `SearchBar` | `search_changed(str)` | `FileExplorer._on_search_changed` |
| `SearchBar` | `search_cleared()` | `FileExplorer._on_search_cleared` |
| `SidebarWidget` | `navigate(str)` | `TabPane._on_sidebar_navigate` |
| `SidebarWidget` | `unmount_requested(str)` | `TabPane._on_unmount_requested` |
| `FileView` | `go_up` | `TabPane.go_up` |
| `FileView` | `open_current` | `TabPane._open_current` |
| `FileView` | `delete_sel` | `TabPane._cmd_delete` |
| `FileView` | `perm_delete_sel` | `TabPane._cmd_perm_delete` |
| `FileView` | `cut_sel` | `TabPane._cmd_cut` |
| `FileView` | `copy_sel` | `TabPane._cmd_copy` |
| `FileView` | `paste_sel` | `TabPane._paste` |
| `FileView` | `refresh_req` | `TabPane._do_refresh` |
| `FileView` | `new_folder_req` | `TabPane._new_folder` |
| `FileView` | `new_file_req` | `TabPane._new_file` |
| `FileView` | `doubleClicked` | `TabPane._on_double_click` |
| `FileView` | `customContextMenuRequested` | `TabPane._show_context_menu` |
| `IconFileView` | (same set as FileView) | (same handlers) |
| `TabPane` | `title_changed(str)` | `FileExplorer._on_pane_title_changed` |
| `TabPane` | `nav_state_changed()` | `FileExplorer._refresh_nav_buttons` |
| `TabPane` | `open_in_new_tab(str)` | `FileExplorer.new_tab` |
| `_PlusTabBar` | `new_tab_requested` | `FileExplorer.new_tab(HOME)` |
| `_PlusTabBar` | `tabCloseRequested(int)` | `FileExplorer._close_tab` |
| `QTabWidget` | `currentChanged(int)` | `FileExplorer._on_tab_changed` |
| `_visible_tab_bar` | `currentChanged(int)` | `_tabs.setCurrentIndex` |
| `SearchWorker` | `results_ready(list)` | `TabPane._on_search_results` |
| `SearchWorker` | `finished(int)` | `TabPane._on_search_finished` |
| `DetailsWorker` | `finished(token, str)` | `TabPane._on_det_ready` |
| `ThumbnailWorker` | `finished(str, object)` | `TabPane._on_thumbnail_ready` |
| `IconThumbWorker` | `ready(str, object)` | `TabPane._on_icon_thumb_ready` |
| `FolderScanWorker` | `finished(str, bool)` | `TabPane._on_scan_finished` |
| `QFileSystemModel` | `directoryLoaded(str)` | `TabPane._new_folder` / `_new_file` (one-shot) |

---

## 17. Keyboard Shortcuts Reference

### Global (FileExplorer-level)

| Shortcut | Action |
|---|---|
| Ctrl+T | New tab |
| Ctrl+W | Close current tab |
| Alt+Left | Go back |
| Alt+Up | Navigate to HOME |
| Ctrl+R | Refresh current folder |
| Ctrl+Shift+V | Toggle list / icon view |
| Ctrl+` | Toggle terminal panel |

### In FileView / IconFileView

| Shortcut | Action |
|---|---|
| Enter / Return | Open selected item(s) |
| Delete | Move selected to Trash |
| Shift+Delete | Permanently delete selected |
| Ctrl+X | Cut |
| Ctrl+C | Copy |
| Ctrl+V | Paste into current folder |
| Ctrl+R | Refresh |
| Ctrl+N | New folder |
| Ctrl+F | New file |
| F2 | Rename (start inline edit) |
| Double-click empty space | Go to parent folder |

### In _TerminalView

| Shortcut | Action |
|---|---|
| Ctrl+Shift+C | Copy selection to clipboard |
| Ctrl+Shift+V | Paste clipboard text to PTY |
| Ctrl+{char} | Send ASCII control code (e.g. Ctrl+C → SIGINT) |
| Arrow keys | VT cursor sequences |
| F1–F12 | VT function key sequences |
| Home / End | `\x1b[H` / `\x1b[F` |
| PageUp / PageDown | `\x1b[5~` / `\x1b[6~` |
| Delete | `\x1b[3~` |
| Insert | `\x1b[2~` |

---

## 18. Persistence Files Reference

| File | Format | Contents |
|---|---|---|
| `~/.local/share/file_explorer_recent.json` | JSON array of strings | Absolute paths, newest first, max 50 |
| `~/.local/share/file_explorer_favorites.json` | JSON array of strings | Absolute directory paths, user order |
| `~/.local/share/file_explorer_view_prefs.json` | JSON object | `{"/abs/path": "list" or "icons"}` |
| `~/.local/share/file_explorer_theme.json` | JSON object | `{"dark": true}` or `{"dark": false}` |

All files are created automatically on first use. Read errors return empty defaults. Write errors are silently ignored.

---

## 19. External Tool Dependencies

| Tool | Used For | Required? |
|---|---|---|
| `xdg-open` | Open files with their default application | Yes (file opening) |
| `xdg-mime` | MIME type detection and default-app setting | Soft — falls back to Python `mimetypes` |
| `ffprobe` + `ffmpeg` | Video thumbnail generation in the details panel | Optional |
| `udisksctl` | Auto-mounting and unmounting removable drives | Optional |
| `find` | Recursive deep file search | Yes (search feature) |
| `x-terminal-emulator` | "Open in Terminal" fallback | Optional |
| gnome-terminal / konsole / alacritty / kitty / xterm / etc. | "Open in Terminal" | Optional — needs at least one |
| file-roller / ark / xarchiver / peazip / engrampa | "Compress" right-click option | Optional — needs at least one |
| Segoe Fluent Icons / Segoe MDL2 Assets | Fluent glyph font for toolbar glyphs | Optional — degrades gracefully |
| Python `pty` stdlib module | PTY for the embedded terminal | Linux only |
| Python `PyQt6.QtSvg.QSvgRenderer` | SVG preview in the details panel | Optional (only used when opening `.svg`) |

---

## 20. Application Entry Point

```python
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")            # cross-platform base style
    _apply_win11_palette(app)         # QPalette for native widgets
    app.setStyleSheet(WIN11_LIGHT_QSS)# full Win11 light theme QSS
    start_path = (sys.argv[1]
                  if len(sys.argv) > 1 and os.path.isdir(sys.argv[1])
                  else HOME)
    w = FileExplorer(start_path=start_path)
    w.show()
    sys.exit(app.exec())
```

**Fusion style** is used as the base so QSS overrides render consistently across Linux desktop environments (GNOME, KDE, XFCE, etc.) without inheriting unexpected platform chrome. The Win11 palette and QSS then override everything on top.

An optional command-line argument sets the initial directory of the first tab. If absent or not a valid directory, the first tab opens at `HOME`.
