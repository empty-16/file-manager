# File Manager — Architecture & Component Documentation

## Overview

A personal file manager for Linux built with PyQt6, designed around my own workflow. Styled after the Windows 11 Fluent Design language — still a work in progress, but already supports multi-tab browsing, list and icon views, a built-in terminal, file operations, recent files, favorites, trash management, and deep search

The entire application lives in a single Python file (`file-manager.py`) of ~7,700 lines, with no external dependencies beyond PyQt6.

---

## High-Level Architecture

```
main()
 └── FileExplorer (QMainWindow)          ← top-level window
      ├── Custom title bar + tab strip
      ├── Nav bar (back/fwd/up + address + search)
      ├── QTabWidget (hidden) + visible QTabBar
      │    └── TabPane (one per tab)      ← self-contained browser pane
      │         ├── SidebarWidget
      │         ├── FileView / IconFileView  (list ↔ icon toggle)
      │         ├── BreadcrumbBar (address bar)
      │         ├── Command bar (toolbar buttons)
      │         └── Details panel
      └── _TerminalPanel (collapsible, Ctrl+`)
```

Data flows upward via **PyQt signals**. Each `TabPane` owns its own model, proxy, views, and navigation history. `FileExplorer` only coordinates the active tab and shared state (clipboard, recent files, favorites).

---

## Theming Layer

### `WIN11_LIGHT_QSS` / `WIN11_DARK_QSS`

Two large Qt StyleSheet strings that implement the full Fluent 2 design token set for both light and dark modes. Color tokens are sourced from the official WinUI 3 `themeresources.xaml`. The stylesheets cover every widget type in the app: toolbars, tabs, tree/list views, menus, dialogs, scrollbars, tooltips, and more.

### `_apply_win11_palette()` / `_apply_win11_dark_palette()`

Set the Qt `QPalette` so that native widgets (which don't read QSS) also match the theme. Called at startup and again when the user toggles dark/light mode.

### Theme toggle

`FileExplorer._toggle_theme()` switches at runtime by calling the appropriate palette function and swapping the application stylesheet. The choice is persisted to `~/.local/share/file_explorer_theme.json`.

---

## Icon System

### Built-in Painted Icons

All file-type icons are rendered programmatically using `QPainter` — no image files are bundled. The painter helpers produce:

| Function | Output |
|---|---|
| `_make_folder_icon()` | Two-tone flat yellow folder |
| `_make_generic_file_icon()` | White document with fold corner |
| `_make_pdf_icon()` | Document + red "PDF" badge |
| `_make_image_icon()` | Document + landscape thumbnail |
| `_make_video_icon()` | Document + indigo play-circle |
| `_make_iso_icon()` | Document + grey disc |
| `_make_audio_icon()` | Document + music note |
| `_make_archive_icon()` | Document + stack layers |
| `_make_code_icon()` | Document + `</>` glyph |
| `_make_text_icon()` | Document + lines |

`_doc_base()` is a shared helper that draws the rounded document body with the folded top-right corner used by all document-style icons.

### `resolve_icon(path, is_dir)`

The central icon resolver. Resolution order:

1. Return from `_icon_cache` if already resolved.
2. For directories, return `_make_folder_icon()`.
3. Check `EXT_ICON_MAP` for a known extension → look up theme icon by XDG name.
4. Fall back to `QFileIconProvider` (reads from the OS icon theme).
5. Last resort: `_make_generic_file_icon()` (always non-null).

Results are cached in `_icon_cache` keyed by file extension.

### Command Bar Icons (`_cmd_icon()`)

Separate small (16×16) icons for the command bar buttons, also painted with `QPainter`. Each icon has a `normal` and `disabled` variant so Qt can switch them automatically.

### Fluent Font Helpers (`_fluent_font`, `_apply_fluent_icon`)

Helpers that set the "Segoe Fluent Icons" / "Segoe MDL2 Assets" font on a widget, used for toolbar glyphs. Degrades gracefully on Linux where these fonts may not be installed.

---

## Persistence Classes

### `RecentFiles`

Tracks the last 50 opened files, stored in `~/.local/share/file_explorer_recent.json`. Entries are kept only while the file still exists on disk. Exposes `add(path)` and `entries()`.

### `Favorites`

Manages a user-pinned list of directories, stored in `~/.local/share/file_explorer_favorites.json`. Exposes `add`, `remove`, `contains`, and `entries`.

### View preferences

Per-folder view mode (list vs icons) is persisted to `~/.local/share/file_explorer_view_prefs.json`. Each `TabPane` loads and saves this on navigation.

---

## Data Model Layer

### `QFileSystemModel` + `GroupByTypeProxy`

Each `TabPane` creates one `QFileSystemModel` rooted at `/` (so it can watch all paths without re-rooting). The model is wrapped by `GroupByTypeProxy`, a `QSortFilterProxyModel` subclass that adds:

- **Group-by-type sorting**: folders always sort before files; within files, groups by extension class.
- **Hidden file filter**: hides dot-files unless `show_hidden` is on; always lets `~/.local/share/Trash` through so Trash is navigable.
- **Live search filter**: `set_search(text)` narrows the view to matching filenames in the current directory.
- **Date formatting**: overrides the date column to 24-hour format regardless of system locale.
- **Rename support**: sets `ItemIsEditable` on column 0.

### `RecentModel`

A `QAbstractTableModel` that presents the recent-files list as a flat table (Name / Size / Type / Date Modified) with custom icons. Used when the user clicks "Recent" in the sidebar — the proxy is swapped out for this model on the same `FileView`.

### `SearchResultModel`

Another `QAbstractTableModel` for search results. It is populated incrementally as `SearchWorker` emits batches, so rows appear in real time as the search runs.

---

## View Layer

### `FileView` (QTreeView subclass)

The default list/detail view. Adds on top of `QTreeView`:

- Double-click on empty space → navigate to parent folder (`go_up` signal).
- Full keyboard shortcut map: Enter (open), Delete (trash), Shift+Delete (permanent delete), Ctrl+X/C/V (cut/copy/paste), Ctrl+R (refresh), Ctrl+N (new folder), Ctrl+F (new file), F2 (rename).
- **Icon-area drag detection**: dragging from the icon region of an item initiates a file URI drag (`QDrag`) with the item's icon as the drag pixmap, enabling drops into other apps.

### `IconFileView` (QListView subclass)

The icon/grid view. Same keyboard shortcuts and double-click-to-go-up behaviour as `FileView`. Uses `QListView.IconMode` with a 110×110 grid.

### `IconDelegate` (QStyledItemDelegate)

Injects custom-painted icons into column 0 of `FileView`. Overrides `paint()` directly (not just `initStyleOption`) to prevent `QFileSystemModel` from silently clobbering the icon during the style's draw pass — a Qt6-specific issue.

Also owns the inline-rename editor: strips the file extension from the selection so only the name part is highlighted on F2.

### `ImagePreviewDelegate` (QStyledItemDelegate)

Used in `IconFileView`. For image files, replaces the icon with a rounded-corner thumbnail loaded from `_thumb_cache`. Falls back to the standard icon for non-images. Renders a subtle selection highlight and elided filename label below each item.

---

## UI Components

### `BreadcrumbBar` (QStackedWidget)

Windows-Explorer-style address bar with two pages:

- **Page 0 — crumb view**: a row of clickable `QPushButton` path segments separated by `›` chevrons. Clicking a crumb navigates to that path. Clicking a chevron opens a `QMenu` listing all sibling subdirectories at that level, allowing quick lateral navigation. Clicking the blank bar area switches to edit mode.
- **Page 1 — edit view**: a plain `QLineEdit` pre-filled with the current path. Enter commits; Escape or focus-out cancels.

Emits a single `navigate(str)` signal in all cases.

### `SearchBar` (QWidget)

Compact search box with a painted magnifier icon and an × clear button. Debounces `textChanged` by 150 ms using a `QTimer` before emitting `search_changed(str)`, so the proxy filter is not hammered on every keystroke.

### `SidebarWidget` (QWidget)

Fixed-width (210 px) left panel with three sections:

- **Pinned folders**: Home, Desktop, Documents, Downloads, Music, Pictures, Videos — only shown if the directory exists on disk.
- **Quick Access**: dynamically rebuilt from the `Favorites` list. Drag-and-drop (right-click context menu) is used to add/remove entries.
- **Devices & Drives**: populated by scanning `QStorageInfo.mountedVolumes()`. A `QTimer` polls every 3 seconds for newly mounted or removed drives. Shows drive name, filesystem, and used/total space. Right-clicking a drive offers an "Unmount" option (calls `udisksctl unmount`).

Clicking "Recent" emits the `RECENT_SENTINEL` string instead of a path, which `TabPane` intercepts to switch to the Recent view.

### `OpenWithDialog` (QDialog)

Shown when the user right-clicks → "Open With". Parses all installed `.desktop` files from standard XDG directories (`/usr/share/applications`, `~/.local/share/applications`) using `configparser`. Filters apps by MIME type (queried via `xdg-mime`). Includes a search box to filter the app list. "Make Default" calls `xdg-mime default` to set the association persistently.

---

## Background Workers

All workers are `QObject` subclasses moved to a `QThread` (Qt's worker-object pattern). This keeps the UI responsive while I/O runs on other threads.

### `FolderScanWorker`

Samples up to 200 files in a directory to decide if it's a "pure media folder" (only images/videos). If so, `TabPane` automatically switches to icon view for that folder.

### `ThumbnailWorker`

Generates a preview pixmap for a single video file by calling `ffprobe` (to get duration) then `ffmpeg` (to extract a frame at 10% into the video) via `subprocess`. The result is returned as a `QPixmap` via the `finished(path, pixmap)` signal.

### `IconThumbWorker`

Batch-loads image thumbnails for all visible files in icon view. Uses `QImageReader` with a scaled-size hint to decode large images cheaply. Results are emitted one at a time via `ready(path, pixmap)` and stored in the global `_thumb_cache` dict so they survive tab switches.

### `DetailsWorker`

Counts the direct children of a folder (`os.listdir`) off the main thread. Uses a **token** pattern: each new request gets a fresh `object()` sentinel; when the result arrives, it is only applied if the token still matches the current request, discarding stale results from superseded folder selections.

### `SearchWorker`

Runs a `find` subprocess to recursively search the current directory for filenames matching the query (case-insensitive). Emits results in batches of 50 via `results_ready(list)` so `SearchResultModel` can grow the table in real time. Cancelled by killing the subprocess.

---

## `TabPane` — The Core Browser Pane

`TabPane` is the central component. Each browser tab gets one independent instance. It owns:

- `QFileSystemModel` + `GroupByTypeProxy`
- `FileView` (list) + `IconFileView` (grid), stacked in a `QStackedWidget`
- `BreadcrumbBar` (address bar — reparented into the main toolbar when this tab is active)
- `SidebarWidget`
- Command bar (strip of action buttons)
- Details panel
- Navigation history stack (`self.history` / `self.history_index`)
- All background worker references

### Navigation

`navigate_to(path)` is the main entry point. It:

1. Exits "Recent" or "Search" mode if active.
2. Maps the path to a model index and sets it as the root of both views.
3. Updates the address bar, pushes the path onto the history stack, and emits `title_changed`.
4. Kicks off `FolderScanWorker` to decide whether to auto-switch to icon view.
5. If in icon view, starts `IconThumbWorker` to pre-load thumbnails.

Back/forward navigation walks the `history` list. Going up calls `os.path.dirname`.

### View Modes

The `_view_stack` holds both views; switching calls `setCurrentIndex(0)` (list) or `setCurrentIndex(1)` (icons) and updates the model root index on the newly-shown view. The choice is persisted per-path in `_view_prefs`.

### File Operations

All operations go through `shutil` (copy/move/rmtree) and `os` (rename, makedirs):

- **Copy/Cut/Paste**: paths are stored in `_shared_clipboard_mode` / `_shared_clipboard_paths` on the `FileExplorer` window so they are shared across tabs.
- **Delete (trash)**: moves the file to `~/.local/share/Trash/files` and writes a `.trashinfo` metadata file to `~/.local/share/Trash/info`.
- **Permanent delete**: calls `shutil.rmtree` or `os.remove` after a confirmation dialog.
- **Rename**: uses `QFileSystemModel`'s built-in inline editor triggered by `FileView.edit()`.

### Details Panel

A collapsible right-side panel showing icon/preview, name, type, size, item count, modification date, and location for the selected file or folder. Heavy work (folder item count, video thumbnail) is done asynchronously by `DetailsWorker` and `ThumbnailWorker`. A 120 ms `QTimer` debounces rapid selection changes.

### Search Mode

Triggered when the user types in the nav-bar `SearchBar`. Two levels:

1. **Inline filter** (`set_search_filter`): if the query is short (≤ 3 chars) or the user hasn't pressed Enter, the proxy's `set_search` narrows the current directory view in-place.
2. **Deep search** (`_start_deep_search`): on Enter or longer queries, spawns a `SearchWorker` that calls `find` recursively. Results populate a `SearchResultModel` displayed in `FileView`. Cancelled automatically when navigation or a new search starts.

---

## `FileExplorer` — The Main Window

`FileExplorer` (a `QMainWindow`) provides the shell around all tabs:

- **Frameless window** (`Qt.WindowType.FramelessWindowHint`) with a custom title bar drawn as a `QWidget`. Window dragging is implemented via mouse event filtering on the tab bar area.
- **Custom title bar**: drag area + visible `QTabBar` + minimize/maximize/close buttons painted with `QPainter` (no system chrome).
- **Nav bar**: back/forward/up buttons + favorite-star button + address bar container (the active tab's `BreadcrumbBar` is reparented here) + `SearchBar`.
- **Tab management**: `QTabWidget` (hidden, used as the pane container) + a separate visible `QTabBar` kept in sync. Tabs can be closed with Ctrl+W or middle-click; the last tab cannot be closed.
- **Shared clipboard**: `_shared_clipboard_mode` and `_shared_clipboard_paths` on the window object so cut/paste works across tabs.
- **Keyboard shortcuts**: Ctrl+T (new tab), Ctrl+W (close tab), Alt+Left (back), Alt+Up (home), Ctrl+R (refresh), Ctrl+Shift+V (toggle view), Ctrl+` (toggle terminal).

---

## `_TerminalPanel` and `_TerminalView`

An embedded terminal emulator toggled by Ctrl+`. It runs the user's `$SHELL` (defaulting to `/bin/bash`) as a subprocess. `_TerminalView` is a `QPlainTextEdit` that:

- Feeds input lines to the shell's stdin.
- Reads stdout/stderr on a background `QThread` and appends to the display.
- Tracks the current working directory by injecting a `cd` command and watching `pwd` output.
- `change_dir(path)` is called by `TabPane` on navigation so the terminal follows the active folder.
- Supports expand/collapse within the vertical `QSplitter` that separates it from the file pane.

---

## Application Entry Point

```python
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")          # base style (QSS overrides appearance)
    _apply_win11_palette(app)       # palette for native widgets
    app.setStyleSheet(WIN11_LIGHT_QSS)
    start_path = sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else HOME
    w = FileExplorer(start_path=start_path)
    w.show()
    sys.exit(app.exec())
```

An optional command-line argument sets the initial directory. The Fusion style is used as the base so QSS overrides render consistently across platforms.
