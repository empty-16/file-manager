import sys
import os
import re
import shutil
import mimetypes
import subprocess
import configparser
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QVBoxLayout,
    QWidget, QToolBar, QLineEdit, QSplitter, QMenu,
    QMessageBox, QDialog, QFormLayout,
    QLabel, QDialogButtonBox, QListWidget, QListWidgetItem,
    QHBoxLayout, QPushButton, QScrollArea, QSizePolicy,
    QFrame, QAbstractItemView, QStyledItemDelegate, QFileIconProvider,
    QStackedWidget, QTabWidget, QTabBar, QToolButton, QPlainTextEdit, QListView,
)
from PyQt6.QtCore import (
    Qt, QDir, QPoint, QSortFilterProxyModel, QModelIndex,
    QAbstractTableModel, QVariant, QSize, pyqtSignal,
    QThread, QObject, QTimer, QStorageInfo,
)
from PyQt6.QtGui import (QAction, QFileSystemModel, QIcon, QColor,
    QPixmap, QPainter, QPainterPath, QFont, QBrush, QPen,
    QLinearGradient, QRadialGradient, QKeySequence, QShortcut,
    QPalette, QTextCharFormat, QTextCursor)


# ═══════════════════════════════════════════════════════════════════════════════
#  WIN 11 LIGHT THEME
# ═══════════════════════════════════════════════════════════════════════════════
#
#  All hex values sourced from the official WinUI 3 themeresources.xaml and the
#  Fluent 2 design token documentation.  Opacity variants are resolved to their
#  opaque equivalents against the relevant surface colour so Qt stylesheets can
#  use them without alpha compositing surprises.
#
#  Token reference (light mode):
#    SolidBackgroundFillColorBase          #F3F3F3  – main window/card bg
#    SolidBackgroundFillColorSecondary     #EEEEEE  – secondary surfaces
#    SolidBackgroundFillColorTertiary      #F9F9F9  – layer-3 (toolbar, bars)
#    SolidBackgroundFillColorQuarternary   #FFFFFF  – pure white surfaces
#    ControlFillColorDefault   #B3FFFFFF → on #F3F3F3 ≈ #F9F9F9
#    ControlFillColorSecondary #80F3F3F3 → on #F3F3F3 ≈ #F6F6F6
#    ControlFillColorTertiary  #4DF3F3F3 → on #F3F3F3 ≈ #F4F4F4
#    ControlFillColorDisabled  #4DF3F3F3 → same
#    ControlStrokeColorDefault           rgba(0,0,0,0.0578) ≈ #0F000000 → #EBEBEB
#    ControlStrokeColorSecondary         rgba(0,0,0,0.1608) ≈ #29000000 → #D4D4D4
#    DividerStrokeColorDefault           rgba(0,0,0,0.0803) ≈ #14000000 → #E9E9E9
#    TextFillColorPrimary                rgba(0,0,0,0.8956) ≈ #1A000000 → #1A1A1A
#    TextFillColorSecondary              rgba(0,0,0,0.6063) ≈ #9A000000 → #5C5C5C
#    TextFillColorTertiary               rgba(0,0,0,0.4458) ≈ #72000000 → #838383  (not used)
#    TextFillColorDisabled               rgba(0,0,0,0.3614) ≈ #5C000000 → #9E9E9E
#    AccentColor (default blue)          #0078D4
#    SubtleAccentFill (hover)            rgba(0,120,212,0.10) → #E5F1FB
#    AccentFillColorSelectedTextBackground #0078D4
#    ListViewItemBackgroundSelected      AccentColor 40% → #99C9E8 (resolved on white)
#    SystemFillColorCritical             #C42B1C   (delete red)
#
#  Sidebar (NavigationView pane):
#    NavigationViewContentBackground    #F3F3F3
#    NavigationViewItemForeground        TextFillColorPrimary = #1A1A1A
#    NavigationViewItemBackgroundSelected  SubtleAccentFill lighter → #E5F1FB
#    NavigationViewItemBackgroundPointerOver  rgba(0,0,0,0.0373) → #F6F6F6
#
# ─────────────────────────────────────────────────────────────────────────────

WIN11_LIGHT_QSS = """

/* ── Global reset ───────────────────────────────────────────────────────── */
QWidget {
    background-color: #E8E6E2;
    color: #1A1A1A;
    font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
    font-size: 16px;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
    border: none;
    outline: none;
}

/* ── Main window ─────────────────────────────────────────────────────────── */
QMainWindow {
    background-color: #E8E6E2;
}
QMainWindow::separator {
    background: #D4D2CE;
    width: 1px;
    height: 1px;
}

/* ── Nav bar (arrows + address + search — sits below tab strip) ──────────── */
QWidget#navBar {
    background-color: #E4E2DE;
    border-bottom: 1px solid #D4D2CE;
}
QWidget#navBar QToolButton {
    background: transparent;
    color: #1A1A1A;
    border: none;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 16px;
}
QWidget#navBar QToolButton:hover {
    background-color: rgba(0, 0, 0, 0.0373);
}
QWidget#navBar QToolButton:pressed {
    background-color: rgba(0, 0, 0, 0.0625);
    color: #5C5C5C;
}
QWidget#navBar QToolButton:disabled {
    color: #9E9E9E;
}

/* ── Toolbar (navigation bar) ────────────────────────────────────────────── */
QToolBar {
    background-color: #E4E2DE;
    border: none;
    border-bottom: 1px solid #D4D2CE;
    padding: 4px 5px;
    spacing: 2px;
}
QToolBar QToolButton {
    background: transparent;
    color: #1A1A1A;
    border: none;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 16px;
}
QToolBar QToolButton:hover {
    background-color: rgba(0, 0, 0, 0.0373);
}
QToolBar QToolButton:pressed {
    background-color: rgba(0, 0, 0, 0.0625);
    color: #5C5C5C;
}
QToolBar QToolButton:disabled {
    color: #9E9E9E;
}

/* ── Custom title bar ───────────────────────────────────────────────────── */
QWidget#titleBar {
    background-color: #E4E2DE;
    border-bottom: 1px solid #D4D2CE;
}
QLabel#titleLabel {
    color: #1A1A1A;
    font-size: 14px;
    font-weight: 500;
    background: transparent;
}
QToolButton#winMin, QToolButton#winMax {
    background: transparent;
    color: #1A1A1A;
    border: none;
}
QToolButton#winMin:hover, QToolButton#winMax:hover {
    background-color: rgba(0, 0, 0, 0.0578);
}
QToolButton#winMin:pressed, QToolButton#winMax:pressed {
    background-color: rgba(0, 0, 0, 0.0900);
    color: #5C5C5C;
}
QToolButton#winClose {
    background: transparent;
    color: #1A1A1A;
    border: none;
}
QToolButton#winClose:hover {
    background-color: #C42B1C;
    color: #FFFFFF;
}
QToolButton#winClose:pressed {
    background-color: #A32314;
    color: #FFFFFF;
}

/* ── Tab widget & tab bar ────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background-color: #E8E6E2;
}
QTabBar {
    background-color: #E4E2DE;
    border-bottom: 1px solid #D4D2CE;
}
QTabBar::tab {
    background: transparent;
    color: #5C5C5C;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 7px 19px;
    margin: 0px;
    min-width: 204px;
    max-width: 204px;
    font-size: 16px;
    font-weight: 400;
}
QTabBar::tab:selected {
    color: #1A1A1A;
    border-bottom: 2px solid #0078D4;
    min-width: 204px;
    max-width: 204px;
    background: transparent;
}
QTabBar::tab:hover:!selected {
    color: #1A1A1A;
    background-color: rgba(0, 0, 0, 0.0373);
    min-width: 204px;
    max-width: 204px;
    border-radius: 5px 5px 0 0;
}


/* ── Command bar (tool strip) ────────────────────────────────────────────── */
QWidget#commandBar {
    background-color: #E4E2DE;
    border-bottom: 1px solid #D4D2CE;
}
QWidget#commandBar QPushButton {
    background: transparent;
    color: #1A1A1A;
    border: none;
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 16px;
    font-weight: 500;

}
QWidget#commandBar QPushButton:hover:enabled {
    background-color: rgba(0, 0, 0, 0.0373);
}
QWidget#commandBar QPushButton:pressed:enabled {
    background-color: rgba(0, 0, 0, 0.0625);
    color: #5C5C5C;
}
QWidget#commandBar QPushButton:disabled {
    color: #9E9E9E;
}
QWidget#commandBar QPushButton:checked {
    background-color: rgba(0, 0, 0, 0.0578);
    border: 1px solid #C4C2BE;
}
QWidget#commandBar QFrame {
    color: #D4D2CE;
    background-color: #D4D2CE;
}

/* ── Splitter ────────────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #D4D2CE;
}
QSplitter::handle:horizontal {
    width: 1px;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
QWidget#sidebar {
    background-color: #E8E6E2;
    border-right: 1px solid #D4D2CE;
}
QWidget#sidebar QLabel {
    color: #5C5C5C;
    font-size: 16px;
    font-weight: 400;
    letter-spacing: 0.10px;
    background: transparent;
    padding: 0 12px;
}
QWidget#sidebar QPushButton {
    background: transparent;
    color: #1A1A1A;
    border: none;
    border-radius: 5px;
    text-align: left;
    padding: 4px 30px;
    font-size: 16px;
    font-weight: 500;
    margin: 1px 7px;
}
QWidget#sidebar QPushButton:hover {
    background-color: rgba(0, 0, 0, 0.0373);
}
QWidget#sidebar QPushButton:pressed {
    background-color: rgba(0, 0, 0, 0.0625);
    color: #5C5C5C;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    background: transparent;
    width: 7px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(0, 0, 0, 0.20);
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(0, 0, 0, 0.35);
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
    height: 0px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 7px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: rgba(0, 0, 0, 0.20);
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(0, 0, 0, 0.35);
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    background: none;
    width: 0px;
}

/* ── File list (QTreeView) ───────────────────────────────────────────────── */
QTreeView {
    background-color: #E8E6E2;
    alternate-background-color: #E8E6E2;
    border: none;
    show-decoration-selected: 1;
    outline: 0;
    font-size: 18px;
    font-weight: 300;
}
QTreeView::item {
    height: 38px;
    border-radius: 0px;
    margin: 0px;
    padding: 0px 5px;
}
QTreeView::item:hover {
    background-color: rgba(0, 0, 0, 0.0373);
}
QTreeView::item:selected {
    background-color: #C5D8EF;
    color: #1A1A1A;
    border-radius: 0px;
}
QTreeView::item:selected:active {
    background-color: #C5D8EF;
    color: #1A1A1A;
    border-radius: 0px;
}
QTreeView::item:selected:!active {
    background-color: #D4E4F2;
    color: #1A1A1A;
    border-radius: 0px;
}
QHeaderView {
    background-color: #E8E6E2;
    border: none;
    border-bottom: 1px solid #D4D2CE;
}
QHeaderView::section {
    background-color: #E8E6E2;
    color: #5C5C5C;
    border: none;
    border-right: 1px solid #D4D2CE;
    padding: 5px 10px;
    font-size: 14px;
    height: 24px;
}
QHeaderView::section:hover {
    background-color: rgba(0, 0, 0, 0.0373);
    color: #1A1A1A;
}
QHeaderView::section:first {
    border-left: none;
}
QHeaderView::section:last {
    border-right: none;
}
QHeaderView::down-arrow {
    image: none;
    width: 0;
}
QHeaderView::up-arrow {
    image: none;
    width: 0;
}

/* ── Breadcrumb / address bar ────────────────────────────────────────────── */
QWidget#crumbPage {
    background-color: #EDECEA;
    border: 1px solid #C4C2BE;
    border-radius: 5px;
}
QWidget#crumbPage:hover {
    border-color: #A09080;
}
QWidget#crumbPage QPushButton {
    background: transparent;
    color: #1A1A1A;
    border: none;
    border-radius: 4px;
    padding: 2px 0;
    font-size: 16px;
    font-weight: 700;
}
QWidget#crumbPage QPushButton:hover {
    background-color: rgba(0, 0, 0, 0.0578);
}
QWidget#crumbPage QPushButton:pressed {
    background-color: rgba(0, 0, 0, 0.0916);
}
QLineEdit {
    background-color: #EDECEA;
    color: #1A1A1A;
    border: 2px solid #0078D4;
    border-radius: 5px;
    padding: 2px 10px;
    font-size: 16px;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
}
QLineEdit:hover {
    border-color: #0078D4;
}

/* ── Menus ───────────────────────────────────────────────────────────────── */
QMenu {
    background-color: #EDECEA;
    border: 1px solid #C4C2BE;
    border-radius: 10px;
}
QMenu::item {
    background: transparent;
    color: #1A1A1A;
    border-radius: 5px;
    padding: 8px 34px 8px 14px;
    font-size: 18px;
    font-weight: 300;
}
QMenu::item:selected {
    background-color: rgba(0, 0, 0, 0.0373);
    color: #1A1A1A;
}
QMenu::item:disabled {
    color: #9E9E9E;
}
QMenu::separator {
    height: 1px;
    background: #D4D2CE;
    margin: 5px 10px;
}
QMenu::indicator {
    width: 19px;
    height: 19px;
    margin-left: 5px;
}
QMenu::indicator:checked {
    image: none;
}
QMenu::indicator:checked {
    background-color: gray;
    border-radius: 4px;
}

/* ── Dialogs ─────────────────────────────────────────────────────────────── */
QDialog {
    background-color: #E8E6E2;
}
QFormLayout QLabel {
    color: green;
    font-size: 14px;
}
QDialogButtonBox QPushButton,
QDialog QPushButton {
    background-color: #E4E2DE;
    color: #1A1A1A;
    border: 1px solid #C4C2BE;
    border-radius: 5px;
    padding: 6px 19px;
    font-size: 16px;
    min-width: 96px;
}
QDialogButtonBox QPushButton:hover,
QDialog QPushButton:hover {
    background-color: #E8E6E2;
    border-color: #A09080;
}
QDialogButtonBox QPushButton:pressed,
QDialog QPushButton:pressed {
    background-color: #DCDBD8;
    color: #5C5C5C;
}
QDialogButtonBox QPushButton:default,
QDialog QPushButton:default {
    background-color: #0078D4;
    color: #FFFFFF;
    border: none;
}
QDialogButtonBox QPushButton:default:hover,
QDialog QPushButton:default:hover {
    background-color: #1A86DC;
}
QDialogButtonBox QPushButton:default:pressed,
QDialog QPushButton:default:pressed {
    background-color: #006CBD;
}

/* ── Message boxes ───────────────────────────────────────────────────────── */
QMessageBox {
    background-color: #E8E6E2;
}
QMessageBox QLabel {
    color: #1A1A1A;
    font-size: 16px;
}

/* ── Search bar ──────────────────────────────────────────────────────────── */
QWidget#searchBar {
    background-color: #EDECEA;
    border: 1px solid #C4C2BE;
    border-radius: 5px;
}
QWidget#searchBar:hover {
    border-color: #A09080;
}
QWidget#searchBar[active="true"] {
    border: 2px solid #0078D4;
}
QWidget#searchBar QLineEdit {
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 0px 2px;
    font-size: 16px;
    color: #1A1A1A;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
}
QWidget#searchBar QPushButton {
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 2px;
    color: #5C5C5C;
    font-size: 16px;
}
QWidget#searchBar QPushButton:hover {
    background-color: rgba(0, 0, 0, 0.0578);
    color: #1A1A1A;
}

/* ── Input dialog ────────────────────────────────────────────────────────── */
QInputDialog {
    background-color: #E8E6E2;
}
QInputDialog QLabel {
    color: #1A1A1A;
}
QInputDialog QLineEdit {
    background-color: #EDECEA;
    border: 1px solid #C4C2BE;
    border-radius: 5px;
    padding: 6px 10px;
}
QInputDialog QLineEdit:focus {
    border: 2px solid #0078D4;
}

/* ── List widget (open-with dialog) ──────────────────────────────────────── */
QListWidget {
    background-color: #EDECEA;
    border: 1px solid #C4C2BE;
    border-radius: 5px;
    outline: 0;
}
QListWidget::item {
    border-radius: 5px;
    padding: 6px 10px;
    margin: 1px 4px;
    color: #1A1A1A;
}
QListWidget::item:hover {
    background-color: rgba(0, 0, 0, 0.0373);
}
QListWidget::item:selected {
    background-color: #C5D8EF;
    color: #1A1A1A;
}

/* ── Details panel ───────────────────────────────────────────────────────── */
QWidget#detailsPanel {
    background-color: #E4E2DE;
    border-left: 1px solid #D4D2CE;
}
QWidget#detailsPanel QLabel {
    background: transparent;
    color: #1A1A1A;
}

/* ── Tooltip ─────────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #EDECEA;
    color: #1A1A1A;
    border: 1px solid #C4C2BE;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 14px;
}

"""

# ═══════════════════════════════════════════════════════════════════════════════
#  WIN 11 DARK THEME
# ═══════════════════════════════════════════════════════════════════════════════
WIN11_DARK_QSS = """

/* ── Global reset ───────────────────────────────────────────────────────── */
QWidget {
    background-color: #202020;
    color: #FFFFFF;
    font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
    font-size: 16px;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
    border: none;
    outline: none;
}

/* ── Main window ─────────────────────────────────────────────────────────── */
QMainWindow {
    background-color: #202020;
}
QMainWindow::separator {
    background: #3A3A3A;
    width: 1px;
    height: 1px;
}

/* ── Custom title bar ───────────────────────────────────────────────────── */
QWidget#titleBar {
    background-color: #202020;
    border-bottom: 1px solid #3A3A3A;
}
QLabel#titleLabel {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 500;
    background: transparent;
}
QToolButton#winMin, QToolButton#winMax {
    background-color: #202020;
    color: #FFFFFF;
    border: none;
}
QToolButton#winMin:hover, QToolButton#winMax:hover {
    background-color: rgba(255, 255, 255, 0.0800);
}
QToolButton#winMin:pressed, QToolButton#winMax:pressed {
    background-color: rgba(255, 255, 255, 0.0419);
    color: #ABABAB;
}
QToolButton#winClose {
    background-color: #202020;
    color: #FFFFFF;
    border: none;
}
QToolButton#winClose:hover {
    background-color: #C42B1C;
    color: #FFFFFF;
}
QToolButton#winClose:pressed {
    background-color: #A32314;
    color: #FFFFFF;
}

/* ── Nav bar (arrows + address + search — sits below tab strip) ──────────── */
QWidget#navBar {
    background-color: #2C2C2C;
    border-bottom: 1px solid #3A3A3A;
}
QWidget#navBar QToolButton {
    background: transparent;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 16px;
}
QWidget#navBar QToolButton:hover {
    background-color: rgba(255, 255, 255, 0.0605);
}
QWidget#navBar QToolButton:pressed {
    background-color: rgba(255, 255, 255, 0.0419);
    color: #ABABAB;
}
QWidget#navBar QToolButton:disabled {
    color: #666666;
}

/* ── Toolbar ─────────────────────────────────────────────────────────────── */
QToolBar {
    background-color: #2C2C2C;
    border: none;
    border-bottom: 1px solid #3A3A3A;
    padding: 4px 5px;
    spacing: 2px;
}
QToolBar QToolButton {
    background: transparent;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 16px;
}
QToolBar QToolButton:hover {
    background-color: rgba(255, 255, 255, 0.0605);
}
QToolBar QToolButton:pressed {
    background-color: rgba(255, 255, 255, 0.0419);
    color: #ABABAB;
}
QToolBar QToolButton:disabled {
    color: #666666;
}

/* ── Tab widget & tab bar ────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background-color: #202020;
}
QTabBar {
    background-color: #202020;
    border-bottom: 1px solid #3A3A3A;
}
QTabBar::tab {
    background: transparent;
    color: #ABABAB;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 7px 19px;
    margin: 0px;
    min-width: 204px;
    max-width: 204px;
    font-size: 16px;
    font-weight: 400;
}
QTabBar::tab:selected {
    color: #FFFFFF;
    border-bottom: 2px solid #0078D4;
    min-width: 204px;
    max-width: 204px;
    background: transparent;
}
QTabBar::tab:hover:!selected {
    color: #FFFFFF;
    background-color: rgba(255, 255, 255, 0.0605);
    min-width: 204px;
    max-width: 204px;
    border-radius: 5px 5px 0 0;
}

/* ── Command bar ─────────────────────────────────────────────────────────── */
QWidget#commandBar {
    background-color: #2C2C2C;
    border-bottom: 1px solid #3A3A3A;
}
QWidget#commandBar QPushButton {
    background: transparent;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 16px;
    font-weight: 500;
}
QWidget#commandBar QPushButton:hover:enabled {
    background-color: rgba(255, 255, 255, 0.0605);
}
QWidget#commandBar QPushButton:pressed:enabled {
    background-color: rgba(255, 255, 255, 0.0419);
    color: #ABABAB;
}
QWidget#commandBar QPushButton:disabled {
    color: #666666;
}
QWidget#commandBar QPushButton:checked {
    background-color: rgba(255, 255, 255, 0.0837);
    border: 1px solid #4A4A4A;
}
QWidget#commandBar QFrame {
    color: #3A3A3A;
    background-color: #3A3A3A;
}

/* ── Splitter ────────────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #3A3A3A;
}
QSplitter::handle:horizontal {
    width: 1px;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
QWidget#sidebar {
    background-color: #202020;
    border-right: 1px solid #3A3A3A;
}
QWidget#sidebar QLabel {
    color: #ABABAB;
    font-size: 16px;
    font-weight: 400;
    letter-spacing: 0.10px;
    background: transparent;
    padding: 0 12px;
}
QWidget#sidebar QPushButton {
    background: transparent;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    text-align: left;
    padding: 4px 30px;
    font-size: 16px;
    font-weight: 500;
    margin: 1px 7px;
}
QWidget#sidebar QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.0605);
}
QWidget#sidebar QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.0419);
    color: #ABABAB;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    background: transparent;
    width: 7px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.18);
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.32);
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
    height: 0px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 7px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.18);
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 0.32);
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    background: none;
    width: 0px;
}

/* ── File list (QTreeView) ───────────────────────────────────────────────── */
QTreeView {
    background-color: #202020;
    alternate-background-color: #202020;
    border: none;
    show-decoration-selected: 1;
    outline: 0;
    font-size: 18px;
    font-weight: 300;
}
QTreeView::item {
    height: 38px;
    border-radius: 0px;
    margin: 0px;
    padding: 0px 5px;
}
QTreeView::item:hover {
    background-color: rgba(255, 255, 255, 0.0605);
}
QTreeView::item:selected {
    background-color: #2D4F6C;
    color: #FFFFFF;
    border-radius: 0px;
}
QTreeView::item:selected:active {
    background-color: #2D4F6C;
    color: #FFFFFF;
    border-radius: 0px;
}
QTreeView::item:selected:!active {
    background-color: #263D54;
    color: #FFFFFF;
    border-radius: 0px;
}
QHeaderView {
    background-color: #202020;
    border: none;
    border-bottom: 1px solid #3A3A3A;
}
QHeaderView::section {
    background-color: #202020;
    color: #ABABAB;
    border: none;
    border-right: 1px solid #3A3A3A;
    padding: 5px 10px;
    font-size: 14px;
    height: 24px;
}
QHeaderView::section:hover {
    background-color: rgba(255, 255, 255, 0.0605);
    color: #FFFFFF;
}
QHeaderView::section:first {
    border-left: none;
}
QHeaderView::section:last {
    border-right: none;
}
QHeaderView::down-arrow {
    image: none;
    width: 0;
}
QHeaderView::up-arrow {
    image: none;
    width: 0;
}

/* ── Breadcrumb / address bar ────────────────────────────────────────────── */
QWidget#crumbPage {
    background-color: #3A3A3A;
    border: 1px solid #555555;
    border-radius: 5px;
}
QWidget#crumbPage:hover {
    border-color: #707070;
}
QWidget#crumbPage QPushButton {
    background: transparent;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 2px 0;
    font-size: 16px;
    font-weight: 700;
}
QWidget#crumbPage QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.0837);
}
QWidget#crumbPage QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.0605);
}
QLineEdit {
    background-color: #3A3A3A;
    color: #FFFFFF;
    border: 2px solid #0078D4;
    border-radius: 5px;
    padding: 2px 10px;
    font-size: 16px;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
}
QLineEdit:hover {
    border-color: #0078D4;
}

/* ── Menus ───────────────────────────────────────────────────────────────── */
QMenu {
    background-color: #2C2C2C;
    border: 1px solid #4A4A4A;
    border-radius: 10px;
}
QMenu::item {
    background: transparent;
    color: #FFFFFF;
    border-radius: 5px;
    padding: 8px 34px 8px 14px;
    font-size: 18px;
    font-weight: 300;
}
QMenu::item:selected {
    background-color: rgba(255, 255, 255, 0.0605);
    color: #FFFFFF;
}
QMenu::item:disabled {
    color: #666666;
}
QMenu::separator {
    height: 1px;
    background: #3A3A3A;
    margin: 5px 10px;
}
QMenu::indicator {
    width: 19px;
    height: 19px;
    margin-left: 5px;
}
QMenu::indicator:checked {
    image: none;
}
QMenu::indicator:checked {
    background-color: gray;
    border-radius: 4px;
}

/* ── Dialogs ─────────────────────────────────────────────────────────────── */
QDialog {
    background-color: #202020;
}
QFormLayout QLabel {
    color: #4EC94E;
    font-size: 14px;
}
QDialogButtonBox QPushButton,
QDialog QPushButton {
    background-color: #2C2C2C;
    color: #FFFFFF;
    border: 1px solid #4A4A4A;
    border-radius: 5px;
    padding: 6px 19px;
    font-size: 16px;
    min-width: 96px;
}
QDialogButtonBox QPushButton:hover,
QDialog QPushButton:hover {
    background-color: #383838;
    border-color: #707070;
}
QDialogButtonBox QPushButton:pressed,
QDialog QPushButton:pressed {
    background-color: #262626;
    color: #ABABAB;
}
QDialogButtonBox QPushButton:default,
QDialog QPushButton:default {
    background-color: #0078D4;
    color: #FFFFFF;
    border: none;
}
QDialogButtonBox QPushButton:default:hover,
QDialog QPushButton:default:hover {
    background-color: #1A86DC;
}
QDialogButtonBox QPushButton:default:pressed,
QDialog QPushButton:default:pressed {
    background-color: #006CBD;
}

/* ── Message boxes ───────────────────────────────────────────────────────── */
QMessageBox {
    background-color: #202020;
}
QMessageBox QLabel {
    color: #FFFFFF;
    font-size: 16px;
}

/* ── Search bar ──────────────────────────────────────────────────────────── */
QWidget#searchBar {
    background-color: #3A3A3A;
    border: 1px solid #555555;
    border-radius: 5px;
}
QWidget#searchBar:hover {
    border-color: #707070;
}
QWidget#searchBar[active="true"] {
    border: 2px solid #0078D4;
}
QWidget#searchBar QLineEdit {
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 0px 2px;
    font-size: 16px;
    color: #FFFFFF;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
}
QWidget#searchBar QPushButton {
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 2px;
    color: #ABABAB;
    font-size: 16px;
}
QWidget#searchBar QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.0837);
    color: #FFFFFF;
}

/* ── Input dialog ────────────────────────────────────────────────────────── */
QInputDialog {
    background-color: #202020;
}
QInputDialog QLabel {
    color: #FFFFFF;
}
QInputDialog QLineEdit {
    background-color: #3A3A3A;
    border: 1px solid #555555;
    border-radius: 5px;
    padding: 6px 10px;
    color: #FFFFFF;
}
QInputDialog QLineEdit:focus {
    border: 2px solid #0078D4;
}

/* ── List widget ─────────────────────────────────────────────────────────── */
QListWidget {
    background-color: #2C2C2C;
    border: 1px solid #4A4A4A;
    border-radius: 5px;
    outline: 0;
}
QListWidget::item {
    border-radius: 5px;
    padding: 6px 10px;
    margin: 1px 4px;
    color: #FFFFFF;
}
QListWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.0605);
}
QListWidget::item:selected {
    background-color: #2D4F6C;
    color: #FFFFFF;
}

/* ── Details panel ───────────────────────────────────────────────────────── */
QWidget#detailsPanel {
    background-color: #2C2C2C;
    border-left: 1px solid #3A3A3A;
}
QWidget#detailsPanel QLabel {
    background: transparent;
    color: #FFFFFF;
}

/* ── Tooltip ─────────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #2C2C2C;
    color: #FFFFFF;
    border: 1px solid #4A4A4A;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 14px;
}

"""



def _apply_win11_dark_palette(app: "QApplication"):
    """Set the QPalette to match Win11 dark colours."""
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor("#202020"))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.Base,            QColor("#2C2C2C"))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor("#202020"))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#2C2C2C"))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.Text,            QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.BrightText,      QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#666666"))
    pal.setColor(QPalette.ColorRole.Button,          QColor("#2C2C2C"))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor("#0078D4"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.Mid,             QColor("#3A3A3A"))
    pal.setColor(QPalette.ColorRole.Midlight,        QColor("#2C2C2C"))
    pal.setColor(QPalette.ColorRole.Dark,            QColor("#181818"))
    pal.setColor(QPalette.ColorRole.Shadow,          QColor("#101010"))
    pal.setColor(QPalette.ColorRole.Light,           QColor("#4A4A4A"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#666666"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor("#666666"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#666666"))
    app.setPalette(pal)


def _apply_win11_palette(app: "QApplication"):
    """Set the QPalette to match warm greige light colours so native widgets blend in."""
    pal = QPalette()
    # Window / base surfaces
    pal.setColor(QPalette.ColorRole.Window,          QColor("#E8E6E2"))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor("#1A1A1A"))
    pal.setColor(QPalette.ColorRole.Base,            QColor("#EDECEA"))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor("#E8E6E2"))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#EDECEA"))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor("#1A1A1A"))
    # Text
    pal.setColor(QPalette.ColorRole.Text,            QColor("#1A1A1A"))
    pal.setColor(QPalette.ColorRole.BrightText,      QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9A8C7C"))
    # Buttons
    pal.setColor(QPalette.ColorRole.Button,          QColor("#E4E2DE"))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor("#1A1A1A"))
    # Highlights
    pal.setColor(QPalette.ColorRole.Highlight,       QColor("#0078D4"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    # Borders / midtones
    pal.setColor(QPalette.ColorRole.Mid,             QColor("#D4D2CE"))
    pal.setColor(QPalette.ColorRole.Midlight,        QColor("#E2E0DC"))
    pal.setColor(QPalette.ColorRole.Dark,            QColor("#C4C2BE"))
    pal.setColor(QPalette.ColorRole.Shadow,          QColor("#C0AE98"))
    pal.setColor(QPalette.ColorRole.Light,           QColor("#EDECEA"))
    # Disabled group — keep readable
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.WindowText,      QColor("#9E9E9E"))
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.Text,            QColor("#9E9E9E"))
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.ButtonText,      QColor("#9E9E9E"))
    app.setPalette(pal)


# ═══════════════════════════════════════════════════════════════════════════════
#  FLUENT ICON FONT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
#
#  Win11 uses Segoe Fluent Icons (Win11+) with MDL2 Assets as fallback.
#  On Linux these fonts must be installed; if absent we fall back gracefully
#  to the system UI font (codepoints render as squares but layout is fine).
#
#  Priority: Segoe Fluent Icons -> Segoe MDL2 Assets -> Segoe UI Symbol


def _fluent_font(size: int = 14) -> QFont:
    """Return a QFont set to the best available Fluent icon font."""
    f = QFont()
    f.setFamilies(["Segoe Fluent Icons", "Segoe MDL2 Assets", "Segoe UI Symbol"])
    f.setPixelSize(size)
    return f


def _apply_fluent_icon(widget, icon_cp: str, label: str = "", icon_size: int = 17):
    """Set widget text to glyph+label and apply the Fluent icon font."""
    widget.setText(f"{icon_cp}  {label}" if label else icon_cp)
    widget.setFont(_fluent_font(icon_size))


# ═══════════════════════════════════════════════════════════════════════════════
#  ICON RESOLVER
# ═══════════════════════════════════════════════════════════════════════════════

# Map extension → XDG theme icon name (fallback chain)
EXT_ICON_MAP: dict[str, str] = {
    # Images
    ".jpg": "image-jpeg", ".jpeg": "image-jpeg", ".png": "image-png",
    ".gif": "image-gif",  ".bmp": "image-bmp",   ".svg": "image-svg+xml",
    ".webp":"image-webp", ".tiff":"image-tiff",  ".ico": "image-x-ico",
    # Video
    ".mp4": "video-mp4",  ".mkv": "video-x-matroska", ".avi": "video-x-msvideo",
    ".mov": "video-quicktime", ".webm":"video-webm",   ".flv": "video-x-flv",
    ".wmv": "video-x-ms-wmv",
    # Audio
    ".mp3": "audio-mpeg", ".flac":"audio-flac",  ".wav": "audio-x-wav",
    ".ogg": "audio-ogg",  ".aac": "audio-aac",   ".m4a": "audio-mp4",
    # Documents
    ".pdf": "application-pdf",
    ".doc": "application-msword",       ".docx": "application-msword",
    ".xls": "application-vnd.ms-excel", ".xlsx": "application-vnd.ms-excel",
    ".ppt": "application-vnd.ms-powerpoint",
    ".pptx":"application-vnd.ms-powerpoint",
    ".odt": "application-vnd.oasis.opendocument.text",
    ".ods": "application-vnd.oasis.opendocument.spreadsheet",
    ".odp": "application-vnd.oasis.opendocument.presentation",
    # Code / text
    ".py":  "text-x-python",  ".js":  "application-javascript",
    ".ts":  "text-x-typescript", ".html":"text-html", ".css":"text-css",
    ".json":"application-json",  ".xml": "text-xml",
    ".sh":  "application-x-shellscript", ".md": "text-x-markdown",
    ".txt": "text-plain",
    # Archives
    ".zip": "application-zip", ".tar": "application-x-tar",
    ".gz":  "application-gzip",".rar": "application-x-rar",
    ".7z":  "application-x-7z-compressed",
    # Executables / packages
    ".deb": "application-x-deb", ".rpm":"application-x-rpm",
    ".AppImage": "application-x-executable",
}

# Friendly generic fallbacks per broad MIME category
GENERIC_FALLBACKS = [
    ("image/",       "image-x-generic"),
    ("video/",       "video-x-generic"),
    ("audio/",       "audio-x-generic"),
    ("text/",        "text-x-generic"),
    ("application/", "application-x-generic"),
]

_icon_cache: dict[str, QIcon] = {}

# ═══════════════════════════════════════════════════════════════════════════════
#  BUILT-IN CUSTOM ICONS
# ═══════════════════════════════════════════════════════════════════════════════

def _doc_base(p, px, size, body_color, fold_color="#FFFFFF"):
    """
    Minimal document base: clean body with a subtle folded top-right corner.
    Thinner strokes, no shadow, more whitespace. Returns (m, w, h, fold).
    """
    from PyQt6.QtCore import QRectF
    m    = size * 0.12
    w    = size * 0.76
    h    = size * 0.86
    fold = size * 0.18
    r    = size * 0.08

    # body
    body = QPainterPath()
    body.moveTo(m + r, m)
    body.lineTo(m + w - fold, m)
    body.lineTo(m + w, m + fold)
    body.lineTo(m + w, m + h - r)
    body.quadTo(m + w, m + h, m + w - r, m + h)
    body.lineTo(m + r, m + h)
    body.quadTo(m, m + h, m, m + h - r)
    body.lineTo(m, m + r)
    body.quadTo(m, m, m + r, m)
    body.closeSubpath()
    p.fillPath(body, QBrush(QColor(body_color)))

    # fold triangle
    tri = QPainterPath()
    tri.moveTo(m + w - fold, m)
    tri.lineTo(m + w - fold, m + fold)
    tri.lineTo(m + w,        m + fold)
    tri.closeSubpath()
    p.fillPath(tri, QBrush(QColor(fold_color)))

    # single clean crease line
    pen = QPen(QColor(0, 0, 0, 18), max(1, size * 0.010))
    p.setPen(pen)
    p.drawLine(int(m + w - fold), int(m), int(m + w - fold), int(m + fold))
    p.drawLine(int(m + w - fold), int(m + fold), int(m + w), int(m + fold))
    p.setPen(Qt.PenStyle.NoPen)

    return m, w, h, fold


def _make_folder_icon(size: int = 256) -> QIcon:
    """Minimal folder — clean flat shape, two-tone, no gradients."""
    from PyQt6.QtCore import QRectF
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    s = size
    m = s * 0.06
    r = s * 0.10

    # back panel
    back = QPainterPath()
    back.addRoundedRect(m, s * 0.30, s * 0.88, s * 0.60, r, r)
    p.fillPath(back, QBrush(QColor("#D4A017")))

    # tab — small, clean, left-aligned
    tab = QPainterPath()
    tab.addRoundedRect(m, s * 0.22, s * 0.32, s * 0.12, r * 0.5, r * 0.5)
    p.fillPath(tab, QBrush(QColor("#D4A017")))

    # front panel — slightly lighter
    front = QPainterPath()
    front.addRoundedRect(m, s * 0.34, s * 0.88, s * 0.56, r, r)
    p.fillPath(front, QBrush(QColor("#F0C030")))

    p.end()
    return QIcon(px)


def _make_generic_file_icon(size: int = 256) -> QIcon:
    """Minimal plain file icon — white body, light fold, three content lines."""
    from PyQt6.QtCore import QRectF
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    m, w, h, fold = _doc_base(p, px, size, "#F5F5F5", "#E0E0E0")

    # two clean content lines
    lx = m + w * 0.16;  ly = m + h * 0.50
    lw = w * 0.58;       lh = size * 0.040; lgap = size * 0.080
    lr = lh / 2
    for i in range(2):
        lp = QPainterPath()
        lp.addRoundedRect(lx, ly + i * lgap, lw if i == 0 else lw * 0.70, lh, lr, lr)
        p.fillPath(lp, QBrush(QColor("#D0D0D0")))

    p.end()
    return QIcon(px)


def _make_pdf_icon(size: int = 256) -> QIcon:
    """Minimal PDF icon — clean white doc, small red accent badge."""
    from PyQt6.QtCore import QRectF
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    m, w, h, fold = _doc_base(p, px, size, "#FFFFFF", "#FFD0CC")

    # small red pill badge at bottom
    bx = m + w * 0.10;  by = m + h * 0.60
    bw = w * 0.72;       bh = h * 0.24;  br = bh / 2
    bp = QPainterPath()
    bp.addRoundedRect(bx, by, bw, bh, br, br)
    p.fillPath(bp, QBrush(QColor("#E53935")))

    font = QFont("Arial", int(size * 0.155), QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QPen(QColor("#FFFFFF")))
    from PyQt6.QtCore import QRectF
    p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, "PDF")

    p.end()
    return QIcon(px)


def _make_image_icon(size: int = 256) -> QIcon:
    """Minimal image icon — white doc with a simple landscape glyph."""
    from PyQt6.QtCore import QRectF, QPointF
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    m, w, h, fold = _doc_base(p, px, size, "#FFFFFF", "#E8EEF4")

    # thumbnail area — light blue-grey background
    tx = m + w * 0.12;  ty = m + h * 0.28
    tw = w * 0.68;       th = h * 0.46;  tr = size * 0.03
    clip = QPainterPath()
    clip.addRoundedRect(tx, ty, tw, th, tr, tr)
    p.fillPath(clip, QBrush(QColor("#E8F4FD")))

    # simple mountain shape
    p.setClipPath(clip)
    mtn = QPainterPath()
    mtn.moveTo(tx, ty + th)
    mtn.lineTo(tx + tw * 0.38, ty + th * 0.42)
    mtn.lineTo(tx + tw * 0.62, ty + th * 0.65)
    mtn.lineTo(tx + tw * 0.78, ty + th * 0.48)
    mtn.lineTo(tx + tw, ty + th * 0.72)
    mtn.lineTo(tx + tw, ty + th)
    mtn.closeSubpath()
    p.fillPath(mtn, QBrush(QColor("#90CAF9")))

    # circle sun
    p.setBrush(QBrush(QColor("#FFE082")))
    sr = size * 0.06
    p.drawEllipse(QPointF(tx + tw * 0.22, ty + th * 0.28), sr, sr)

    p.setClipping(False)
    p.end()
    return QIcon(px)


def _make_video_icon(size: int = 256) -> QIcon:
    """Minimal video icon — white doc with a clean indigo play badge."""
    from PyQt6.QtCore import QRectF, QPointF
    from PyQt6.QtGui import QPolygonF
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    m, w, h, fold = _doc_base(p, px, size, "#FFFFFF", "#EDE7F6")

    # clean indigo circle badge
    cx2 = m + w * 0.46
    cy2 = m + h * 0.60
    cr  = h * 0.22
    circle = QPainterPath()
    circle.addEllipse(QPointF(cx2, cy2), cr, cr)
    p.fillPath(circle, QBrush(QColor("#5C6BC0")))

    # white play triangle (slightly right-offset for visual centering)
    tr  = cr * 0.42
    poly = QPolygonF([
        QPointF(cx2 - tr * 0.55, cy2 - tr),
        QPointF(cx2 - tr * 0.55, cy2 + tr),
        QPointF(cx2 + tr * 0.90, cy2),
    ])
    play = QPainterPath()
    play.addPolygon(poly)
    play.closeSubpath()
    p.fillPath(play, QBrush(QColor("#FFFFFF")))

    p.end()
    return QIcon(px)


def _make_iso_icon(size: int = 256) -> QIcon:
    """Win11-style ISO icon — white document with a grey disc badge."""
    from PyQt6.QtCore import QRectF, QPointF
    from PyQt6.QtGui import QRadialGradient
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    m, w, h, fold = _doc_base(p, px, size, "#FFFFFF", "#E0E0E0")

    # disc circle
    cx2 = m + w * 0.46
    cy2 = m + h * 0.60
    dr  = size * 0.22
    rg  = QRadialGradient(cx2 - dr * 0.2, cy2 - dr * 0.2, dr * 1.1)
    rg.setColorAt(0.0, QColor("#E0E0E0"))
    rg.setColorAt(1.0, QColor("#9E9E9E"))
    disc = QPainterPath()
    disc.addEllipse(QPointF(cx2, cy2), dr, dr)
    p.fillPath(disc, QBrush(rg))

    # hole
    hole = QPainterPath()
    hole.addEllipse(QPointF(cx2, cy2), dr * 0.20, dr * 0.20)
    p.fillPath(hole, QBrush(QColor("#F5F5F5")))

    # disc border
    p.setPen(QPen(QColor(0, 0, 0, 25), size * 0.014))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(cx2, cy2), dr, dr)
    p.setPen(Qt.PenStyle.NoPen)

    # "ISO" text
    font = QFont("Arial", int(size * 0.13), QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QPen(QColor("#555555")))
    p.drawText(QRectF(cx2 - dr, cy2 - dr * 0.38, dr * 2, dr * 0.76),
               Qt.AlignmentFlag.AlignCenter, "ISO")

    p.end()
    return QIcon(px)


def _make_archive_icon(size: int = 256) -> QIcon:
    """Win11-style archive icon — white document with a teal zip badge."""
    from PyQt6.QtCore import QRectF
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    m, w, h, fold = _doc_base(p, px, size, "#FFFFFF", "#D0F0EC")

    # teal rounded badge
    bx = m + w * 0.12;  by = m + h * 0.36
    bw = w * 0.68;       bh = h * 0.42;  br = size * 0.055
    badge = QPainterPath()
    badge.addRoundedRect(bx, by, bw, bh, br, br)
    p.fillPath(badge, QBrush(QColor("#00897B")))

    # zipper teeth (two columns of white rounded rects)
    tw = bw * 0.16;  th = bh * 0.13;  tgap = bh * 0.18;  tr2 = th * 0.4
    col_l = bx + bw * 0.28;  col_r = bx + bw * 0.54
    ty0   = by + bh * 0.13
    for i in range(4):
        for cx3 in (col_l, col_r):
            tp = QPainterPath()
            tp.addRoundedRect(cx3, ty0 + i * tgap, tw, th, tr2, tr2)
            p.fillPath(tp, QBrush(QColor("#FFFFFF")))

    # "ZIP" label
    font = QFont("Arial", int(size * 0.115), QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QPen(QColor("#FFFFFF")))
    p.drawText(QRectF(bx, by + bh * 0.56, bw, bh * 0.38),
               Qt.AlignmentFlag.AlignCenter, "ZIP")

    p.end()
    return QIcon(px)


# Per-path thumbnail cache for the icon-view image previews.
# Maps absolute file path → QPixmap (already cropped/scaled to THUMB_SIZE).
_thumb_cache: dict[str, "QPixmap"] = {}
THUMB_SIZE = 115   # pixels — matches the 110×110 grid with a comfortable margin

# Keys used in _icon_cache for our hand-drawn icons
_BUILTIN_FOLDER_KEY  = "__builtin_folder__"
_BUILTIN_FILE_KEY    = "__builtin_file__"
_BUILTIN_PDF_KEY     = "__builtin_pdf__"
_BUILTIN_IMAGE_KEY   = "__builtin_image__"
_BUILTIN_VIDEO_KEY   = "__builtin_video__"
_BUILTIN_ISO_KEY     = "__builtin_iso__"
_BUILTIN_ARCHIVE_KEY = "__builtin_archive__"
_BUILTIN_PY_KEY      = "__builtin_py__"
_BUILTIN_HTML_KEY    = "__builtin_html__"
_BUILTIN_CSS_KEY     = "__builtin_css__"
_BUILTIN_JS_KEY      = "__builtin_js__"

# Extensions that should use the hand-drawn image icon
_IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".tiff", ".tif", ".ico", ".svg", ".heic", ".avif",
}

_VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm",
    ".flv", ".wmv", ".m4v", ".mpg", ".mpeg", ".3gp",
}

_ARCHIVE_EXTS = {
    ".zip", ".tar", ".gz", ".bz2", ".xz",
    ".rar", ".7z", ".tgz", ".tbz2",
}




def _make_code_icon(size: int, badge_color: str, label: str,
                    body_color: str = "#FFFFFF", fold_color: str = "#E8EEF4") -> QIcon:
    """Shared helper: white doc with a coloured pill badge and a short label."""
    from PyQt6.QtCore import QRectF
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    m, w, h, fold = _doc_base(p, px, size, body_color, fold_color)

    bx = m + w * 0.08;  by = m + h * 0.50
    bw = w * 0.76;       bh = h * 0.30;  br = size * 0.045
    bp = QPainterPath()
    bp.addRoundedRect(bx, by, bw, bh, br, br)
    p.fillPath(bp, QBrush(QColor(badge_color)))

    font = QFont("Arial", int(size * 0.155), QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QPen(QColor("#FFFFFF")))
    p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, label)

    p.end()
    return QIcon(px)


def _make_py_icon(size: int = 256) -> QIcon:
    """Python file — blue/yellow two-tone badge matching Python brand colours."""
    from PyQt6.QtCore import QRectF
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    m, w, h, fold = _doc_base(p, px, size, "#FFFFFF", "#E8F0FE")

    bx = m + w * 0.08;  by = m + h * 0.50
    bw = w * 0.76;       bh = h * 0.30;  br = size * 0.045

    bp = QPainterPath()
    bp.addRoundedRect(bx, by, bw, bh, br, br)
    p.fillPath(bp, QBrush(QColor("#3776AB")))

    clip = QPainterPath()
    clip.addRoundedRect(bx, by, bw, bh, br, br)
    p.setClipPath(clip)
    p.fillPath(_rr(bx + bw * 0.5, by, bw * 0.5, bh, 0), QBrush(QColor("#FFD43B")))
    p.setClipping(False)

    font = QFont("Arial", int(size * 0.155), QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QPen(QColor("#FFFFFF")))
    p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, ".py")

    p.end()
    return QIcon(px)


def _make_html_icon(size: int = 256) -> QIcon:
    """HTML file — orange badge."""
    return _make_code_icon(size, "#E44D26", ".html", "#FFFFFF", "#FDE8E4")


def _make_css_icon(size: int = 256) -> QIcon:
    """CSS file — blue badge."""
    return _make_code_icon(size, "#264DE4", ".css", "#FFFFFF", "#E4EAF8")


def _make_js_icon(size: int = 256) -> QIcon:
    """JavaScript file — yellow badge with dark text."""
    from PyQt6.QtCore import QRectF
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    m, w, h, fold = _doc_base(p, px, size, "#FFFFFF", "#FFF8E1")

    bx = m + w * 0.08;  by = m + h * 0.50
    bw = w * 0.76;       bh = h * 0.30;  br = size * 0.045
    bp = QPainterPath()
    bp.addRoundedRect(bx, by, bw, bh, br, br)
    p.fillPath(bp, QBrush(QColor("#F7DF1E")))

    font = QFont("Arial", int(size * 0.155), QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QPen(QColor("#333333")))
    p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, ".js")

    p.end()
    return QIcon(px)

_icon_provider = QFileIconProvider()


def resolve_icon(path: str, is_dir: bool) -> QIcon:
    """Return the best QIcon for a path, with caching."""
    if is_dir:
        if _BUILTIN_FOLDER_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_FOLDER_KEY] = _make_folder_icon()
        return _icon_cache[_BUILTIN_FOLDER_KEY]

    ext = os.path.splitext(path)[1].lower()
    if ext in _icon_cache:
        return _icon_cache[ext]

    # ── Built-in hand-drawn icons (highest priority) ──
    if ext == ".pdf":
        if _BUILTIN_PDF_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_PDF_KEY] = _make_pdf_icon()
        _icon_cache[ext] = _icon_cache[_BUILTIN_PDF_KEY]
        return _icon_cache[ext]

    if ext in _IMAGE_EXTS:
        if _BUILTIN_IMAGE_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_IMAGE_KEY] = _make_image_icon()
        _icon_cache[ext] = _icon_cache[_BUILTIN_IMAGE_KEY]
        return _icon_cache[ext]

    if ext in _VIDEO_EXTS:
        if _BUILTIN_VIDEO_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_VIDEO_KEY] = _make_video_icon()
        _icon_cache[ext] = _icon_cache[_BUILTIN_VIDEO_KEY]
        return _icon_cache[ext]

    if ext == ".iso":
        if _BUILTIN_ISO_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_ISO_KEY] = _make_iso_icon()
        _icon_cache[ext] = _icon_cache[_BUILTIN_ISO_KEY]
        return _icon_cache[ext]

    if ext in _ARCHIVE_EXTS:
        if _BUILTIN_ARCHIVE_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_ARCHIVE_KEY] = _make_archive_icon()
        _icon_cache[ext] = _icon_cache[_BUILTIN_ARCHIVE_KEY]
        return _icon_cache[ext]

    if ext == ".py":
        if _BUILTIN_PY_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_PY_KEY] = _make_py_icon()
        _icon_cache[ext] = _icon_cache[_BUILTIN_PY_KEY]
        return _icon_cache[ext]

    if ext in (".html", ".htm"):
        if _BUILTIN_HTML_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_HTML_KEY] = _make_html_icon()
        _icon_cache[ext] = _icon_cache[_BUILTIN_HTML_KEY]
        return _icon_cache[ext]

    if ext == ".css":
        if _BUILTIN_CSS_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_CSS_KEY] = _make_css_icon()
        _icon_cache[ext] = _icon_cache[_BUILTIN_CSS_KEY]
        return _icon_cache[ext]

    if ext in (".js", ".mjs", ".cjs"):
        if _BUILTIN_JS_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_JS_KEY] = _make_js_icon()
        _icon_cache[ext] = _icon_cache[_BUILTIN_JS_KEY]
        return _icon_cache[ext]

    mime = None  # initialise so step 3 never hits NameError

    # 1. Try exact extension → theme name
    theme_name = EXT_ICON_MAP.get(ext, "")
    icon = QIcon.fromTheme(theme_name) if theme_name else QIcon()

    # 2. Try MIME-derived theme name  (e.g. "image/png" → "image-png")
    if icon.isNull():
        mime, _ = mimetypes.guess_type(f"x{ext}")
        if mime:
            mime_icon = mime.replace("/", "-")
            icon = QIcon.fromTheme(mime_icon)

    # 3. Generic MIME category fallback
    if icon.isNull() and mime:
        for prefix, fallback in GENERIC_FALLBACKS:
            if mime.startswith(prefix):
                icon = QIcon.fromTheme(fallback)
                break

    # 4. Let QFileIconProvider handle it (reads from system)
    if icon.isNull():
        from PyQt6.QtCore import QFileInfo
        icon = _icon_provider.icon(QFileInfo(path))

    # 5. Generic file icon (our own painted one — never null)
    if icon.isNull():
        if _BUILTIN_FILE_KEY not in _icon_cache:
            _icon_cache[_BUILTIN_FILE_KEY] = _make_generic_file_icon()
        icon = _icon_cache[_BUILTIN_FILE_KEY]

    _icon_cache[ext] = icon
    return icon


# ═══════════════════════════════════════════════════════════════════════════════
#  RECENT FILES
# ═══════════════════════════════════════════════════════════════════════════════

RECENT_JSON = os.path.expanduser("~/.local/share/file_explorer_recent.json")
MAX_RECENT  = 50

FAVORITES_JSON = os.path.expanduser("~/.local/share/file_explorer_favorites.json")
VIEW_PREFS_JSON = os.path.expanduser("~/.local/share/file_explorer_view_prefs.json")
THEME_JSON      = os.path.expanduser("~/.local/share/file_explorer_theme.json")


class Favorites:
    def __init__(self):
        self._entries: list[str] = []
        self._load()

    def _load(self):
        try:
            with open(FAVORITES_JSON) as f:
                self._entries = [e for e in json.load(f) if os.path.isdir(e)]
        except Exception:
            self._entries = []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(FAVORITES_JSON), exist_ok=True)
            with open(FAVORITES_JSON, "w") as f:
                json.dump(self._entries, f)
        except Exception:
            pass

    def add(self, path: str):
        if path not in self._entries:
            self._entries.append(path)
            self._save()

    def remove(self, path: str):
        if path in self._entries:
            self._entries.remove(path)
            self._save()

    def contains(self, path: str) -> bool:
        return path in self._entries

    def entries(self) -> list[str]:
        return list(self._entries)

class RecentFiles:
    def __init__(self):
        self._entries: list[str] = []
        self._load()

    def _load(self):
        try:
            with open(RECENT_JSON) as f:
                self._entries = [e for e in json.load(f) if os.path.exists(e)]
        except Exception:
            self._entries = []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(RECENT_JSON), exist_ok=True)
            with open(RECENT_JSON, "w") as f:
                json.dump(self._entries, f)
        except Exception:
            pass

    def add(self, path: str):
        if path in self._entries:
            self._entries.remove(path)
        self._entries.insert(0, path)
        self._entries = self._entries[:MAX_RECENT]
        self._save()

    def entries(self) -> list[str]:
        return list(self._entries)


# ═══════════════════════════════════════════════════════════════════════════════
#  RECENT VIEW  (virtual QAbstractTableModel shown instead of QFileSystemModel)
# ═══════════════════════════════════════════════════════════════════════════════

class RecentModel(QAbstractTableModel):
    HEADERS = ["Name", "Size", "Type", "Date Modified"]

    def __init__(self, entries: list[str], parent=None):
        super().__init__(parent)
        self._rows = self._build(entries)

    def _build(self, entries):
        rows = []
        for path in entries:
            try:
                stat = os.stat(path)
                ext  = os.path.splitext(path)[1].upper().lstrip(".") or "File"
                size = self._fmt(stat.st_size)
                date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                rows.append((os.path.basename(path), size, ext, date, path))
            except Exception:
                pass
        return rows

    @staticmethod
    def _fmt(n):
        for u in ("B","KB","MB","GB"):
            if n < 1024: return f"{n:.1f} {u}"
            n /= 1024
        return f"{n:.1f} TB"

    def rowCount(self, parent=QModelIndex()): return len(self._rows)
    def columnCount(self, parent=QModelIndex()): return 4

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return QVariant()

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._rows):
            return QVariant()
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return row[index.column()]
        if role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
            return resolve_icon(row[4], False)
        if role == Qt.ItemDataRole.UserRole:   # full path
            return row[4]
        return QVariant()

    def filepath(self, row: int) -> str:
        return self._rows[row][4] if row < len(self._rows) else ""


# ═══════════════════════════════════════════════════════════════════════════════
#  ICON DELEGATE  (injects custom icons into QFileSystemModel rows)
# ═══════════════════════════════════════════════════════════════════════════════

class IconDelegate(QStyledItemDelegate):
    """Paints custom icons for column 0; falls back to default for other columns.

    We override paint() rather than only initStyleOption() because QFileSystemModel
    re-fetches its own icon from the model inside the style's drawControl(), which
    means any icon set in initStyleOption can be silently clobbered on many Qt6
    builds.  By driving the paint pass ourselves we guarantee our icon is used.
    """

    def __init__(self, fs_model: QFileSystemModel, proxy, parent=None):
        super().__init__(parent)
        self._fs    = fs_model
        self._proxy = proxy

    # ── helpers ───────────────────────────────────────────────────────────────

    def _get_icon(self, index):
        """Return resolved QIcon for a proxy index, or null QIcon on failure."""
        if index.column() != 0:
            return QIcon()
        src = self._proxy.mapToSource(index)
        if not src.isValid():
            return QIcon()
        return resolve_icon(self._fs.filePath(src), self._fs.isDir(src))

    # ── Qt overrides ──────────────────────────────────────────────────────────

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        icon = self._get_icon(index)
        if not icon.isNull():
            from PyQt6.QtWidgets import QStyleOptionViewItem
            option.icon = icon
            option.features |= QStyleOptionViewItem.ViewItemFeature.HasDecoration

    def paint(self, painter, option, index):
        if index.column() != 0:
            super().paint(painter, option, index)
            return
        icon = self._get_icon(index)
        if icon.isNull():
            super().paint(painter, option, index)
            return
        from PyQt6.QtWidgets import QStyleOptionViewItem
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        # Overwrite whatever the model put in — this is the critical line
        opt.icon = icon
        opt.features |= QStyleOptionViewItem.ViewItemFeature.HasDecoration
        super().paint(painter, opt, index)

    # ── inline rename editor ──────────────────────────────────────────────────

    def createEditor(self, parent, option, index):
        if index.column() != 0:
            return super().createEditor(parent, option, index)
        editor = QLineEdit(parent)
        editor.setFrame(True)
        editor._committed = False   # flag: set True by setModelData on success
        return editor

    def setEditorData(self, editor, index):
        if index.column() != 0:
            super().setEditorData(editor, index)
            return
        src = self._proxy.mapToSource(index)
        if src.isValid():
            name = os.path.basename(self._fs.filePath(src))
        else:
            name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        editor.setText(name)
        # Select name without extension for files, full name for folders
        src = self._proxy.mapToSource(index)
        is_dir = src.isValid() and self._fs.isDir(src)
        if not is_dir and "." in name:
            editor.setSelection(0, name.rfind("."))
        else:
            editor.selectAll()

    @staticmethod
    def _unique_path(parent_dir: str, name: str) -> str:
        """Return a path that doesn't collide with any existing sibling.

        Splits *name* into stem + ext, then tries:
          name, stem (1).ext, stem (2).ext, …
        Works for both files and directories (ext is "" for dirs).
        """
        candidate = os.path.join(parent_dir, name)
        if not os.path.exists(candidate):
            return candidate
        stem, ext = os.path.splitext(name)
        n = 1
        while True:
            new_name = f"{stem} ({n}){ext}"
            candidate = os.path.join(parent_dir, new_name)
            if not os.path.exists(candidate):
                return candidate
            n += 1

    def setModelData(self, editor, model, index):
        if index.column() != 0:
            super().setModelData(editor, model, index)
            return
        new_name = editor.text().strip()
        src = self._proxy.mapToSource(index)
        if not src.isValid():
            return
        old_path = self._fs.filePath(src)
        old_name = os.path.basename(old_path)
        # Empty name → delete placeholder
        if not new_name:
            try:
                import shutil as _shutil
                _shutil.rmtree(old_path) if os.path.isdir(old_path) else os.remove(old_path)
            except Exception:
                pass
            return
        # Mark as committed so destroyEditor won't delete the placeholder
        editor._committed = True
        if new_name == old_name:
            return
        parent_dir = os.path.dirname(old_path)
        # Resolve collisions: if a sibling already has this name, append (1), (2), …
        desired = os.path.join(parent_dir, new_name)
        if os.path.exists(desired):
            new_path = self._unique_path(parent_dir, new_name)
        else:
            new_path = desired
        try:
            os.rename(old_path, new_path)
        except Exception as e:
            QMessageBox.critical(None, "Rename Error", str(e))

    def destroyEditor(self, editor, index):
        """If user pressed Escape on a placeholder, delete it."""
        if index.column() == 0 and not getattr(editor, "_committed", False):
            src = self._proxy.mapToSource(index)
            if src.isValid():
                path = self._fs.filePath(src)
                name = os.path.basename(path)
                is_dir = self._fs.isDir(src)
                try:
                    is_placeholder = (
                        (is_dir and name.startswith("New Folder") and not os.listdir(path)) or
                        (not is_dir and name.startswith("New File") and os.path.getsize(path) == 0)
                    )
                except OSError:
                    is_placeholder = False
                if is_placeholder:
                    try:
                        os.rmdir(path) if is_dir else os.remove(path)
                    except Exception:
                        pass
        super().destroyEditor(editor, index)


# ═══════════════════════════════════════════════════════════════════════════════
#  IMAGE PREVIEW DELEGATE  (used by icon/grid view — shows actual thumbnails)
# ═══════════════════════════════════════════════════════════════════════════════

class ImagePreviewDelegate(IconDelegate):
    """Like IconDelegate but renders actual image thumbnails in icon/grid view.

    For image files whose thumbnail is in ``_thumb_cache`` it draws the pixmap
    centered in the decoration rect with a subtle rounded shadow, replacing the
    generic image-icon.  For everything else it falls back to the parent class.
    """

    # Radius of the rounded clipping mask applied to thumbnail previews
    CORNER_RADIUS = 4

    def paint(self, painter, option, index):
        # Only decorate column 0 and only for single-file rows
        if index.column() != 0:
            super().paint(painter, option, index)
            return

        src = self._proxy.mapToSource(index)
        if not src.isValid():
            super().paint(painter, option, index)
            return

        path = self._fs.filePath(src)
        ext  = os.path.splitext(path)[1].lower()

        # Check cache
        thumb = _thumb_cache.get(path)
        if thumb is None or ext not in _IMAGE_EXTS:
            super().paint(painter, option, index)
            return

        # ── Draw the standard item background (hover / selection) ────────────
        from PyQt6.QtWidgets import QStyleOptionViewItem, QApplication, QStyle
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        # Clear icon and text so the style only draws background/selection;
        # we render both the thumbnail and label ourselves below.
        opt.icon = QIcon()
        opt.text = ""
        style = QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter)

        # ── Draw thumbnail in the decoration rect ────────────────────────────
        deco_rect = style.subElementRect(
            QStyle.SubElement.SE_ItemViewItemDecoration, opt
        )
        if deco_rect.isEmpty():
            # Fallback: carve out the top portion of the item rect
            r = option.rect
            side = min(r.width(), r.height() - 20)
            deco_rect.setRect(
                r.x() + (r.width() - side) // 2,
                r.y() + 4,
                side, side,
            )

        # Scale thumb to fit inside deco_rect while keeping aspect ratio
        px = thumb.scaled(
            deco_rect.width(), deco_rect.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        px_x = deco_rect.x() + (deco_rect.width()  - px.width())  // 2
        px_y = deco_rect.y() + (deco_rect.height() - px.height()) // 2

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Subtle drop shadow
        shadow_rect = px.rect().translated(px_x + 1, px_y + 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 35)))
        painter.drawRoundedRect(shadow_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

        # Rounded clip mask
        clip = QPainterPath()
        from PyQt6.QtCore import QRectF
        clip.addRoundedRect(
            QRectF(px_x, px_y, px.width(), px.height()),
            self.CORNER_RADIUS, self.CORNER_RADIUS,
        )
        painter.setClipPath(clip)
        painter.drawPixmap(px_x, px_y, px)
        painter.setClipping(False)

        # Thin border
        painter.setPen(QPen(QColor(0, 0, 0, 25), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            QRectF(px_x, px_y, px.width(), px.height()),
            self.CORNER_RADIUS, self.CORNER_RADIUS,
        )
        painter.restore()

        # ── Draw display label (file name) ───────────────────────────────────
        text_rect = style.subElementRect(
            QStyle.SubElement.SE_ItemViewItemText, opt
        )
        if not text_rect.isEmpty():
            painter.save()
            # Use app default font — never inherit opt.font which may be the
            # Fluent icon font set on toolbar buttons.
            from PyQt6.QtWidgets import QApplication as _App
            painter.setFont(_App.font())
            color = (opt.palette.highlightedText().color()
                     if option.state & QStyle.StateFlag.State_Selected
                     else opt.palette.text().color())
            painter.setPen(color)
            fm   = painter.fontMetrics()
            name = os.path.basename(path)
            elided = fm.elidedText(name, Qt.TextElideMode.ElideRight, text_rect.width())
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                elided,
            )
            painter.restore()


# ═══════════════════════════════════════════════════════════════════════════════
#  BREADCRUMB ADDRESS BAR
# ═══════════════════════════════════════════════════════════════════════════════

class BreadcrumbBar(QStackedWidget):
    """Windows-Explorer-style address bar.

    - Page 0 (crumb view): row of clickable path segments with › chevrons.
      Clicking a chevron opens a dropdown of sibling folders at that level.
      Clicking anywhere on the empty area of the bar switches to edit mode.
    - Page 1 (edit view): plain QLineEdit pre-filled with the current path.
      Pressing Enter or losing focus commits the path and returns to crumb mode.

    Signals:
        navigate(str)  — emitted when the user picks a path (crumb, dropdown, or typed).
    """

    navigate = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = ""

        # ── page 0: crumb view ────────────────────────────────────────────────
        self._crumb_page = QWidget(); self._crumb_page.setObjectName("crumbPage")
        self._crumb_layout = QHBoxLayout(self._crumb_page)
        self._crumb_layout.setContentsMargins(5, 0, 5, 0)
        self._crumb_layout.setSpacing(0)
        self._crumb_layout.addStretch()

        # clicking the blank area of the bar enters edit mode
        self._crumb_page.mousePressEvent = lambda e: self._enter_edit_mode()

        # ── page 1: edit view ─────────────────────────────────────────────────
        self._edit = QLineEdit()
        self._edit.returnPressed.connect(self._commit_edit)
        self._edit.installEventFilter(self)   # Escape / focus-out → cancel

        self.addWidget(self._crumb_page)   # index 0
        self.addWidget(self._edit)         # index 1
        self.setCurrentIndex(0)

        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # ── public API ────────────────────────────────────────────────────────────
    def set_path(self, path: str):
        """Update the breadcrumb display without emitting navigate."""
        self._current_path = path
        # Non-filesystem label (e.g. "Recent Files") → single static crumb
        if not os.path.isabs(path):
            while self._crumb_layout.count() > 1:
                item = self._crumb_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            lbl = QPushButton(path)
            lbl.setEnabled(False)
            self._crumb_layout.insertWidget(0, lbl)
            self.setCurrentIndex(0)
            return
        self._rebuild_crumbs(path)
        self.setCurrentIndex(0)

    def text(self) -> str:
        return self._current_path

    def setText(self, path: str):          # drop-in for QLineEdit.setText
        self.set_path(path)

    # ── crumb builder ─────────────────────────────────────────────────────────
    def _rebuild_crumbs(self, path: str):
        # Remove all widgets except the trailing stretch
        while self._crumb_layout.count() > 1:
            item = self._crumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not path:
            return

        # Split path into (label, full_path) pairs
        parts = []
        p = path
        while True:
            parent = os.path.dirname(p)
            label  = os.path.basename(p) or p   # root → "/" or "C:\"
            parts.append((label, p))
            if parent == p:
                break
            p = parent
        parts.reverse()

        for i, (label, full_path) in enumerate(parts):
            # crumb button
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, fp=full_path: self.navigate.emit(fp))
            # stop the click bubbling up to the bar's mousePressEvent
            btn.mousePressEvent = lambda e, b=btn: (
                b.__class__.mousePressEvent(b, e)
            )
            self._crumb_layout.insertWidget(self._crumb_layout.count() - 1, btn)

            # chevron (not after the last segment)
            if i < len(parts) - 1:
                chev = QPushButton("›")
                chev.setStyleSheet("QPushButton { color: palette(placeholderText); font-size: 11px; padding: 2px 2px; }")
                chev.setCursor(Qt.CursorShape.PointingHandCursor)
                chev.setFixedWidth(19)
                chev.clicked.connect(
                    lambda checked, fp=full_path: self._show_chevron_menu(fp, chev)
                )
                # capture chev properly
                chev.clicked.disconnect()
                chev.clicked.connect(
                    lambda checked, fp=full_path, c=chev: self._show_chevron_menu(fp, c)
                )
                self._crumb_layout.insertWidget(self._crumb_layout.count() - 1, chev)

    def _show_chevron_menu(self, parent_path: str, button: QPushButton):
        """Popup listing immediate subdirectories of parent_path."""
        try:
            entries = sorted(
                (e for e in os.scandir(parent_path) if e.is_dir()),
                key=lambda e: e.name.lower()
            )
        except PermissionError:
            return
        if not entries:
            return
        menu = QMenu(self)
        for entry in entries:
            act = menu.addAction(QIcon.fromTheme("folder"), entry.name)
            act.triggered.connect(
                lambda checked, fp=entry.path: self.navigate.emit(fp)
            )
        # show below the chevron button
        pos = button.mapToGlobal(button.rect().bottomLeft())
        menu.exec(pos)

    # ── edit mode ─────────────────────────────────────────────────────────────
    def _enter_edit_mode(self):
        self._edit.setText(self._current_path)
        self.setCurrentIndex(1)
        self._edit.setFocus()
        self._edit.selectAll()

    def _commit_edit(self):
        path = self._edit.text().strip()
        path = os.path.expanduser(path)
        self.setCurrentIndex(0)
        if path and os.path.isdir(path):
            self._current_path = path
            self._rebuild_crumbs(path)
            self.navigate.emit(path)
        else:
            # invalid path — just restore previous crumbs
            self._rebuild_crumbs(self._current_path)

    def _cancel_edit(self):
        self.setCurrentIndex(0)
        self._rebuild_crumbs(self._current_path)

    # ── event filter (Escape / focus-out on the QLineEdit) ────────────────────
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self._edit:
            if event.type() == QEvent.Type.KeyPress:
                from PyQt6.QtGui import QKeyEvent
                if event.key() == Qt.Key.Key_Escape:
                    self._cancel_edit()
                    return True
            elif event.type() == QEvent.Type.FocusOut:
                self._cancel_edit()
        return super().eventFilter(obj, event)


# ═══════════════════════════════════════════════════════════════════════════════
#  FILE VIEW  (QTreeView with go-up on empty-space double-click)
# ═══════════════════════════════════════════════════════════════════════════════

class FileView(QTreeView):
    """QTreeView with two behaviours:

    1. Single-clicking empty space clears selection (Qt default, unchanged).
    2. Double-clicking empty space emits go_up to navigate to parent folder.
    3. Dragging from the icon area initiates a URI drag (icon-only drag pixmap).
    """
    go_up        = pyqtSignal()
    open_current = pyqtSignal()   # Enter
    delete_sel        = pyqtSignal()   # Delete
    perm_delete_sel   = pyqtSignal()   # Shift+Delete
    cut_sel      = pyqtSignal()   # Ctrl+X
    copy_sel     = pyqtSignal()   # Ctrl+C
    paste_sel    = pyqtSignal()   # Ctrl+V
    refresh_req      = pyqtSignal()   # Ctrl+R
    new_folder_req   = pyqtSignal()   # Ctrl+N
    new_file_req     = pyqtSignal()   # Ctrl+F

    _ICON_W = 26   # px width of the icon region in column 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.viewport().installEventFilter(self)
        self._drag_start_pos  = None
        self._drag_from_icon  = False

    # ── icon-only drag ────────────────────────────────────────────────────────

    def _index_at_viewport(self, pos):
        """Return the column-0 index under pos, or invalid."""
        idx = self.indexAt(pos)
        if not idx.isValid():
            return idx
        return idx.sibling(idx.row(), 0)

    def _on_icon_area(self, pos) -> bool:
        """True if pos is within the icon rect of a column-0 item."""
        idx = self._index_at_viewport(pos)
        if not idx.isValid():
            return False
        rect = self.visualRect(idx)
        # icon occupies the leftmost _ICON_W pixels of the item rect
        return pos.x() <= rect.left() + self._ICON_W

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self._drag_from_icon = self._on_icon_area(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton
                and self._drag_from_icon
                and self._drag_start_pos is not None):
            from PyQt6.QtCore import QPoint
            dist = (event.pos() - self._drag_start_pos).manhattanLength()
            if dist >= 8:   # start drag after a small threshold
                self._drag_start_pos = None
                self._drag_from_icon = False
                self._start_icon_drag()
                return
        super().mouseMoveEvent(event)

    def _start_icon_drag(self):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDrag
        from PyQt6.QtCore import QMimeData

        indexes = self.selectionModel().selectedRows(0)
        if not indexes:
            return

        # collect URLs from the model
        urls = []
        icons = []
        model = self.model()
        for idx in indexes:
            # works for both proxy (QSortFilterProxyModel) and direct models
            if hasattr(model, "mapToSource"):
                src = model.mapToSource(idx)
                src_model = model.sourceModel()
                path = src_model.filePath(src)
            else:
                path = model.data(idx, Qt.ItemDataRole.UserRole) or ""
            if path:
                urls.append(QUrl.fromLocalFile(path))
                icons.append(model.data(idx, Qt.ItemDataRole.DecorationRole))

        if not urls:
            return

        mime = QMimeData()
        mime.setUrls(urls)

        drag = QDrag(self)
        drag.setMimeData(mime)

        # drag pixmap: first file's icon, scaled to 32×32
        icon = icons[0] if icons else None
        if icon and not icon.isNull():
            px = icon.pixmap(QSize(38, 38))
        else:
            px = QPixmap(32, 32)
            px.fill(Qt.GlobalColor.transparent)
        drag.setPixmap(px)
        drag.setHotSpot(QPoint(px.width() // 2, px.height() // 2))

        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self.viewport():
            if event.type() == QEvent.Type.MouseButtonDblClick:
                if not self.indexAt(event.pos()).isValid():
                    self.go_up.emit()
                    return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        key  = event.key()
        mods = event.modifiers()
        ctrl = Qt.KeyboardModifier.ControlModifier

        if key == Qt.Key.Key_F2:
            idx = self.currentIndex()
            if idx.isValid():
                name_idx = idx.sibling(idx.row(), 0)
                self.edit(name_idx)
                return

        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.state() != QAbstractItemView.State.EditingState:
                self.open_current.emit()
            return

        elif key == Qt.Key.Key_Delete:
            shift = Qt.KeyboardModifier.ShiftModifier
            if mods & shift:
                self.perm_delete_sel.emit()
            else:
                self.delete_sel.emit()
            return

        elif mods == ctrl and key == Qt.Key.Key_X:
            self.cut_sel.emit()
            return

        elif mods == ctrl and key == Qt.Key.Key_C:
            self.copy_sel.emit()
            return

        elif mods == ctrl and key == Qt.Key.Key_V:
            self.paste_sel.emit()
            return

        elif mods == ctrl and key == Qt.Key.Key_R:
            self.refresh_req.emit()
            return

        elif mods == ctrl and key == Qt.Key.Key_N:
            self.new_folder_req.emit()
            return

        elif mods == ctrl and key == Qt.Key.Key_F:
            self.new_file_req.emit()
            return

        super().keyPressEvent(event)


class IconFileView(QListView):
    """QListView (icon/grid mode) with the same keyboard shortcuts and
    double-click-empty-space behaviour as FileView."""

    go_up             = pyqtSignal()
    open_current      = pyqtSignal()
    delete_sel        = pyqtSignal()
    perm_delete_sel   = pyqtSignal()
    cut_sel           = pyqtSignal()
    copy_sel          = pyqtSignal()
    paste_sel         = pyqtSignal()
    refresh_req       = pyqtSignal()
    new_folder_req    = pyqtSignal()
    new_file_req      = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self.viewport():
            if event.type() == QEvent.Type.MouseButtonDblClick:
                if not self.indexAt(event.pos()).isValid():
                    self.go_up.emit()
                    return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        key  = event.key()
        mods = event.modifiers()
        ctrl = Qt.KeyboardModifier.ControlModifier

        if key == Qt.Key.Key_F2:
            idx = self.currentIndex()
            if idx.isValid():
                self.edit(idx)
            return

        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.state() != QAbstractItemView.State.EditingState:
                self.open_current.emit()
            return

        elif key == Qt.Key.Key_Delete:
            if mods & Qt.KeyboardModifier.ShiftModifier:
                self.perm_delete_sel.emit()
            else:
                self.delete_sel.emit()
            return

        elif mods == ctrl and key == Qt.Key.Key_X:
            self.cut_sel.emit(); return
        elif mods == ctrl and key == Qt.Key.Key_C:
            self.copy_sel.emit(); return
        elif mods == ctrl and key == Qt.Key.Key_V:
            self.paste_sel.emit(); return
        elif mods == ctrl and key == Qt.Key.Key_R:
            self.refresh_req.emit(); return
        elif mods == ctrl and key == Qt.Key.Key_N:
            self.new_folder_req.emit(); return
        elif mods == ctrl and key == Qt.Key.Key_F:
            self.new_file_req.emit(); return

        super().keyPressEvent(event)


def _sidebar_icon(label: str) -> QIcon:
    """
    Return a 24×24 minimal icon for each sidebar label.
    Clean thin strokes, geometric, monochrome — no fills except where essential.
    """
    from PyQt6.QtCore import QPointF, QRectF
    from PyQt6.QtGui import QPolygonF
    S = 24
    px = QPixmap(S, S)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    BLUE  = QColor("#0078D4")
    WHITE = QApplication.instance().palette().color(QPalette.ColorRole.Window)

    def stroke(width=1.5):
        return QPen(BLUE, width, Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

    key = label.lower()

    if key == "home":
        # Clean house outline: roof + walls, door cutout
        p.setBrush(QBrush(BLUE))
        roof = QPainterPath()
        roof.moveTo(10, 2); roof.lineTo(17.4, 10); roof.lineTo(1.8, 10)
        roof.closeSubpath()
        p.fillPath(roof, QBrush(BLUE))
        body = QPainterPath()
        body.addRoundedRect(4, 9.0, 12, 8, 1, 1)
        p.fillPath(body, QBrush(BLUE))
        # door — white cutout
        door = QPainterPath()
        door.addRoundedRect(7, 13, 5, 5, 0.96, 0.96)
        p.fillPath(door, QBrush(WHITE))

    elif key == "desktop":
        # Thin monitor outline
        p.setPen(stroke(1.68))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1, 2, 17, 11), 1.8, 1.8)
        p.drawLine(7, 13, 12, 13)   # stand top
        p.drawLine(10, 13, 10, 16)    # pole
        p.drawLine(6, 16, 13, 16)   # base

    elif key == "documents":
        # Minimal doc outline with fold
        p.setPen(stroke(1.56))
        p.setBrush(Qt.BrushStyle.NoBrush)
        doc = QPainterPath()
        doc.moveTo(4, 1); doc.lineTo(12, 1); doc.lineTo(16, 5)
        doc.lineTo(16, 18); doc.lineTo(4, 18); doc.closeSubpath()
        p.drawPath(doc)
        # fold
        fold = QPainterPath()
        fold.moveTo(12, 1); fold.lineTo(12, 5); fold.lineTo(16, 5)
        p.drawPath(fold)
        # two text lines
        p.setPen(stroke(1.44))
        p.drawLine(6, 10, 13, 10)
        p.drawLine(QPointF(6, 12.6), QPointF(11, 12.6))

    elif key == "downloads":
        # Down arrow — clean stroked
        p.setPen(stroke(1.92))
        p.drawLine(10, 1, 10, 12)
        arr = QPainterPath()
        arr.moveTo(5.4, 8); arr.lineTo(10, 13); arr.lineTo(13.8, 8)
        p.drawPath(arr)
        # tray
        p.drawLine(2, 16, 17, 16)
        p.drawLine(2, 16, 2, 18)
        p.drawLine(17, 16, 17, 18)

    elif key == "music":
        # Clean music note — stroked
        p.setPen(stroke(1.68))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # note head
        p.drawEllipse(QRectF(5, 12, 5.4, 4.2))
        # stem
        p.drawLine(QPointF(10.2, 13.8), QPointF(10.2, 4))
        # flag
        flag = QPainterPath()
        flag.moveTo(10.2, 4); flag.lineTo(16, 6); flag.lineTo(10.2, 8)
        p.drawPath(flag)

    elif key == "pictures":
        # Simple framed landscape — outline only
        p.setPen(stroke(1.56))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1, 2, 17, 14), 1.8, 1.8)
        # mountain
        mtn = QPainterPath()
        mtn.moveTo(2, 17); mtn.lineTo(7, 10); mtn.lineTo(12, 13)
        mtn.lineTo(14, 10.2); mtn.lineTo(18, 14)
        p.drawPath(mtn)
        # sun circle
        p.drawEllipse(12, 5, 4, 4)

    elif key == "videos":
        # Play button in a rounded rect outline
        p.setPen(stroke(1.56))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(1, 2, 17, 14, 2, 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(BLUE))
        play = QPainterPath()
        play.addPolygon(QPolygonF([
            QPointF(7, 6.6), QPointF(7, 12.6), QPointF(13.8, 10)
        ]))
        play.closeSubpath()
        p.fillPath(play, QBrush(BLUE))

    elif key == "recent":
        # Clock — thin circle + hands
        p.setPen(stroke(1.56))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(1, 1, 17, 17)
        p.setPen(stroke(1.8))
        p.drawLine(10, 10, 10, 5)      # hour hand
        p.drawLine(QPointF(10, 10), QPointF(13.8, 12))  # minute hand

    elif key == "trash":
        # Clean bin — outline only
        p.setPen(stroke(1.56))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # lid
        p.drawLine(4, 5, 16, 5)
        p.drawRoundedRect(QRectF(7, 1.8, 5, 3.0), 0.6, 0.6)   # handle
        # body trapezoid
        body = QPainterPath()
        body.moveTo(5, 5); body.lineTo(14, 5)
        body.lineTo(13, 18); body.lineTo(6, 18)
        body.closeSubpath()
        p.drawPath(body)
        # stripes
        p.drawLine(QPointF(8, 7.8), QPointF(7.8, 16))
        p.drawLine(QPointF(11, 7.8), QPointF(11.4, 16))

    else:
        # fallback: minimal folder outline
        p.setPen(stroke(1.56))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1, 6, 17, 11), 1.8, 1.8)
        tab = QPainterPath()
        tab.addRoundedRect(1, 4, 6.6, 4, 1, 1)
        p.drawPath(tab)

    p.end()
    return QIcon(px)


def _rr(x, y, w, h, r) -> QPainterPath:
    """Shorthand for a rounded-rect QPainterPath."""
    path = QPainterPath()
    path.addRoundedRect(x, y, w, h, r, r)
    return path


def _cmd_icon(key: str, ink: "QColor | None" = None) -> QIcon:
    """
    Paint a 24×24 minimal icon for command bar buttons.
    ink: stroke colour; defaults to app palette WindowText so it adapts to theme.
    """
    from PyQt6.QtCore import QPointF, QRectF
    from PyQt6.QtGui import QPolygonF
    if ink is None:
        app = QApplication.instance()
        ink = app.palette().color(QPalette.ColorRole.WindowText) if app else QColor("#1A1A1A")
    S = 24
    px = QPixmap(S, S)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    INK = ink

    def stroke(w=1.4):
        return QPen(INK, w, Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

    p.setPen(stroke())
    p.setBrush(Qt.BrushStyle.NoBrush)

    if key == "new_folder":
        # folder outline + plus
        p.drawRoundedRect(QRectF(1, 6, 17, 12), 1.8, 1.8)
        tab = QPainterPath()
        tab.addRoundedRect(1, 4, 6, 4, 1, 1)
        p.drawPath(tab)
        # plus overlay (filled blue badge)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#0078D4")))
        p.drawRoundedRect(QRectF(11, 10.2, 7, 6), 1, 1)
        p.setPen(QPen(QColor("#FFFFFF"), 1.56,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(14, 11.4), QPointF(14, 15.0))
        p.drawLine(QPointF(12.6, 13), QPointF(16.2, 13))

    elif key == "new_file":
        # doc outline with fold
        p.setBrush(Qt.BrushStyle.NoBrush)
        doc = QPainterPath()
        doc.moveTo(4, 1); doc.lineTo(11.4, 1); doc.lineTo(16, 5.4)
        doc.lineTo(16, 18); doc.lineTo(4, 18); doc.closeSubpath()
        p.drawPath(doc)
        fold = QPainterPath()
        fold.moveTo(11.4, 1); fold.lineTo(11.4, 5.4); fold.lineTo(16, 5.4)
        p.drawPath(fold)
        # plus overlay
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#0078D4")))
        p.drawRoundedRect(QRectF(11, 11, 7, 6.6), 1, 1)
        p.setPen(QPen(QColor("#FFFFFF"), 1.56,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(14, 12), QPointF(14, 16.2))
        p.drawLine(QPointF(12.6, 14.1), QPointF(16.2, 14.1))

    elif key == "cut":
        # minimalist scissors — two circles + blades
        p.setPen(stroke(1.68))
        p.drawEllipse(QRectF(1.8, 12, 5, 5))
        p.drawEllipse(QRectF(12.6, 12, 5, 5))
        # blades
        p.drawLine(QPointF(5.4, 14), QPointF(10, 10))
        p.drawLine(QPointF(13.8, 14), QPointF(10, 10))
        p.drawLine(10, 10, 4, 2)
        p.drawLine(10, 10, 16, 2)

    elif key == "copy":
        # two overlapping page outlines
        p.setPen(stroke(1.56))
        p.drawRoundedRect(6, 5, 11, 13, 1, 1)   # back
        app = QApplication.instance()
        bg = app.palette().color(QPalette.ColorRole.Window) if app else QColor("#F3F3F3")
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(2, 1, 11, 13, 1, 1)   # front

    elif key == "paste":
        # clipboard — outline only
        p.drawRoundedRect(QRectF(4, 4, 12, 14), 1.8, 1.8)
        # clip tab
        p.drawRoundedRect(7, 1, 5, 5, 1, 1)
        app2 = QApplication.instance()
        bg2 = app2.palette().color(QPalette.ColorRole.Window) if app2 else QColor("#F3F3F3")
        p.fillPath(_rr(8, 2, 2, 2, 0.6), QBrush(bg2))
        # two content lines
        p.drawLine(6, 10, 13, 10)
        p.drawLine(QPointF(6, 12.6), QPointF(11, 12.6))

    elif key == "rename":
        # simple pencil
        p.setPen(stroke(1.68))
        # pencil body diagonal
        pen_path = QPainterPath()
        pen_path.moveTo(13.8, 2); pen_path.lineTo(17, 5.4)
        pen_path.lineTo(5.4, 17); pen_path.lineTo(2, 17); pen_path.lineTo(2, 13.8)
        pen_path.closeSubpath()
        p.drawPath(pen_path)
        # eraser line
        p.drawLine(QPointF(11.4, 4.2), QPointF(15.0, 7.8))

    elif key == "delete":
        # clean trash outline
        p.drawLine(2, 5, 17, 5)            # lid top
        p.drawRoundedRect(QRectF(7, 1.8, 5, 3.0), 0.6, 0.6)  # handle
        body = QPainterPath()
        body.moveTo(5, 5); body.lineTo(14, 5)
        body.lineTo(13, 18); body.lineTo(6, 18)
        body.closeSubpath()
        p.drawPath(body)
        p.drawLine(QPointF(8, 7.8), QPointF(7.8, 16))
        p.drawLine(QPointF(11, 7.8), QPointF(11.4, 16))

    elif key == "sort":
        # three descending lines
        p.setPen(stroke(1.8))
        p.drawLine(2, 5, 17, 5)
        p.drawLine(2, 10, 13, 10)
        p.drawLine(2, 14, 8, 14)

    elif key == "details":
        # three equal lines (details/panel view)
        p.setPen(stroke(1.8))
        p.drawLine(2, 5, 17, 5)
        p.drawLine(2, 10, 17, 10)
        p.drawLine(2, 14, 17, 14)

    elif key == "icon_view":
        # 2×2 grid of squares (icon/grid view)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(INK))
        for rx, ry in [(2, 2), (9, 2), (2, 9), (9, 9)]:
            p.drawRoundedRect(QRectF(rx, ry, 6, 6), 1, 1)

    elif key == "list_view":
        # icon + line rows (list view)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(INK))
        for ry in [3, 7, 11]:
            p.drawRoundedRect(QRectF(2, ry, 4, 3.0), 0.6, 0.6)
        p.setPen(stroke(1.68))
        for ry in [4, 8, 12]:
            p.drawLine(QPointF(8, ry), QPointF(17, ry))

    elif key == "restore":
        # curved undo arrow
        p.setPen(stroke(1.8))
        p.drawArc(QRectF(2, 4, 12, 12), 36 * 19, 324 * 19)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(INK))
        arrow = QPainterPath()
        arrow.moveTo(8, 2); arrow.lineTo(5.4, 6.6); arrow.lineTo(11.4, 6.6)
        arrow.closeSubpath()
        p.fillPath(arrow, QBrush(INK))

    elif key in ("pin_add", "pin_remove"):
        import math
        cx, cy, R, r = 11.52, 11.52, 9.36, 4.03
        pts = []
        for i in range(10):
            angle = math.radians(-90 + i * 36)
            radius = R if i % 2 == 0 else r
            pts.append(QPointF(cx + radius * math.cos(angle),
                               cy + radius * math.sin(angle)))
        star = QPainterPath()
        star.addPolygon(QPolygonF(pts))
        star.closeSubpath()
        if key == "pin_add":
            # filled gold + matching border so it pops on any background
            p.setPen(QPen(QColor("#D4A000"), 1.0))
            p.fillPath(star, QBrush(QColor("#F5C030")))
            p.drawPath(star)
        else:
            # muted outline — clearly "off"
            p.setPen(QPen(QColor("#9E9E9E"), 1.56,
                          Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(star)

    p.end()
    return QIcon(px)


# ═══════════════════════════════════════════════════════════════════════════════
#  SEARCH BAR  (Win11-style inline search with magnifier + clear button)
# ═══════════════════════════════════════════════════════════════════════════════

class SearchBar(QWidget):
    """Compact Win11-style search box.

    Emits:
        search_changed(str) — live as the user types (debounced 150 ms).
        search_cleared()    — when the user explicitly clears the field or
                              presses Escape.
    """

    search_changed = pyqtSignal(str)
    search_cleared = pyqtSignal()

    _PLACEHOLDER = "Search"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("searchBar")
        self.setFixedHeight(34)
        self.setFixedWidth(264)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(7, 0, 5, 0)
        lay.setSpacing(2)

        # ── magnifier icon (painted QPushButton acting as a label) ────────────
        self._icon_btn = QPushButton()
        self._icon_btn.setFixedSize(18, 18)
        self._icon_btn.setIcon(self._make_search_icon())
        self._icon_btn.setIconSize(QSize(17, 17))
        self._icon_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._icon_btn.clicked.connect(lambda: self._edit.setFocus())
        lay.addWidget(self._icon_btn)

        # ── text input ────────────────────────────────────────────────────────
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(self._PLACEHOLDER)
        self._edit.setClearButtonEnabled(False)   # we draw our own
        self._edit.textChanged.connect(self._on_text_changed)
        self._edit.returnPressed.connect(self._on_return)
        self._edit.installEventFilter(self)
        lay.addWidget(self._edit)

        # ── clear (×) button ─────────────────────────────────────────────────
        self._clear_btn = QPushButton("✕")
        self._clear_btn.setFixedSize(18, 18)
        self._clear_btn.setVisible(False)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self.clear)
        lay.addWidget(self._clear_btn)

        # debounce timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._emit_search)

    # ── public API ────────────────────────────────────────────────────────────

    def clear(self):
        self._edit.clear()
        self._clear_btn.setVisible(False)
        self._set_active(False)
        self.search_cleared.emit()

    def text(self) -> str:
        return self._edit.text()

    # ── internals ─────────────────────────────────────────────────────────────

    def _on_text_changed(self, text: str):
        self._clear_btn.setVisible(bool(text))
        self._set_active(bool(text))
        self._timer.start()   # restart debounce

    def _emit_search(self):
        self.search_changed.emit(self._edit.text())

    def _on_return(self):
        self._timer.stop()
        self.search_changed.emit(self._edit.text())

    def _set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    # ── Escape to cancel ──────────────────────────────────────────────────────
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self._edit and event.type() == QEvent.Type.KeyPress:
            from PyQt6.QtGui import QKeyEvent
            if event.key() == Qt.Key.Key_Escape:
                self.clear()
                self._edit.clearFocus()
                return True
        return super().eventFilter(obj, event)

    # ── magnifier icon ────────────────────────────────────────────────────────
    @staticmethod
    def _make_search_icon() -> QIcon:
        S = 14
        px = QPixmap(S, S)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#9E9E9E"), 1.3,
                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(1, 1, 8, 8)   # lens
        p.drawLine(8, 8, 13, 13)    # handle
        p.end()
        return QIcon(px)


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

HOME       = os.path.expanduser("~")
TRASH_PATH = os.path.expanduser("~/.local/share/Trash/files")

# Global registry that keeps QThread objects alive until their OS thread has
# fully exited.  Threads add themselves on start and remove themselves via a
# finished→lambda connection.  This prevents "QThread destroyed while running".
_live_threads: set = set()

PINNED = [
    ("Home",      HOME),
    ("Desktop",   os.path.join(HOME, "Desktop")),
    ("Documents", os.path.join(HOME, "Documents")),
    ("Downloads", os.path.join(HOME, "Downloads")),
    ("Music",     os.path.join(HOME, "Music")),
    ("Pictures",  os.path.join(HOME, "Pictures")),
    ("Videos",    os.path.join(HOME, "Videos")),
]

# Sentinel used to signal "show recent view"
RECENT_SENTINEL = "__RECENT__"


class SidebarWidget(QWidget):
    navigate          = pyqtSignal(str)   # emits path or RECENT_SENTINEL
    unmount_requested = pyqtSignal(str)   # emits mount root

    def __init__(self, favorites: "Favorites", parent=None):
        super().__init__(parent)
        self._favorites = favorites
        self.setObjectName("sidebar")
        self.setFixedWidth(252)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        self._lay = QVBoxLayout(inner)
        self._lay.setContentsMargins(0, 7, 0, 7)
        self._lay.setSpacing(0)

        # ── pinned folders + Recent ───────────────────────────────────────────
        self._pinned_btns: list[tuple[str, QPushButton]] = []
        for label, path in PINNED:
            if os.path.isdir(path):
                self._add_btn(label, path)
        self._add_btn("Recent", RECENT_SENTINEL)

        # ── Quick Access section ──────────────────────────────────────────────
        self._qa_label = QLabel("QUICK ACCESS")
        self._qa_label.setContentsMargins(14, 17, 10, 5)
        self._qa_label.setStyleSheet("color: #5C5C5C; font-size: 11px; font-weight: 600; background: transparent;")
        self._lay.addWidget(self._qa_label)

        # container for dynamic favorite buttons
        self._qa_container = QWidget()
        self._qa_container.setObjectName("sidebar")
        self._qa_lay = QVBoxLayout(self._qa_container)
        self._qa_lay.setContentsMargins(0, 0, 0, 0)
        self._qa_lay.setSpacing(0)
        self._lay.addWidget(self._qa_container)

        self._rebuild_favorites()

        # ── Devices & Drives ──────────────────────────────────────────────────
        self._dev_label = QLabel("DEVICES & DRIVES")
        self._dev_label.setContentsMargins(14, 17, 10, 5)
        self._dev_label.setStyleSheet(
            "color: #5C5C5C; font-size: 11px; font-weight: 600; background: transparent;")
        self._lay.addWidget(self._dev_label)

        self._dev_container = QWidget()
        self._dev_container.setObjectName("sidebar")
        self._dev_lay = QVBoxLayout(self._dev_container)
        self._dev_lay.setContentsMargins(0, 0, 0, 0)
        self._dev_lay.setSpacing(0)
        self._lay.addWidget(self._dev_container)

        self._known_volumes: set[str] = set()
        self._mount_attempted: set[str] = set()  # devices we already asked to mount
        self._ejected: set[str] = set()           # devices user manually ejected
        self._refresh_devices()

        # poll every 2 s — reads /proc/mounts, negligible cost
        self._dev_timer = QTimer(self)
        self._dev_timer.setInterval(2000)
        self._dev_timer.timeout.connect(self._refresh_devices)
        self._dev_timer.start()

        self._lay.addStretch()

        # ── Trash (bottom) ───────────────────────────────────────────────────
        os.makedirs(TRASH_PATH, exist_ok=True)
        self._add_btn("Trash", TRASH_PATH)
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── public API ────────────────────────────────────────────────────────────

    def add_favorite(self, path: str):
        self._favorites.add(path)
        self._rebuild_favorites()

    def remove_favorite(self, path: str):
        self._favorites.remove(path)
        self._rebuild_favorites()

    def has_favorite(self, path: str) -> bool:
        return self._favorites.contains(path)

    # ── internals ─────────────────────────────────────────────────────────────

    def _rebuild_favorites(self):
        # clear existing favorite buttons
        while self._qa_lay.count():
            item = self._qa_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = self._favorites.entries()
        self._qa_label.setVisible(bool(entries))
        self._qa_container.setVisible(bool(entries))

        for path in entries:
            self._add_favorite_btn(path)

    def _add_favorite_btn(self, path: str):
        label = os.path.basename(path) or path
        btn = QPushButton(label)
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIcon(QIcon.fromTheme("folder", _make_folder_icon(24)))
        btn.setIconSize(QSize(24, 24))
        btn.clicked.connect(lambda: self.navigate.emit(path))
        # right-click to remove
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, p=path, b=btn: self._fav_context_menu(p, b, pos))
        self._qa_lay.addWidget(btn)

    def refresh_icons(self):
        """Re-render palette-dependent sidebar icons after a theme switch."""
        for label, btn in self._pinned_btns:
            btn.setIcon(_sidebar_icon(label))

    def _fav_context_menu(self, path: str, btn: QPushButton, pos):
        menu = QMenu(self)
        menu.addAction("Remove from Quick Access").triggered.connect(
            lambda: self.remove_favorite(path))
        menu.exec(btn.mapToGlobal(pos))

    def _add_section(self, text: str):
        lbl = QLabel(text.upper())
        lbl.setContentsMargins(14, 17, 10, 5)
        self._lay.addWidget(lbl)

    def _add_btn(self, label: str, target: str):
        btn = QPushButton(label)
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIcon(_sidebar_icon(label))
        btn.setIconSize(QSize(24, 24))
        btn.clicked.connect(lambda: self.navigate.emit(target))
        self._lay.addWidget(btn)
        self._pinned_btns.append((label, btn))

    # ── devices ───────────────────────────────────────────────────────────────

    @staticmethod
    def _drive_icon(is_removable: bool) -> QIcon:
        """Paint a simple drive/USB icon (20x20)."""
        size = 20
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        color = QColor("#5C5C5C")
        p.setBrush(QBrush(color))

        if is_removable:
            # USB stick shape: body + small connector nub
            p.drawRoundedRect(3, 2, 10, 9, 2, 2)    # body
            p.drawRect(6, 11, 4, 3)                  # connector
            p.drawRect(5, 13, 6, 1)                  # base
            # highlight slots
            p.setBrush(QBrush(QColor("#F3F3F3")))
            p.drawRect(5, 4, 2, 2)
            p.drawRect(9, 4, 2, 2)
        else:
            # Hard-drive / cylinder shape
            p.drawRoundedRect(2, 4, 12, 8, 2, 2)    # body
            p.setBrush(QBrush(QColor("#F3F3F3")))
            p.drawEllipse(9, 7, 3, 3)               # platter dot
            p.setBrush(QBrush(color))
            p.drawRect(3, 6, 4, 1)                  # slot line

        p.end()
        icon = QIcon()
        icon.addPixmap(px, QIcon.Mode.Normal, QIcon.State.Off)
        return icon

    @staticmethod
    def _udisks_mount(device: str):
        """Ask udisks2 to mount a block device. Fire-and-forget."""
        try:
            subprocess.Popen(
                ["udisksctl", "mount", "--block-device", device, "--no-user-interaction"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass  # udisksctl not available

    @staticmethod
    def _unmounted_block_devices() -> list[str]:
        """
        Return block device paths (e.g. /dev/sdb1) that are:
          - partitions or whole disks on a removable/USB bus
          - NOT currently mounted
        Reads /sys and /proc/mounts — no subprocesses, negligible cost.
        """
        # build set of already-mounted devices
        mounted: set[str] = set()
        try:
            with open("/proc/mounts") as f:
                for line in f:
                    parts = line.split()
                    if parts:
                        mounted.add(parts[0])
        except OSError:
            return []

        candidates = []
        sys_block = "/sys/block"
        if not os.path.isdir(sys_block):
            return []

        for disk in os.listdir(sys_block):
            disk_path = os.path.join(sys_block, disk)

            # check removable flag
            removable_file = os.path.join(disk_path, "removable")
            try:
                with open(removable_file) as f:
                    if f.read().strip() != "1":
                        continue
            except OSError:
                continue

            # prefer partitions (sdb1, sdb2…); fall back to whole disk
            parts = [
                e for e in os.listdir(disk_path)
                if e.startswith(disk) and os.path.isdir(os.path.join(disk_path, e))
            ]
            targets = parts if parts else [disk]

            for part in targets:
                dev = f"/dev/{part}"
                if dev not in mounted:
                    candidates.append(dev)

        return candidates

    def _refresh_devices(self):
        """
        1. Auto-mount any unmounted removable block devices via udisksctl.
        2. Rebuild the sidebar devices section if mounted volumes changed.
        """
        # ── auto-mount unmounted removable devices ────────────────────────────
        current_block = set(self._unmounted_block_devices())
        # forget devices that disappeared (physically unplugged) so replug works
        self._mount_attempted &= current_block
        self._ejected          &= current_block   # clear ejected if physically gone
        for dev in current_block:
            if dev not in self._mount_attempted and dev not in self._ejected:
                self._mount_attempted.add(dev)
                self._udisks_mount(dev)

        # ── collect relevant mounted volumes ──────────────────────────────────
        skip_roots = {"/", "/boot", "/boot/efi", "/tmp", "/run"}
        skip_fs    = {"tmpfs", "devtmpfs", "squashfs", "overlay",
                      "sysfs", "proc", "cgroup", "cgroup2", "pstore",
                      "efivarfs", "bpf", "tracefs", "configfs",
                      "debugfs", "securityfs", "fusectl", "hugetlbfs",
                      "mqueue", "ramfs"}

        current: dict[str, QStorageInfo] = {}
        for vol in QStorageInfo.mountedVolumes():
            if not vol.isValid() or not vol.isReady():
                continue
            root = vol.rootPath()
            if root in skip_roots:
                continue
            if vol.fileSystemType().data().decode(errors="ignore").lower() in skip_fs:
                continue
            if root.startswith("/snap/"):
                continue
            current[root] = vol

        current_roots = set(current.keys())
        if current_roots == self._known_volumes:
            return   # nothing changed — skip UI rebuild

        self._known_volumes = current_roots

        # clear old buttons
        while self._dev_lay.count():
            item = self._dev_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not current:
            return

        for root, vol in sorted(current.items()):
            name = os.path.basename(root) or vol.displayName() or root
            total_gb = vol.bytesTotal() / (1024 ** 3)
            label = f"{name}  ({total_gb:.0f} GB)" if total_gb >= 0.1 else name

            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(self._drive_icon(vol.isRoot() is False))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(root)
            btn.clicked.connect(lambda checked=False, r=root: self.navigate.emit(r))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, r=root, v=vol: self._drive_context_menu(b, r, v, pos))
            self._dev_lay.addWidget(btn)

    # ── drive context menu ────────────────────────────────────────────────────

    def _drive_context_menu(self, btn: QPushButton, root: str, vol: QStorageInfo, pos):
        menu = QMenu(self)

        unmount_act = menu.addAction("⏏  Unmount")
        menu.addSeparator()
        props_act = menu.addAction("Properties")

        action = menu.exec(btn.mapToGlobal(pos))

        if action == unmount_act:
            self.unmount_requested.emit(root)
        elif action == props_act:
            self._show_drive_properties(root, vol)

    def _do_unmount(self, root: str):
        dev = _mount_point_to_device(root)
        # Mark as ejected so the auto-mounter won't remount it
        self._ejected.add(dev)
        self._mount_attempted.discard(dev)
        try:
            # No --no-user-interaction so the desktop notification fires
            subprocess.Popen(
                ["udisksctl", "unmount", "--block-device", dev],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            QMessageBox.warning(None, "Unmount", "udisksctl not found.")

    @staticmethod
    def _show_drive_properties(root: str, vol: QStorageInfo):
        dlg = DrivePropertiesDialog(root, vol)
        dlg.exec()


def _mount_point_to_device(mount_point: str) -> str:
    """Return the block device path for a given mount point, e.g. /dev/sdb1."""
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == mount_point:
                    return parts[0]
    except OSError:
        pass
    return mount_point   # fallback


class DrivePropertiesDialog(QDialog):
    def __init__(self, root: str, vol: QStorageInfo, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Drive Properties")
        self.setMinimumWidth(408)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        # ── header ────────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet("background: #F9F9F9; border-bottom: 1px solid #E5E5E5;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(19, 17, 19, 17)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(SidebarWidget._drive_icon(True).pixmap(QSize(38, 38)))
        h_lay.addWidget(icon_lbl)

        name_lbl = QLabel(os.path.basename(root) or root)
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #1A1A1A; background: transparent;")
        h_lay.addWidget(name_lbl, 1)
        lay.addWidget(header)

        # ── details ───────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background: #F3F3F3;")
        form = QFormLayout(body)
        form.setContentsMargins(19, 17, 19, 17)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def row(label, value):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #5C5C5C; font-size: 12px; background: transparent;")
            val = QLabel(str(value))
            val.setStyleSheet("color: #1A1A1A; font-size: 12px; background: transparent;")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(lbl, val)

        total   = vol.bytesTotal()
        free    = vol.bytesFree()
        used    = total - free
        fs_type = vol.fileSystemType().data().decode(errors="ignore")

        def fmt(b):
            for unit in ("B", "KB", "MB", "GB", "TB"):
                if b < 1024 or unit == "TB":
                    return f"{b:.1f} {unit}"
                b /= 1024

        device = _mount_point_to_device(root)

        row("Device",      device)
        row("Mount point", root)
        row("Filesystem",  fs_type or "unknown")
        row("Total size",  fmt(total))
        row("Used",        fmt(used))
        row("Free",        fmt(free))

        # usage bar
        if total > 0:
            pct = used / total
            bar_bg = QFrame()
            bar_bg.setFixedHeight(7)
            bar_bg.setStyleSheet("background: palette(mid); border-radius: 3px;")
            bar_fill = QFrame(bar_bg)
            bar_fill.setFixedHeight(7)
            fill_color = "#C42B1C" if pct > 0.9 else "#0078D4"
            bar_fill.setStyleSheet(f"background: {fill_color}; border-radius: 3px;")
            # set width after show via resize; approximate here
            bar_fill.setFixedWidth(max(6, int(280 * pct)))
            form.addRow(QLabel(""), bar_bg)

        lay.addWidget(body)

        # ── close button ──────────────────────────────────────────────────────
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.setContentsMargins(19, 10, 19, 14)
        btn_box.rejected.connect(self.reject)
        btn_box.accepted.connect(self.accept)
        lay.addWidget(btn_box)


# ═══════════════════════════════════════════════════════════════════════════════
#  OPEN-WITH DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

DESKTOP_DIRS = [
    "/usr/share/applications",
    os.path.expanduser("~/.local/share/applications"),
]


def _parse_desktop_files() -> list[dict]:
    apps = []
    for d in DESKTOP_DIRS:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if not fname.endswith(".desktop"):
                continue
            cfg = configparser.RawConfigParser()
            try:
                cfg.read(os.path.join(d, fname), encoding="utf-8")
            except Exception:
                continue
            if not cfg.has_section("Desktop Entry"):
                continue
            entry = cfg["Desktop Entry"]
            if entry.get("NoDisplay", "false").lower() == "true":
                continue
            if entry.get("Type", "") != "Application":
                continue
            name, exec_cmd = entry.get("Name", ""), entry.get("Exec", "")
            if not name or not exec_cmd:
                continue
            apps.append({
                "name": name, "exec": exec_cmd,
                "icon": entry.get("Icon", ""),
                "mime_types": set(m for m in entry.get("MimeType","").split(";") if m),
                "desktop_file": fname,
            })
    apps.sort(key=lambda a: a["name"].lower())
    return apps


def _clean_exec(cmd: str) -> str:
    return re.sub(r"%[fFuUdDnNickvm]", "", cmd).strip()


def _get_mime(path: str) -> str:
    try:
        r = subprocess.run(["xdg-mime","query","filetype",path],
                           capture_output=True, text=True, timeout=2)
        if r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def _apps_for_mime(mime: str, all_apps: list[dict]) -> list[dict]:
    generic = mime.split("/")[0] + "/*"
    return [a for a in all_apps if mime in a["mime_types"] or generic in a["mime_types"]]


def _launch_app(exec_cmd: str, file_path: str):
    cmd = _clean_exec(exec_cmd)
    subprocess.Popen(f'{cmd} "{file_path}"', shell=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class OpenWithDialog(QDialog):
    def __init__(self, file_path: str, all_apps: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Open With")
        self.setMinimumSize(480, 600)
        self._chosen     = None
        self._all_apps   = all_apps
        self._file_path  = file_path
        self._mime       = _get_mime(file_path)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        # ── file label ────────────────────────────────────────────────────────
        lbl = QLabel(f"Choose an application to open:\n<b>{os.path.basename(file_path)}</b>")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(lbl)

        # ── search bar ───────────────────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search applications…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)

        # ── app list ──────────────────────────────────────────────────────────
        self._list = QListWidget()
        self._list.setIconSize(QSize(29, 29))
        self._list.itemDoubleClicked.connect(self._accept_item)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        lay.addWidget(self._list)
        self._populate(all_apps)

        # ── buttons ───────────────────────────────────────────────────────────
        row = QHBoxLayout()
        self._default_btn = QPushButton("Make Default")
        self._default_btn.setEnabled(False)
        self._default_btn.setToolTip(
            f"Set selected app as the default for {self._mime}")
        self._default_btn.clicked.connect(self._make_default)
        cancel = QPushButton("Cancel")
        self._open_btn = QPushButton("Open")
        self._open_btn.setDefault(True)
        self._open_btn.setEnabled(False)
        cancel.clicked.connect(self.reject)
        self._open_btn.clicked.connect(self._on_open)
        row.addWidget(self._default_btn)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(self._open_btn)
        lay.addLayout(row)

    def _populate(self, apps: list[dict]):
        self._list.clear()
        for app in apps:
            item = QListWidgetItem(app["name"])
            icon = QIcon.fromTheme(app["icon"])
            if not icon.isNull():
                item.setIcon(icon)
            item.setData(Qt.ItemDataRole.UserRole, app)
            self._list.addItem(item)

    def _filter(self, text: str):
        text = text.strip().lower()
        filtered = [a for a in self._all_apps
                    if text in a["name"].lower()] if text else self._all_apps
        self._populate(filtered)

    def _on_selection_changed(self, current, _previous):
        has = current is not None
        self._open_btn.setEnabled(has)
        self._default_btn.setEnabled(has)

    def _make_default(self):
        item = self._list.currentItem()
        if not item:
            return
        app = item.data(Qt.ItemDataRole.UserRole)
        desktop_file = os.path.basename(app.get("desktop_file", ""))
        if not desktop_file:
            QMessageBox.warning(self, "Make Default",
                "Could not determine the .desktop file for this application.")
            return
        try:
            subprocess.run(
                ["xdg-mime", "default", desktop_file, self._mime],
                check=True, timeout=5,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            QMessageBox.information(self, "Make Default",
                f"<b>{app['name']}</b> is now the default for <i>{self._mime}</i>.")
        except Exception as e:
            QMessageBox.critical(self, "Make Default", f"Failed to set default:\n{e}")

    def _accept_item(self, item):
        self._chosen = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _on_open(self):
        item = self._list.currentItem()
        if item:
            self._chosen = item.data(Qt.ItemDataRole.UserRole)
            self.accept()

    def chosen_app(self):
        return self._chosen


# ═══════════════════════════════════════════════════════════════════════════════
#  PROXY  (group-by-type sorting)
# ═══════════════════════════════════════════════════════════════════════════════

class GroupByTypeProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._group = False
        self._search = ""
        self._show_hidden = False
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_grouping(self, enabled: bool):
        self._group = enabled
        self.invalidate()

    def set_search(self, text: str):
        self._search = text.strip()
        self.invalidateFilter()

    def set_show_hidden(self, enabled: bool):
        self._show_hidden = enabled
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        src = self.sourceModel()
        idx = src.index(source_row, 0, source_parent)
        name = src.fileName(idx)

        # Hide dot-entries unless show_hidden is on — but always allow any
        # ancestor directory of TRASH_PATH so Trash is always navigable.
        if not self._show_hidden and name.startswith("."):
            full_path = src.filePath(idx)
            if not TRASH_PATH.startswith(full_path):
                return False

        if self._search:
            return self._search.lower() in name.lower()

        return super().filterAcceptsRow(source_row, source_parent)

    def flags(self, index: QModelIndex):
        f = super().flags(index)
        if index.column() == 0:
            f |= Qt.ItemFlag.ItemIsEditable
        return f

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        # Reformat the date column to 24h to override system-locale 12h format
        if role == Qt.ItemDataRole.DisplayRole and index.column() == 3:
            src_idx = self.mapToSource(index)
            path = self.sourceModel().filePath(src_idx.siblingAtColumn(0))
            try:
                mtime = os.path.getmtime(path)
                return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d  %H:%M")
            except OSError:
                pass
        return super().data(index, role)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        src = self.sourceModel()
        ld, rd = src.isDir(left), src.isDir(right)
        if ld != rd:
            return ld  # dirs first
        if not ld:
            ln = src.fileName(left); rn = src.fileName(right)
            le = os.path.splitext(ln)[1].lower(); re_ = os.path.splitext(rn)[1].lower()
            if le != re_: return le < re_
            return ln.lower() < rn.lower()
        return super().lessThan(left, right)


# ═══════════════════════════════════════════════════════════════════════════════
#  PROPERTIES DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

class PropertiesDialog(QDialog):
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Properties"); self.setMinimumWidth(456)
        lay = QFormLayout(self); lay.setVerticalSpacing(8)
        stat   = os.stat(path)
        is_dir = os.path.isdir(path)
        size   = self._dir_size(path) if is_dir else self._fmt(stat.st_size)
        mod    = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d  %H:%M:%S")
        kind   = "Folder" if is_dir else (os.path.splitext(path)[1] or "File")
        lay.addRow("Name:",     QLabel(os.path.basename(path)))
        lay.addRow("Location:", QLabel(os.path.dirname(path)))
        lay.addRow("Type:",     QLabel(kind))
        lay.addRow("Size:",     QLabel(size))
        lay.addRow("Modified:", QLabel(mod))
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(self.accept)
        lay.addRow(btns)

    @staticmethod
    def _fmt(n):
        for u in ("B","KB","MB","GB","TB"):
            if n < 1024: return f"{n:.1f} {u}"
            n /= 1024
        return f"{n:.1f} PB"

    @staticmethod
    def _dir_size(path):
        total = 0
        try:
            for dp, _, files in os.walk(path):
                for f in files:
                    try: total += os.path.getsize(os.path.join(dp, f))
                    except OSError: pass
        except OSError: pass
        return PropertiesDialog._fmt(total)


# ═══════════════════════════════════════════════════════════════════════════════
#  THUMBNAIL WORKER  (generates video previews off the main thread)
# ═══════════════════════════════════════════════════════════════════════════════

class FolderScanWorker(QObject):
    """Scans a folder in a background thread and signals whether it is a
    pure media folder (only images, only videos, or images + videos — no
    other file types mixed in).

    Emits ``finished(path, is_media)`` when done or cancelled.
    Rule: every file in the sample must be an image or video, and there must
    be at least MEDIA_MIN such files.
    """

    finished = pyqtSignal(str, bool)   # (path, is_media)

    MAX_SAMPLE = 200
    MEDIA_MIN  = 3      # need at least this many files to bother switching

    def __init__(self, path: str):
        super().__init__()
        self._path      = path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        media_exts = _IMAGE_EXTS | _VIDEO_EXTS
        try:
            entries = os.scandir(self._path)
        except OSError:
            self.finished.emit(self._path, False)
            return

        total = media = 0
        for entry in entries:
            if self._cancelled:
                self.finished.emit(self._path, False)
                return
            if entry.is_file(follow_symlinks=False):
                ext = os.path.splitext(entry.name)[1].lower()
                total += 1
                if ext in media_exts:
                    media += 1
                else:
                    # Non-media file found — not a pure media folder
                    self.finished.emit(self._path, False)
                    return
            if total >= self.MAX_SAMPLE:
                break

        # Pure media folder only if every sampled file was media
        is_media = media >= self.MEDIA_MIN
        self.finished.emit(self._path, is_media)


class ThumbnailWorker(QObject):
    """Runs _load_preview_pixmap in a background QThread and signals the result.

    Usage:
        self._thumb_worker = ThumbnailWorker(path)
        self._thumb_thread = QThread()
        self._thumb_worker.moveToThread(self._thumb_thread)
        self._thumb_thread.started.connect(self._thumb_worker.run)
        self._thumb_worker.finished.connect(self._on_thumbnail_ready)
        self._thumb_worker.finished.connect(self._thumb_thread.quit)
        self._thumb_thread.start()
    """

    finished = pyqtSignal(str, object)   # (path, QPixmap | None)

    def __init__(self, path: str, max_size: int = 240):
        super().__init__()
        self._path     = path
        self._max_size = max_size

    def run(self):
        from PyQt6.QtGui import QPixmap
        ext = os.path.splitext(self._path)[1].lower()
        px  = None

        if ext in _VIDEO_EXTS:
            import tempfile
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                     self._path],
                    capture_output=True, text=True, timeout=5,
                )
                try:
                    duration  = float(probe.stdout.strip())
                    seek_time = max(0.0, duration * 0.10)
                except (ValueError, TypeError):
                    seek_time = 0.0

                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                    tmp_path = tf.name

                result = subprocess.run(
                    ["ffmpeg", "-y", "-ss", str(seek_time),
                     "-i", self._path,
                     "-frames:v", "1",
                     "-vf", (f"scale={self._max_size}:{self._max_size}"
                             ":force_original_aspect_ratio=decrease"),
                     "-q:v", "3",
                     tmp_path],
                    capture_output=True, timeout=10,
                )
                if result.returncode == 0:
                    candidate = QPixmap(tmp_path)
                    if not candidate.isNull():
                        px = candidate
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            except Exception:
                pass

        self.finished.emit(self._path, px)


# ═══════════════════════════════════════════════════════════════════════════════
#  ICON-VIEW THUMBNAIL WORKER  (batch-loads image previews for icon/grid view)
# ═══════════════════════════════════════════════════════════════════════════════

class IconThumbWorker(QObject):
    """Load image thumbnails for a list of paths in a background thread.

    Emits one ``ready`` signal per path as soon as the pixmap is decoded.
    Skips paths already in ``_thumb_cache``.  Checks ``_cancelled`` between
    each file so the caller can abort the job when the folder changes.
    """

    ready = pyqtSignal(str, object)   # (path, QPixmap)

    def __init__(self, paths: list, size: int = THUMB_SIZE):
        super().__init__()
        self._paths     = paths
        self._size      = size
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        from PyQt6.QtGui import QPixmap, QImageReader
        for path in self._paths:
            if self._cancelled:
                return
            if path in _thumb_cache:
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext not in _IMAGE_EXTS or ext == ".svg":
                continue
            try:
                reader = QImageReader(path)
                reader.setAutoTransform(True)
                # Limit decode size for very large images — fast and memory-safe
                orig_size = reader.size()
                if orig_size.isValid():
                    tw, th = orig_size.width(), orig_size.height()
                    scale = self._size / max(tw, th, 1)
                    if scale < 1.0:
                        reader.setScaledSize(
                            orig_size.scaled(
                                int(tw * scale), int(th * scale),
                                Qt.AspectRatioMode.IgnoreAspectRatio,
                            )
                        )
                img = reader.read()
                if img.isNull():
                    continue
                px = QPixmap.fromImage(img).scaled(
                    self._size, self._size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                if not px.isNull():
                    _thumb_cache[path] = px
                    self.ready.emit(path, px)
            except Exception:
                pass

        # SVG thumbnails (need main-thread renderer — skip here; handled on demand)


# ═══════════════════════════════════════════════════════════════════════════════
#  DETAILS WORKER  (counts folder contents off the main thread)
# ═══════════════════════════════════════════════════════════════════════════════

class DetailsWorker(QObject):
    """Computes slow per-path stats (listdir count) in a background thread.

    finished emits (token, contents_str) where token is an opaque value the
    caller uses to discard stale results.
    """

    finished = pyqtSignal(object, str)   # (token, contents_str)

    def __init__(self, paths: list, token: object):
        super().__init__()
        self._paths = paths
        self._token = token

    def run(self):
        if len(self._paths) == 1 and os.path.isdir(self._paths[0]):
            # Single folder — just count direct children (fast)
            try:
                n = len(os.listdir(self._paths[0]))
                result = f"{n} item{'s' if n != 1 else ''}"
            except OSError:
                result = "—"
        else:
            result = "—"
        self.finished.emit(self._token, result)


# ═══════════════════════════════════════════════════════════════════════════════
#  SEARCH WORKER  (walks directory tree off the main thread)
# ═══════════════════════════════════════════════════════════════════════════════

class SearchWorker(QObject):
    """Recursively searches root_dir for entries matching query (case-insensitive).

    Emits results in batches of up to BATCH_SIZE so the UI can update live,
    and emits finished(total) when done or cancelled.
    """

    results_ready = pyqtSignal(list)   # list[str] — batch of matching paths
    finished      = pyqtSignal(int)    # total matches found

    BATCH_SIZE = 50

    def __init__(self, root_dir: str, query: str):
        super().__init__()
        self._root  = root_dir
        self._query = query.lower()
        self._cancelled = False
        self._proc  = None

    def cancel(self):
        self._cancelled = True
        if self._proc is not None:
            try:
                self._proc.kill()
            except Exception:
                pass

    def run(self):
        batch = []
        total = 0
        self._proc = None
        try:
            cmd = [
                "find", self._root,
                "-not", "-path", "*/.*",
                "-type", "f",
                "-iname", f"*{self._query}*",
            ]
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            for line in self._proc.stdout:
                if self._cancelled:
                    break
                path = line.rstrip("\n")
                if not path:
                    continue
                batch.append(path)
                total += 1
                if len(batch) >= self.BATCH_SIZE:
                    self.results_ready.emit(batch)
                    batch = []
            self._proc.wait()
        except Exception:
            pass

        if batch and not self._cancelled:
            self.results_ready.emit(batch)
        self.finished.emit(total)


class DeleteWorker(QObject):
    """Moves files to Trash (or permanently deletes them) on a background thread.

    Emits finished(errors) when done, where errors is a list of (path, message)
    tuples for any files that could not be processed.
    """

    finished = pyqtSignal(list)   # list[(path, error_str)]

    def __init__(self, paths: list, permanent: bool,
                 trash_files_dir: str, trash_info_dir: str):
        super().__init__()
        self._paths       = paths
        self._permanent   = permanent
        self._trash_files = trash_files_dir
        self._trash_info  = trash_info_dir
        self._cancelled   = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        from urllib.parse import quote
        errors = []
        os.makedirs(self._trash_files, exist_ok=True)
        os.makedirs(self._trash_info,  exist_ok=True)

        for p in self._paths:
            if self._cancelled:
                break
            try:
                if self._permanent:
                    shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
                    info = os.path.join(self._trash_info,
                                        os.path.basename(p) + ".trashinfo")
                    if os.path.exists(info):
                        os.remove(info)
                else:
                    name = os.path.basename(p)
                    dest      = os.path.join(self._trash_files, name)
                    info_dest = os.path.join(self._trash_info,  name + ".trashinfo")
                    stem, ext = os.path.splitext(name)
                    counter = 1
                    while os.path.exists(dest) or os.path.exists(info_dest):
                        unique    = f"{stem} ({counter}){ext}"
                        dest      = os.path.join(self._trash_files, unique)
                        info_dest = os.path.join(self._trash_info,  unique + ".trashinfo")
                        counter  += 1
                    deletion_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    with open(info_dest, "w") as f:
                        f.write("[Trash Info]\n")
                        f.write(f"Path={quote(os.path.abspath(p), safe='/')}\n")
                        f.write(f"DeletionDate={deletion_date}\n")
                    shutil.move(p, dest)
            except Exception as e:
                errors.append((p, str(e)))

        self.finished.emit(errors)


# ═══════════════════════════════════════════════════════════════════════════════
#  SEARCH RESULT MODEL  (streamable flat table, same columns as RecentModel)
# ═══════════════════════════════════════════════════════════════════════════════

class SearchResultModel(QAbstractTableModel):
    HEADERS = ["Name", "Location", "Size", "Date Modified"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[tuple] = []

    def append_paths(self, paths: list[str]):
        if not paths:
            return
        first = len(self._rows)
        last  = first + len(paths) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        for path in paths:
            try:
                stat    = os.stat(path)
                is_dir  = os.path.isdir(path)
                size    = "—" if is_dir else RecentModel._fmt(stat.st_size)
                date    = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                location = os.path.dirname(path)
                self._rows.append((os.path.basename(path), location, size, date, path))
            except Exception:
                pass
        self.endInsertRows()

    def rowCount(self, parent=QModelIndex()): return len(self._rows)
    def columnCount(self, parent=QModelIndex()): return 4

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return QVariant()

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._rows):
            return QVariant()
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return row[index.column()]
        if role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
            return resolve_icon(row[4], os.path.isdir(row[4]))
        if role == Qt.ItemDataRole.UserRole:
            return row[4]
        return QVariant()

    def filepath(self, row: int) -> str:
        return self._rows[row][4] if 0 <= row < len(self._rows) else ""


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB PANE  (one self-contained browser pane per tab)
# ═══════════════════════════════════════════════════════════════════════════════

class TabPane(QWidget):
    """A fully self-contained file-browser pane.

    Owns its own model, proxy, list_view, address_bar, sidebar, and navigation
    history. The parent FileExplorer only needs to forward toolbar button clicks
    to the active pane.

    Signals:
        title_changed(str)  — emitted whenever the visible folder name changes.
        nav_state_changed() — emitted so the toolbar can refresh back/fwd state.
    """

    COL_NAME, COL_SIZE, COL_TYPE, COL_DATE = 0, 1, 2, 3

    title_changed    = pyqtSignal(str)
    nav_state_changed = pyqtSignal()
    open_in_new_tab  = pyqtSignal(str)

    def __init__(self, shared_recent: "RecentFiles",
                 shared_apps: list, shared_favorites: "Favorites", parent=None):
        super().__init__(parent)
        self._recent    = shared_recent
        self._all_apps  = shared_apps
        self._favorites = shared_favorites

        self.history: list[str] = []
        self.history_index = -1
        self._clipboard_mode  = None   # local fallback only; use _get/set_clipboard
        self._clipboard_paths = []
        self._sort_col   = self.COL_NAME
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._group_by_type = True
        self._show_hidden   = False
        self._view_mode     = "list"   # "list" | "icons"
        self._view_prefs: dict[str, str] = self._load_view_prefs()
        self._in_recent = False
        self._in_search = False
        self._search_model = None
        self._search_worker = None
        self._search_thread: QThread | None = None
        self._search_graveyard: list = []
        self._thumb_thread: QThread | None = None   # background video-thumb thread
        self._thumb_worker: ThumbnailWorker | None = None
        self._thumb_graveyard: list = []

        self._icon_thumb_thread: QThread | None = None   # icon-view batch thumb thread
        self._icon_thumb_worker: IconThumbWorker | None = None

        self._scan_thread: QThread | None = None    # background folder-scan thread
        self._scan_worker: FolderScanWorker | None = None            # old threads kept alive until done

        self._det_thread: QThread | None = None     # background details worker thread
        self._det_worker: DetailsWorker | None = None
        self._det_graveyard: list = []
        self._det_token: object = None              # current request token

        self._del_thread: QThread | None = None     # background delete worker thread
        self._del_worker: DeleteWorker | None = None
        self._del_graveyard: list = []

        # Debounce timer: delays _update_details so rapid selection changes
        # (shift-click, rubber-band) only trigger one update when they settle.
        self._details_timer = QTimer(self)
        self._details_timer.setSingleShot(True)
        self._details_timer.setInterval(120)   # ms — imperceptible delay
        self._details_timer.timeout.connect(self._update_details)

        self._build_model()
        self._build_ui()
        self._connect_signals()

    # ── model ─────────────────────────────────────────────────────────────────
    def _build_model(self):
        self.model = QFileSystemModel()
        self.model.setRootPath("/")
        # Always include Hidden so the model can index .local/share/Trash.
        # Dot-file visibility is controlled by the proxy, not the model.
        self.model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden)
        self.proxy = GroupByTypeProxy(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.set_grouping(True)

    # ── ui ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.address_bar = BreadcrumbBar()

        self.sidebar = SidebarWidget(self._favorites)

        self.list_view = FileView()
        self.list_view.setModel(self.proxy)
        self.list_view.setColumnWidth(0, 260)
        self.list_view.setSortingEnabled(True)
        self.list_view.sortByColumn(self._sort_col, self._sort_order)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.setIconSize(QSize(22, 22))
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.list_view.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.list_view.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed)

        self._icon_delegate = IconDelegate(self.model, self.proxy)
        self.list_view.setItemDelegateForColumn(0, self._icon_delegate)

        # ── Icon / grid view ──────────────────────────────────────────────────
        self.icon_view = IconFileView()
        self.icon_view.setModel(self.proxy)
        self.icon_view.setViewMode(QListView.ViewMode.IconMode)
        self.icon_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.icon_view.setWrapping(True)
        self.icon_view.setGridSize(QSize(132, 132))
        self.icon_view.setIconSize(QSize(72, 72))
        self.icon_view.setSpacing(5)
        self.icon_view.setUniformItemSizes(True)
        self.icon_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.icon_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.icon_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.icon_view.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.icon_view.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed)
        self.icon_view.setWordWrap(True)
        # Separate delegate instance — sharing one delegate between two views
        # causes "commitData called with an editor that does not belong to this view"
        self._icon_delegate_grid = ImagePreviewDelegate(self.model, self.proxy)
        self.icon_view.setItemDelegate(self._icon_delegate_grid)

        # Stack that holds both views; only one is visible at a time
        self._view_stack = QStackedWidget()
        self._view_stack.addWidget(self.list_view)   # index 0 → list
        self._view_stack.addWidget(self.icon_view)   # index 1 → icons
        self._view_stack.setCurrentIndex(0)

        self._details_panel = self._build_details_panel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self._view_stack)
        splitter.addWidget(self._details_panel)
        splitter.setSizes([210, 440, 260])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(2, True)
        self._splitter = splitter

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        # address bar inside the pane (hidden — shown in toolbar by FileExplorer
        # when this pane is active; kept here so each tab has its own bar)
        lay.addWidget(self.address_bar)
        lay.addWidget(self._build_command_bar())
        lay.addWidget(splitter)

    # ── command bar ───────────────────────────────────────────────────────────
    def _cmd_sep(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        return sep

    def _cmd_btn(self, icon_key: str | None, label: str, tooltip: str) -> QPushButton:
        btn = QPushButton(label)
        if icon_key is not None:
            btn.setIcon(_cmd_icon(icon_key))
        btn.setIconSize(QSize(24, 24))
        btn.setToolTip(tooltip)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _build_command_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("commandBar")
        bar.setFixedHeight(43)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(7, 2, 7, 2)
        lay.setSpacing(2)

        # ── New group ──
        self._btn_new_folder = self._cmd_btn("new_folder", "New folder",  "New folder (Ctrl+N)")
        self._btn_new_file   = self._cmd_btn("new_file",   "New file",    "New empty file")
        lay.addWidget(self._btn_new_folder)
        lay.addWidget(self._btn_new_file)

        lay.addWidget(self._cmd_sep())

        # ── Clipboard group ──
        self._btn_cut   = self._cmd_btn("cut",   "Cut",   "Cut (Ctrl+X)")
        self._btn_copy  = self._cmd_btn("copy",  "Copy",  "Copy (Ctrl+C)")
        self._btn_paste = self._cmd_btn("paste", "Paste", "Paste (Ctrl+V)")
        for b in (self._btn_cut, self._btn_copy, self._btn_paste):
            lay.addWidget(b)

        lay.addWidget(self._cmd_sep())

        # ── Edit group ──
        self._btn_rename = self._cmd_btn("rename", "Rename", "Rename (F2)")
        self._btn_delete = self._cmd_btn("delete", "Delete", "Delete (Del)")
        lay.addWidget(self._btn_rename)
        lay.addWidget(self._btn_delete)

        lay.addWidget(self._cmd_sep())

        # ── Sort menu ──
        self._btn_sort = self._cmd_btn("sort", "Sort", "Sort options")
        self._btn_sort.setFixedWidth(108)
        lay.addWidget(self._btn_sort)

        # ── View mode toggle (list ↔ icons) ──
        self._btn_view_mode = self._cmd_btn("icon_view", "", "Switch to icon view (Ctrl+Shift+V)")
        self._btn_view_mode.setFixedWidth(38)
        self._btn_view_mode.setToolTip("Switch to icon view (Ctrl+Shift+V)")
        lay.addWidget(self._btn_view_mode)

        lay.addWidget(self._cmd_sep())

        # ── Empty Trash (shown only when in Trash) ──
        self._btn_empty_trash = self._cmd_btn("delete", "Empty Trash", "Permanently delete all items in Trash")
        self._btn_empty_trash.setVisible(False)
        lay.addWidget(self._btn_empty_trash)

        # ── Restore Files (shown only when in Trash) ──
        self._btn_restore = self._cmd_btn("restore", "Restore", "Restore selected files to their original locations")
        self._btn_restore.setVisible(False)
        lay.addWidget(self._btn_restore)

        lay.addStretch()

        # ── Details toggle (far right) ──
        self._btn_details = self._cmd_btn("details", "Details", "Toggle details panel")
        self._btn_details.setCheckable(True)
        self._btn_details.setChecked(True)
        lay.addWidget(self._btn_details)

        # initial enabled state
        self._refresh_cmd_bar()

        return bar

    def _refresh_cmd_bar(self):
        sel = self._selected_paths()
        n   = len(sel)
        has_sel     = n > 0
        _, clip_paths = self._get_clipboard()
        has_clip    = bool(clip_paths)
        single_file = n == 1

        self._btn_cut.setEnabled(has_sel)
        self._btn_copy.setEnabled(has_sel)
        self._btn_paste.setEnabled(has_clip)
        self._btn_rename.setEnabled(single_file)
        self._btn_delete.setEnabled(has_sel)

    def _refresh_cmd_icons(self):
        """Re-render all command bar icons to match the current palette."""
        keys = [
            (self._btn_new_folder, "new_folder"),
            (self._btn_new_file,   "new_file"),
            (self._btn_cut,        "cut"),
            (self._btn_copy,       "copy"),
            (self._btn_paste,      "paste"),
            (self._btn_rename,     "rename"),
            (self._btn_delete,     "delete"),
            (self._btn_sort,       "sort"),
            (self._btn_view_mode,  "icon_view"),
            (self._btn_details,    "details"),
            (self._btn_empty_trash,"delete"),
            (self._btn_restore,    "restore"),
        ]
        for btn, key in keys:
            if key:
                btn.setIcon(_cmd_icon(key))

    # ── details panel ─────────────────────────────────────────────────────────
    def _build_details_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("detailsPanel")
        panel.setMinimumWidth(276)
        panel.setMaximumWidth(360)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 19, 14, 14)
        lay.setSpacing(7)

        # icon / preview area
        self._det_icon = QLabel()
        self._det_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._det_icon.setMinimumHeight(64)
        self._det_icon.setMaximumHeight(210)
        self._det_icon.setStyleSheet(
            "background: transparent; border-radius: 6px;"
        )
        lay.addWidget(self._det_icon)

        # name (bold, word-wrap)
        self._det_name = QLabel()
        self._det_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._det_name.setWordWrap(True)
        self._det_name.setStyleSheet("font-weight: 600; font-size: 13px; color: palette(windowText);")
        lay.addWidget(self._det_name)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("QFrame { color: palette(mid); }")
        lay.addWidget(sep)

        # property rows
        self._det_type     = self._det_row(lay, "Type")
        self._det_size     = self._det_row(lay, "Size")
        self._det_contents = self._det_row(lay, "Contents")
        self._det_mod      = self._det_row(lay, "Modified")
        self._det_path     = self._det_row(lay, "Location")
        self._det_path.setWordWrap(True)

        lay.addStretch()

        return panel

    @staticmethod
    def _det_row(layout: QVBoxLayout, label: str) -> QLabel:
        """Add a label/value pair; return the value QLabel."""
        hdr = QLabel(label)
        hdr.setStyleSheet("font-size: 11px; color: palette(placeholderText); background: transparent;")
        layout.addWidget(hdr)
        val = QLabel("—")
        val.setStyleSheet("font-size: 12px; color: palette(windowText); background: transparent; margin-bottom: 6px;")
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(val)
        return val

    def _update_details(self):
        """Populate the details panel for the current selection."""
        self._cancel_thumb_job()
        self._cancel_det_job()

        sel = self._selected_paths()
        n   = len(sel)

        if n == 0:
            self._show_folder_details(self.address_bar.text())
            return

        if n > 1:
            self._det_icon.clear()
            self._det_name.setText(f"{n} items selected")
            self._det_type.setText("Multiple")
            self._det_size.setText("—")
            self._det_contents.setText(f"{n} items")
            self._det_mod.setText("—")
            self._det_path.setText("—")
            return

        path   = sel[0]
        is_dir = os.path.isdir(path)
        ext    = os.path.splitext(path)[1].lower()

        # ── Icon / preview (always instant) ───────────────────────────────────
        if is_dir or ext not in _VIDEO_EXTS:
            preview_px = None if is_dir else self._load_preview_pixmap(path, max_size=240)
            self._apply_preview(preview_px, path, is_dir)
        else:
            icon = resolve_icon(path, is_dir)
            self._det_icon.setPixmap(icon.pixmap(QSize(77, 77)))
            self._det_icon.setStyleSheet("background: transparent; border-radius: 6px;")
            self._start_thumb_job(path)

        # ── Cheap stat fields (instant) ────────────────────────────────────────
        self._det_name.setText(os.path.basename(path))
        try:
            stat   = os.stat(path)
            ext_up = ext.upper().lstrip(".") or "—"
            kind   = "Folder" if is_dir else (ext_up + " file" if ext_up != "—" else "File")
            size   = "—" if is_dir else RecentModel._fmt(stat.st_size)
            mod    = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d  %H:%M")
        except OSError:
            kind = size = mod = "—"
        self._det_type.setText(kind)
        self._det_size.setText(size)
        self._det_mod.setText(mod)
        self._det_path.setText(os.path.dirname(path))

        # ── Slow field: folder item count (async) ──────────────────────────────
        if is_dir:
            self._det_contents.setText("…")
            self._start_det_job([path])
        else:
            self._det_contents.setText("—")

    def _show_folder_details(self, path: str):
        """Fill the details panel with info about the current folder (no selection)."""
        self._cancel_det_job()

        if not path or not os.path.isdir(path):
            self._det_icon.clear()
            self._det_name.clear()
            for w in (self._det_type, self._det_size, self._det_contents,
                      self._det_mod, self._det_path):
                w.setText("—")
            return

        # ── Instant fields ─────────────────────────────────────────────────────
        icon = resolve_icon(path, True)
        self._det_icon.setPixmap(icon.pixmap(QSize(77, 77)))
        self._det_icon.setStyleSheet("background: transparent; border-radius: 6px;")
        self._det_name.setText(os.path.basename(path) or path)
        try:
            stat = os.stat(path)
            mod  = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d  %H:%M")
        except OSError:
            mod = "—"
        self._det_type.setText("Folder")
        self._det_size.setText("—")
        self._det_mod.setText(mod)
        self._det_path.setText(os.path.dirname(path))

        # ── Slow field: item count (async) ─────────────────────────────────────
        self._det_contents.setText("…")
        self._start_det_job([path])

    # ── async details worker helpers ──────────────────────────────────────────

    def _start_det_job(self, paths: list):
        """Spawn a background thread to compute folder item count."""
        token = object()                # unique sentinel for this request
        self._det_token = token
        worker = DetailsWorker(paths, token)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_det_ready)
        worker.finished.connect(thread.quit)
        self._det_graveyard = [
            (t, w) for t, w in self._det_graveyard if t.isRunning()
        ]
        self._det_worker = worker
        self._det_thread = thread
        thread.start()

    def _cancel_det_job(self):
        """Retire the current details worker without blocking."""
        self._det_token = None          # invalidate — any pending result is stale
        if self._det_worker is not None:
            try:
                self._det_worker.finished.disconnect(self._on_det_ready)
            except Exception:
                pass
        if self._det_thread is not None and self._det_thread.isRunning():
            self._det_graveyard.append((self._det_thread, self._det_worker))
        self._det_thread = None
        self._det_worker = None

    def _on_det_ready(self, token: object, contents: str):
        """Called on the main thread when the details worker finishes."""
        if token is self._det_token:    # only apply if still current
            self._det_contents.setText(contents)

    # ── async video thumbnail helpers ─────────────────────────────────────────

    def _apply_preview(self, preview_px, path: str, is_dir: bool):
        """Apply a preview pixmap (or icon fallback) to the details icon label."""
        if preview_px is not None:
            self._det_icon.setPixmap(preview_px)
            self._det_icon.setStyleSheet(
                "background: #E8E8E8; border-radius: 6px; padding: 4px;"
            )
        else:
            icon = resolve_icon(path, is_dir)
            self._det_icon.setPixmap(icon.pixmap(QSize(77, 77)))
            self._det_icon.setStyleSheet("background: transparent; border-radius: 6px;")

    def _start_thumb_job(self, path: str):
        """Spawn a background thread to generate a video thumbnail."""
        worker = ThumbnailWorker(path, max_size=240)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_thumbnail_ready)
        worker.finished.connect(thread.quit)
        # Clean up graveyard: drop any threads that have already finished
        self._thumb_graveyard = [
            (t, w) for t, w in self._thumb_graveyard if t.isRunning()
        ]
        self._thumb_worker = worker
        self._thumb_thread = thread
        thread.start()

    def _cancel_thumb_job(self):
        """Retire the current thumbnail thread without destroying it immediately.

        We can't safely delete the thread/worker while ffmpeg may still be
        running inside it.  Instead we disconnect the UI callback so a stale
        result never lands on the panel, then park the pair in a graveyard list
        so Python keeps them alive until the thread finishes naturally.
        """
        if self._thumb_worker is not None:
            try:
                self._thumb_worker.finished.disconnect(self._on_thumbnail_ready)
            except Exception:
                pass
        if self._thumb_thread is not None and self._thumb_thread.isRunning():
            # Park in graveyard so Qt objects stay alive until the thread stops
            self._thumb_graveyard.append((self._thumb_thread, self._thumb_worker))
        self._thumb_thread = None
        self._thumb_worker = None

    def _on_thumbnail_ready(self, path: str, px):
        """Called on the main thread when the background job delivers a frame."""
        # Ignore if the user already moved to a different file
        sel = self._selected_paths()
        if len(sel) == 1 and sel[0] == path:
            self._apply_preview(px, path, False)

    # ── preview thumbnail helpers ─────────────────────────────────────────────

    @staticmethod
    def _load_preview_pixmap(path: str, max_size: int = 240) -> "QPixmap | None":
        """Return a scaled preview QPixmap for image/video files, or None."""
        ext = os.path.splitext(path)[1].lower()

        # ── Image preview ──────────────────────────────────────────────────────
        if ext in _IMAGE_EXTS and ext != ".svg":
            try:
                px = QPixmap(path)
                if not px.isNull():
                    return px.scaled(
                        max_size, max_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
            except Exception:
                pass

        # ── SVG preview ────────────────────────────────────────────────────────
        if ext == ".svg":
            try:
                from PyQt6.QtSvg import QSvgRenderer
                renderer = QSvgRenderer(path)
                if renderer.isValid():
                    px = QPixmap(max_size, max_size)
                    px.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(px)
                    renderer.render(painter)
                    painter.end()
                    return px
            except Exception:
                pass

        # ── Video thumbnails are generated asynchronously by ThumbnailWorker ──
        # (nothing to do here for video files)

        return None

    def _toggle_details(self, checked: bool):
        if checked:
            self._details_panel.setMinimumWidth(276)
            self._details_panel.setMaximumWidth(360)
            sizes = self._splitter.sizes()
            total = sizes[1] + sizes[2]
            self._splitter.setSizes([sizes[0], total - 260, 260])
            self._update_details()
        else:
            self._cancel_thumb_job()
            self._details_panel.setMinimumWidth(0)
            self._details_panel.setMaximumWidth(0)
            sizes = self._splitter.sizes()
            self._splitter.setSizes([sizes[0], sizes[1] + sizes[2], 0])

    def _toggle_view_mode(self):
        """Switch between list view and icon/grid view, remembering per folder."""
        if self._view_mode == "list":
            self._view_mode = "icons"
            self._view_stack.setCurrentIndex(1)
            self.icon_view.setRootIndex(self.list_view.rootIndex())
            self._btn_view_mode.setIcon(_cmd_icon("list_view"))
            self._btn_view_mode.setToolTip("Switch to list view (Ctrl+Shift+V)")
            # Kick off thumbnail generation for the current folder
            path = self.address_bar.text()
            if path:
                self._start_icon_thumb_batch(path)
        else:
            self._view_mode = "list"
            self._view_stack.setCurrentIndex(0)
            self._btn_view_mode.setIcon(_cmd_icon("icon_view"))
            self._btn_view_mode.setToolTip("Switch to icon view (Ctrl+Shift+V)")
        # Persist the choice for this folder
        path = self.address_bar.text()
        if path:
            self._view_prefs[path] = self._view_mode
            self._save_view_prefs()

    @staticmethod
    def _load_view_prefs() -> dict:
        try:
            with open(VIEW_PREFS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_view_prefs(self):
        try:
            with open(VIEW_PREFS_JSON, "w", encoding="utf-8") as f:
                json.dump(self._view_prefs, f, indent=2)
        except Exception:
            pass

    def _apply_view_pref(self, path: str):
        """Switch to the remembered view mode for path, if any."""
        preferred = self._view_prefs.get(path)
        if preferred and preferred != self._view_mode:
            self._toggle_view_mode()

    # ── folder media scan (auto icon view) ────────────────────────────────────

    def _cancel_scan(self):
        """Signal the current scan worker to stop; the thread cleans itself up."""
        if self._scan_worker is not None:
            self._scan_worker.cancel()
            try:
                self._scan_worker.finished.disconnect(self._on_scan_finished)
            except Exception:
                pass
            self._scan_worker = None
        if self._scan_thread is not None:
            self._scan_thread.quit()
            self._scan_thread = None

    def _start_folder_scan(self, path: str):
        """Spawn a background scan; on completion auto-switch if media-heavy."""
        self._cancel_scan()
        worker = FolderScanWorker(path)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_scan_finished)
        worker.finished.connect(thread.quit)
        # Keep the thread object alive in the global registry until it stops,
        # then remove it — this prevents "QThread destroyed while running".
        _live_threads.add(thread)
        thread.finished.connect(lambda t=thread: _live_threads.discard(t))
        self._scan_worker = worker
        self._scan_thread = thread
        thread.start()

    def _on_scan_finished(self, path: str, is_media: bool):
        self._scan_worker = None
        self._scan_thread = None
        # Only act if the user is still on this folder and in list mode
        if self.address_bar.text() != path:
            return
        if self._view_mode != "list":
            return
        if is_media:
            self._toggle_view_mode()

    # ── icon-view thumbnail batch loading ─────────────────────────────────────

    def _start_icon_thumb_batch(self, directory: str):
        """Spawn a background thread to load image thumbnails for directory."""
        self._cancel_icon_thumb()
        if not os.path.isdir(directory):
            return
        try:
            paths = [
                os.path.join(directory, e)
                for e in os.listdir(directory)
                if os.path.splitext(e)[1].lower() in _IMAGE_EXTS
                and os.path.isfile(os.path.join(directory, e))
            ]
        except OSError:
            return
        if not paths:
            return

        worker = IconThumbWorker(paths, size=THUMB_SIZE)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.ready.connect(self._on_icon_thumb_ready)
        thread.finished.connect(lambda t=thread: _live_threads.discard(t))
        _live_threads.add(thread)
        self._icon_thumb_worker = worker
        self._icon_thumb_thread = thread
        thread.start()

    def _cancel_icon_thumb(self):
        if self._icon_thumb_worker is not None:
            self._icon_thumb_worker.cancel()
            try:
                self._icon_thumb_worker.ready.disconnect(self._on_icon_thumb_ready)
            except Exception:
                pass
        self._icon_thumb_worker = None
        self._icon_thumb_thread = None

    def _on_icon_thumb_ready(self, path: str, px):
        """Called on the main thread when one thumbnail is done — refresh view."""
        if self._view_mode == "icons":
            self.icon_view.viewport().update()

    def cleanup_threads(self):
        """Block until every background thread owned by this pane has stopped.

        Must be called before the pane (or the app) is destroyed so Qt never
        tears down a QThread object while its OS thread is still running.
        """
        self._cancel_scan()
        self._cancel_thumb_job()
        self._cancel_det_job()
        self._cancel_search()
        self._cancel_icon_thumb()
        # Cancel any in-flight delete and park it in the graveyard
        if self._del_worker is not None:
            self._del_worker.cancel()
        if self._del_thread is not None and self._del_thread.isRunning():
            self._del_graveyard.append((self._del_thread, self._del_worker))
        self._del_thread = None
        self._del_worker = None

        for graveyard in (self._thumb_graveyard,
                          self._det_graveyard,
                          self._search_graveyard,
                          self._del_graveyard):
            for thread, _ in graveyard:
                if thread.isRunning():
                    thread.quit()
                    thread.wait()
            graveyard.clear()

    def _reconnect_selection(self):
        """Re-bind selectionChanged after the list_view model is swapped."""
        try:
            self.list_view.selectionModel().selectionChanged.disconnect(
                self._on_selection_changed)
        except Exception:
            pass
        self.list_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed)
        try:
            self.icon_view.selectionModel().selectionChanged.disconnect(
                self._on_selection_changed)
        except Exception:
            pass
        self.icon_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed)

    # ── signals ───────────────────────────────────────────────────────────────
    def _connect_signals(self):
        self.list_view.doubleClicked.connect(self._on_double_click)
        self.list_view.go_up.connect(self.go_up)
        self.address_bar.navigate.connect(self.navigate_to)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)
        self.sidebar.navigate.connect(self._on_sidebar_navigate)
        self.sidebar.unmount_requested.connect(self._on_unmount_requested)

        # icon_view mirrors list_view for navigation and context menu
        self.icon_view.doubleClicked.connect(self._on_double_click)
        self.icon_view.customContextMenuRequested.connect(self._show_context_menu)
        self.icon_view.go_up.connect(self.go_up)
        self.icon_view.open_current.connect(self._open_current)
        self.icon_view.delete_sel.connect(self._cmd_delete)
        self.icon_view.perm_delete_sel.connect(self._cmd_perm_delete)
        self.icon_view.cut_sel.connect(self._cmd_cut)
        self.icon_view.copy_sel.connect(self._cmd_copy)
        self.icon_view.paste_sel.connect(lambda: self._paste(self.address_bar.text()))
        self.icon_view.refresh_req.connect(self._do_refresh)
        self.icon_view.new_folder_req.connect(lambda: self._new_folder(self.address_bar.text()))
        self.icon_view.new_file_req.connect(lambda: self._new_file(self.address_bar.text()))

        # keyboard shortcuts via FileView signals
        self.list_view.open_current.connect(self._open_current)
        self.list_view.delete_sel.connect(self._cmd_delete)
        self.list_view.perm_delete_sel.connect(self._cmd_perm_delete)
        self.list_view.cut_sel.connect(self._cmd_cut)
        self.list_view.copy_sel.connect(self._cmd_copy)
        self.list_view.paste_sel.connect(lambda: self._paste(self.address_bar.text()))
        self.list_view.refresh_req.connect(self._do_refresh)
        self.list_view.new_folder_req.connect(lambda: self._new_folder(self.address_bar.text()))
        self.list_view.new_file_req.connect(lambda: self._new_file(self.address_bar.text()))

        # command bar actions
        self._btn_new_folder.clicked.connect(
            lambda: self._new_folder(self.address_bar.text()))
        self._btn_new_file.clicked.connect(
            lambda: self._new_file(self.address_bar.text()))
        self._btn_cut.clicked.connect(self._cmd_cut)
        self._btn_copy.clicked.connect(self._cmd_copy)
        self._btn_paste.clicked.connect(
            lambda: self._paste(self.address_bar.text()))
        self._btn_rename.clicked.connect(self._cmd_rename)
        self._btn_delete.clicked.connect(self._cmd_delete)
        self._btn_sort.clicked.connect(self._show_sort_menu)
        self._btn_view_mode.clicked.connect(self._toggle_view_mode)
        self._btn_empty_trash.clicked.connect(self._empty_trash)
        self._btn_restore.clicked.connect(self._restore_selected)
        self._btn_details.toggled.connect(self._toggle_details)

        # keep cmd bar state fresh on selection change
        self.list_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed)
        self.icon_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed)

    def _on_selection_changed(self):
        self._refresh_cmd_bar()
        if self._btn_details.isChecked():
            self._details_timer.start()   # restarts if already running — debounce

    # ── command bar action helpers ────────────────────────────────────────────
    def _get_clipboard(self):
        win = self.window()
        if hasattr(win, '_shared_clipboard_mode'):
            return win._shared_clipboard_mode, win._shared_clipboard_paths
        return self._clipboard_mode, self._clipboard_paths

    def _set_clipboard(self, mode, paths):
        win = self.window()
        if hasattr(win, '_shared_clipboard_mode'):
            win._shared_clipboard_mode  = mode
            win._shared_clipboard_paths = paths
        else:
            self._clipboard_mode  = mode
            self._clipboard_paths = paths

    def _cmd_cut(self):
        sel = self._selected_paths()
        if sel:
            self._set_clipboard("cut", sel)
            self._refresh_cmd_bar()

    def _cmd_copy(self):
        sel = self._selected_paths()
        if sel:
            self._set_clipboard("copy", sel)
            self._refresh_cmd_bar()

    def _cmd_rename(self):
        sel = self.list_view.selectionModel().selectedRows(0)
        if len(sel) == 1:
            if not self._in_recent:
                self.list_view.edit(sel[0])

    def _cmd_delete(self):
        sel = self._selected_paths()
        if sel:
            self._delete(sel[0])

    def _cmd_perm_delete(self):
        """Permanently delete selected files (Shift+Delete), bypassing Trash."""
        paths = self._selected_paths()
        if not paths:
            return
        msg = (f'Permanently delete "{os.path.basename(paths[0])}"?\nThis cannot be undone.'
               if len(paths) == 1 else
               f'Permanently delete {len(paths)} items?\nThis cannot be undone.')
        r = QMessageBox.question(self, 'Delete Forever', msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        self._start_delete_job(paths, permanent=True)

    def _show_sort_menu(self):
        menu = QMenu(self)
        for label, col in [("Name",          self.COL_NAME),
                            ("Size",          self.COL_SIZE),
                            ("Type",          self.COL_TYPE),
                            ("Date modified", self.COL_DATE)]:
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(self._sort_col == col)
            act.triggered.connect(lambda checked, c=col: self._apply_sort(c))
        menu.addSeparator()
        grp = menu.addAction("Group by Type")
        grp.setCheckable(True)
        grp.setChecked(self._group_by_type)
        grp.triggered.connect(self._toggle_group_by_type)
        menu.addSeparator()
        hid = menu.addAction("Show Hidden Files")
        hid.setCheckable(True)
        hid.setChecked(self._show_hidden)
        hid.triggered.connect(self._toggle_show_hidden)
        btn = self._btn_sort
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _toggle_show_hidden(self):
        self._show_hidden = not self._show_hidden
        # Visibility is controlled by the proxy — never touch model.setFilter()
        # as that resets the Hidden flag needed to keep Trash indexed.
        self.proxy.set_show_hidden(self._show_hidden)

    # ── sidebar ───────────────────────────────────────────────────────────────
    def _on_sidebar_navigate(self, target: str):
        if target == RECENT_SENTINEL:
            self._show_recent_view()
        elif target == TRASH_PATH:
            self._show_trash_view()
        else:
            self.navigate_to(target)

    def _on_unmount_requested(self, root: str):
        # Navigate away if we are inside the drive
        if self.address_bar.text().startswith(root):
            self.navigate_to(HOME)
        # Drop all inotify watches by resetting the model root,
        # wait for Qt to process it, then unmount, then restore watches.
        self.model.setRootPath("")
        def _do():
            self.sidebar._do_unmount(root)
            self.model.setRootPath("/")
        QTimer.singleShot(300, _do)

    def _show_trash_view(self):
        # Ensure the directory exists
        try:
            os.makedirs(TRASH_PATH, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Trash", f"Cannot open Trash:\n{e}")
            return

        # Do NOT call setRootPath(TRASH_PATH) — that resets the model filter.
        # The model already watches "/" with Hidden included, so Trash is always
        # indexed. Just trigger navigation directly.
        def _do_navigate():
            src_index = self.model.index(TRASH_PATH)
            if not src_index.isValid():
                # Still not ready — wait for directoryLoaded
                def _on_loaded(p):
                    if os.path.normpath(p) == os.path.normpath(TRASH_PATH):
                        try:
                            self.model.directoryLoaded.disconnect(_on_loaded)
                        except Exception:
                            pass
                        self._navigate_to_trash()
                self.model.directoryLoaded.connect(_on_loaded)
            else:
                self._navigate_to_trash()

        QTimer.singleShot(0, _do_navigate)

    def _navigate_to_trash(self):
        src_index = self.model.index(TRASH_PATH)
        if not src_index.isValid():
            return
        self._leave_recent_view()
        proxy_index = self.proxy.mapFromSource(src_index)
        self.list_view.setRootIndex(proxy_index)
        self.icon_view.setRootIndex(proxy_index)
        self.address_bar.set_path(TRASH_PATH)
        self._update_pin_button()
        self._push_history(TRASH_PATH)
        self._update_nav()
        self.title_changed.emit("Trash")
        if self._btn_details.isChecked():
            self._update_details()

    # ── recent view ───────────────────────────────────────────────────────────
    def _show_recent_view(self):
        self._in_recent = True
        self._recent_model = RecentModel(self._recent.entries())
        self.list_view.setItemDelegateForColumn(0, QStyledItemDelegate())
        self.list_view.setModel(self._recent_model)
        self.list_view.setColumnWidth(0, 260)
        self.address_bar.set_path("Recent Files")
        self._push_history(RECENT_SENTINEL)
        self.title_changed.emit("Recent Files")
        self._reconnect_selection()
        self._refresh_cmd_bar()

    def _leave_recent_view(self):
        if not self._in_recent:
            return
        self._in_recent = False
        self.list_view.setItemDelegateForColumn(0, self._icon_delegate)
        self.list_view.setModel(self.proxy)
        self.list_view.setColumnWidth(0, 260)
        self._reconnect_selection()
        self._refresh_cmd_bar()

    # ── navigation ────────────────────────────────────────────────────────────
    def navigate_to(self, path: str, push_history: bool = True):
        if not os.path.isdir(path):
            return
        src_index = self.model.index(path)
        if not src_index.isValid():
            return
        self._cancel_scan()   # abort any scan from the previous folder
        self._leave_recent_view()
        self._leave_search_view()
        self.list_view.setRootIndex(self.proxy.mapFromSource(src_index))
        self.icon_view.setRootIndex(self.proxy.mapFromSource(src_index))
        self.address_bar.set_path(path)
        self._update_pin_button()
        if push_history:
            self._push_history(path)
        self._update_nav()
        label = "Trash" if path == TRASH_PATH else (os.path.basename(path) or path)
        self.title_changed.emit(label)
        # Update details: if nothing selected, this will show the new folder
        if self._btn_details.isChecked():
            self._update_details()
        # Restore remembered view mode for this folder
        self._apply_view_pref(path)
        # If no saved pref, scan for media content and auto-switch to icon view
        if path not in self._view_prefs:
            self._start_folder_scan(path)
        # Kick off thumbnail generation for icon view (harmless if list view)
        self._start_icon_thumb_batch(path)

    def _push_history(self, entry: str):
        self.history = self.history[: self.history_index + 1]
        self.history.append(entry)
        self.history_index = len(self.history) - 1
        self._update_nav()

    def _go_to_history(self, entry: str):
        if entry == RECENT_SENTINEL:
            self._show_recent_view()
        else:
            self.navigate_to(entry, push_history=False)

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self._go_to_history(self.history[self.history_index])

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._go_to_history(self.history[self.history_index])

    def go_up(self):
        if self._in_recent:
            return
        cur = self.address_bar.text()
        par = os.path.dirname(cur)
        if par and par != cur:
            self.navigate_to(par)

    def can_go_back(self)    -> bool: return self.history_index > 0
    def can_go_forward(self) -> bool: return self.history_index < len(self.history) - 1

    def set_search_filter(self, text: str):
        """Start a recursive search or clear if text is empty."""
        text = text.strip()
        if not text:
            self._leave_search_view()
            return
        if self._in_recent:
            return
        self._start_search(text)

    def clear_search(self):
        self._leave_search_view()

    # ── search view ───────────────────────────────────────────────────────────

    def _start_search(self, query: str):
        """Cancel any running search, then start a fresh one."""
        self._cancel_search()

        root = self.address_bar.text()
        if not os.path.isdir(root):
            return

        # Build / reset the live model
        self._search_model = SearchResultModel(parent=self)
        self._in_search = True

        # swap view to search model
        self.list_view.setItemDelegateForColumn(0, QStyledItemDelegate())
        self.list_view.setModel(self._search_model)
        self.list_view.setColumnWidth(0, 260)
        self._reconnect_selection()
        self._refresh_cmd_bar()

        # status in details panel
        if self._btn_details.isChecked():
            self._det_icon.clear()
            self._det_name.setText(f'Searching "{query}"\u2026')
            for w in (self._det_type, self._det_size, self._det_contents,
                      self._det_mod, self._det_path):
                w.setText("\u2014")

        # launch worker thread
        worker = SearchWorker(HOME, query)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.results_ready.connect(self._on_search_results)
        worker.finished.connect(self._on_search_finished)
        worker.finished.connect(thread.quit)

        self._search_worker = worker
        self._search_thread = thread
        thread.start()

    def _cancel_search(self):
        if self._search_worker is not None:
            self._search_worker.cancel()
            try:
                self._search_worker.results_ready.disconnect(self._on_search_results)
                self._search_worker.finished.disconnect(self._on_search_finished)
            except Exception:
                pass
        if self._search_thread is not None and self._search_thread.isRunning():
            self._search_graveyard.append((self._search_thread, self._search_worker))
        self._search_worker = None
        self._search_thread = None

    def _leave_search_view(self):
        if not self._in_search:
            return
        self._cancel_search()
        self._in_search = False
        self._search_model = None
        self.list_view.setItemDelegateForColumn(0, self._icon_delegate)
        self.list_view.setModel(self.proxy)
        self.list_view.setColumnWidth(0, 260)
        cur = self.address_bar.text()
        if os.path.isdir(cur):
            src_index = self.model.index(cur)
            if src_index.isValid():
                self.list_view.setRootIndex(self.proxy.mapFromSource(src_index))
                self.icon_view.setRootIndex(self.proxy.mapFromSource(src_index))
        self._reconnect_selection()
        self._refresh_cmd_bar()
        if self._btn_details.isChecked():
            self._update_details()

    def _on_search_results(self, paths: list):
        if self._search_model is not None:
            self._search_model.append_paths(paths)

    def _on_search_finished(self, total: int):
        if not self._in_search:
            return
        if self._btn_details.isChecked():
            self._det_name.setText(f"{total} result{'s' if total != 1 else ''} found")

    def _update_nav(self):
        self.nav_state_changed.emit()

    # ── context menu ──────────────────────────────────────────────────────────
    def _show_context_menu(self, pos: QPoint):
        active_view = self.icon_view if self._view_mode == "icons" else self.list_view
        global_pos = active_view.viewport().mapToGlobal(pos)
        menu = QMenu(self)

        if self._in_recent:
            index = active_view.indexAt(pos)
            if index.isValid():
                path = self._recent_model.filepath(index.row())
                menu.addAction("Open").triggered.connect(lambda: self._open(path, False))
                menu.addSeparator()
                menu.addAction("Properties").triggered.connect(
                    lambda: self._show_properties(path))
            menu.exec(global_pos)
            return

        proxy_index = active_view.indexAt(pos)

        if proxy_index.isValid():
            if proxy_index not in active_view.selectionModel().selectedRows():
                active_view.selectionModel().select(
                    proxy_index,
                    active_view.selectionModel().SelectionFlag.ClearAndSelect |
                    active_view.selectionModel().SelectionFlag.Rows)

            sel_paths = self._selected_paths()
            n = len(sel_paths)
            src_index = self.proxy.mapToSource(proxy_index)
            path   = self.model.filePath(src_index)
            is_dir = os.path.isdir(path)

            if n > 1:
                lbl = menu.addAction(f"{n} items selected")
                lbl.setEnabled(False)
                menu.addSeparator()
            else:
                menu.addAction("Open").triggered.connect(lambda: self._open(path, is_dir))
                if is_dir:
                    menu.addAction("Open in new tab").triggered.connect(
                        lambda checked=False, p=path: self.open_in_new_tab.emit(p))
                    menu.addAction("Open in Terminal").triggered.connect(
                        lambda checked=False, p=path: self._open_in_terminal(p))
                if not is_dir:
                    ow_menu = menu.addMenu("Open with")
                    mime    = _get_mime(path)
                    matched = _apps_for_mime(mime, self._all_apps)
                    for app in matched:
                        act = ow_menu.addAction(app["name"])
                        ic  = QIcon.fromTheme(app["icon"])
                        if not ic.isNull(): act.setIcon(ic)
                        act.triggered.connect(
                            lambda checked, a=app: _launch_app(a["exec"], path))
                    if matched: ow_menu.addSeparator()
                    ow_menu.addAction("Other application…").triggered.connect(
                        lambda: self._open_with_other(path))

            menu.addSeparator()
            # ── Compress ──────────────────────────────────────────────────────
            targets = sel_paths if n > 1 else [path]
            out_dir = os.path.dirname(path)
            base    = os.path.basename(path) if n == 1 else "archive"
            menu.addAction("Compress…").triggered.connect(
                lambda checked=False, t=targets, o=out_dir, b=base:
                    self._compress(t, o, b, ".zip"))
            menu.addSeparator()
            menu.addAction("Cut").triggered.connect(
                lambda: self._clipboard_set("cut", path))
            menu.addAction("Copy").triggered.connect(
                lambda: self._clipboard_set("copy", path))
            if self._clipboard_paths and is_dir and n == 1:
                menu.addAction("Paste").triggered.connect(lambda: self._paste(path))
            menu.addSeparator()
            if n == 1:
                def _start_rename(checked=False, pi=proxy_index):
                    name_idx = pi.sibling(pi.row(), 0)
                    self.list_view.edit(name_idx)
                menu.addAction("Rename").triggered.connect(_start_rename)
            menu.addAction("Delete").triggered.connect(lambda: self._delete(path))
            if n == 1:
                menu.addSeparator()
                menu.addAction("Properties").triggered.connect(
                    lambda: self._show_properties(path))
        else:
            cur = self.address_bar.text()
            menu.addAction("New Folder").triggered.connect(lambda: self._new_folder(cur))
            menu.addAction("New File").triggered.connect(lambda: self._new_file(cur))
            if self._clipboard_paths:
                menu.addSeparator()
                menu.addAction("Paste").triggered.connect(lambda: self._paste(cur))
            menu.addSeparator()
            menu.addAction("Open in Terminal").triggered.connect(
                lambda checked=False, p=cur: self._open_in_terminal(p))

            sort_menu = menu.addMenu("Sort by")
            for label, col in [("Name", self.COL_NAME), ("Size", self.COL_SIZE),
                                ("Type", self.COL_TYPE), ("Date modified", self.COL_DATE)]:
                act = sort_menu.addAction(label)
                act.setCheckable(True); act.setChecked(self._sort_col == col)
                act.triggered.connect(lambda checked, c=col: self._apply_sort(c))

            grp = menu.addAction("Group by Type")
            grp.setCheckable(True); grp.setChecked(self._group_by_type)
            grp.triggered.connect(self._toggle_group_by_type)
            menu.addSeparator()
            menu.addAction("Refresh").triggered.connect(lambda: self.navigate_to(cur))

        menu.exec(global_pos)

    # ── sort / group ──────────────────────────────────────────────────────────
    def _apply_sort(self, col: int):
        if self._sort_col == col:
            self._sort_order = (Qt.SortOrder.DescendingOrder
                                if self._sort_order == Qt.SortOrder.AscendingOrder
                                else Qt.SortOrder.AscendingOrder)
        else:
            self._sort_col   = col
            self._sort_order = Qt.SortOrder.AscendingOrder
        self.proxy.sort(self._sort_col, self._sort_order)
        self.list_view.sortByColumn(self._sort_col, self._sort_order)

    def _toggle_favorite(self):
        """Pin or unpin the current folder from Quick Access."""
        path = self.address_bar.text()
        if not os.path.isdir(path):
            return
        if self.sidebar.has_favorite(path):
            self.sidebar.remove_favorite(path)
        else:
            self.sidebar.add_favorite(path)
        self._update_pin_button()

    def _empty_trash(self):
        r = QMessageBox.question(
            self, "Empty Trash",
            "Permanently delete all items in the Trash?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        import shutil as _shutil
        errors = []
        try:
            for entry in os.scandir(TRASH_PATH):
                try:
                    if entry.is_dir(follow_symlinks=False):
                        _shutil.rmtree(entry.path)
                    else:
                        os.remove(entry.path)
                except Exception as e:
                    errors.append(f"{entry.name}: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Empty Trash", str(e))
            return
        if errors:
            QMessageBox.warning(self, "Empty Trash",
                                "Some items could not be deleted:\n" + "\n".join(errors))

    def _restore_selected(self):
        """Restore selected files from Trash to their original locations.

        Uses the FreeDesktop Trash spec: for each file in ~/.local/share/Trash/files/
        there is a matching .trashinfo in ~/.local/share/Trash/info/ that records the
        original path under the [Trash Info] section's 'Path' key.  If no .trashinfo
        exists the file is moved to the user's home directory as a fallback.
        """
        active_view = self.icon_view if self._view_mode == "icons" else self.list_view
        indexes = active_view.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self, "Restore", "Select one or more files to restore.")
            return

        TRASH_INFO_DIR = os.path.expanduser("~/.local/share/Trash/info")
        HOME_DIR = os.path.expanduser("~")
        errors = []
        restored = 0

        for proxy_index in indexes:
            src_index = self.proxy.mapToSource(proxy_index)
            src_path  = self.model.filePath(src_index)
            name      = os.path.basename(src_path)

            # Look up original path from .trashinfo
            trashinfo_path = os.path.join(TRASH_INFO_DIR, name + ".trashinfo")
            dest_path = None
            if os.path.exists(trashinfo_path):
                cfg = configparser.RawConfigParser()
                try:
                    cfg.read(trashinfo_path)
                    raw = cfg.get("Trash Info", "Path")
                    # Path may be percent-encoded
                    from urllib.parse import unquote
                    candidate = unquote(raw)
                    # Only use the original path if its parent directory still exists
                    if os.path.isdir(os.path.dirname(candidate) or "/"):
                        dest_path = candidate
                except Exception:
                    pass

            if not dest_path:
                # Fallback: restore to home directory
                dest_path = os.path.join(HOME_DIR, name)

            # Avoid overwriting an existing file at the destination
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(dest_path)
                counter = 1
                while os.path.exists(f"{base} ({counter}){ext}"):
                    counter += 1
                dest_path = f"{base} ({counter}){ext}"

            try:
                shutil.move(src_path, dest_path)
                # Remove the .trashinfo file if it exists
                if os.path.exists(trashinfo_path):
                    os.remove(trashinfo_path)
                restored += 1
            except Exception as e:
                errors.append(f"{name}: {e}")

        if errors:
            QMessageBox.warning(
                self, "Restore",
                f"Restored {restored} item(s) with errors:\n" + "\n".join(errors),
            )
        elif restored:
            QMessageBox.information(
                self, "Restore",
                f"Successfully restored {restored} item(s).",
            )

    def _update_pin_button(self):
        path = self.address_bar.text()
        in_trash = path == TRASH_PATH
        # Walk up widget hierarchy to find FileExplorer (TabPane lives inside
        # a QStackedWidget inside QTabWidget, not directly under FileExplorer)
        _explorer = self.parent()
        while _explorer is not None and not hasattr(_explorer, "_btn_pin"):
            _explorer = _explorer.parent()
        _pin_btn = getattr(_explorer, "_btn_pin", None)
        if _pin_btn:
            _pin_btn.setVisible(not in_trash)
        self._btn_empty_trash.setVisible(in_trash)
        self._btn_restore.setVisible(in_trash)
        if not in_trash:
            is_pinned = os.path.isdir(path) and self.sidebar.has_favorite(path)
            if _pin_btn:
                _pin_btn.setToolTip("Remove from favorites" if is_pinned else "Add to favorites")
                _pin_btn.setIcon(_cmd_icon("pin_add" if is_pinned else "pin_remove"))
                _pin_btn.setIconSize(QSize(24, 24))

    def _toggle_group_by_type(self, checked: bool):
        self._group_by_type = checked
        self.proxy.set_grouping(checked)
        self.proxy.sort(self._sort_col, self._sort_order)
        self.list_view.scheduleDelayedItemsLayout()

    # ── selection ─────────────────────────────────────────────────────────────
    def _selected_paths(self) -> list[str]:
        active_view = self.icon_view if self._view_mode == "icons" else self.list_view
        if self._in_recent:
            rows = {idx.row() for idx in active_view.selectionModel().selectedRows()}
            return [self._recent_model.filepath(r) for r in sorted(rows)
                    if self._recent_model.filepath(r)]
        if self._in_search:
            rows = {idx.row() for idx in active_view.selectionModel().selectedRows()}
            return [self._search_model.filepath(r) for r in sorted(rows)
                    if self._search_model and self._search_model.filepath(r)]
        paths = []
        for proxy_idx in active_view.selectionModel().selectedRows():
            src = self.proxy.mapToSource(proxy_idx)
            if src.isValid():
                paths.append(self.model.filePath(src))
        return paths

    # ── file actions ──────────────────────────────────────────────────────────
    def _open(self, path: str, is_dir: bool):
        if is_dir:
            self.navigate_to(path)
        else:
            subprocess.Popen(f'xdg-open "{path}"', shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._recent.add(path)

    def _compress(self, sources: list, out_dir: str, base_name: str, ext: str):
        """Hand off to the system's archive manager (File Roller, Ark, etc.)."""
        # Preferred archive managers in order
        managers = [
            "file-roller",   # GNOME
            "ark",           # KDE
            "xarchiver",     # XFCE / GTK
            "peazip",
            "engrampa",      # MATE
        ]
        binary = next((m for m in managers if shutil.which(m)), None)
        if binary is None:
            QMessageBox.warning(self, "Compress",
                "No archive manager found.\n"
                "Install File Roller (GNOME), Ark (KDE), or Xarchiver.")
            return

        # Build the command — all managers accept multiple paths as arguments
        # file-roller and engrampa: --add-to=<output>
        # ark: --add-to <output>
        # xarchiver: just open with files selected (no output flag)
        import shlex
        if binary in ("file-roller", "engrampa"):
            cmd = [binary, "--add"] + sources
        elif binary == "ark":
            cmd = [binary, "--add"] + sources
        else:
            cmd = [binary] + sources

        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            QMessageBox.critical(self, "Compress", f"Failed to launch {binary}:\n{e}")

    def _open_in_terminal(self, path: str):
        """Open a terminal emulator in the given directory.

        Checks $TERMINAL env var and x-terminal-emulator first, then falls
        back through a list of known terminals, with xterm as last resort.
        """
        terminals = [
            # (binary, args_to_set_working_dir)
            ("gnome-terminal", ["--working-directory", path]),
            ("konsole",        ["--workdir", path]),
            ("xfce4-terminal", ["--working-directory", path]),
            ("mate-terminal",  ["--working-directory", path]),
            ("tilix",          ["--working-directory", path]),
            ("alacritty",      ["--working-directory", path]),
            ("kitty",          ["--directory", path]),
            ("wezterm",        ["start", "--cwd", path]),
            ("xterm",          []),
        ]

        # Build candidate list: $TERMINAL and x-terminal-emulator go first
        candidates = []
        env_term = os.environ.get("TERMINAL", "").strip()
        if env_term and shutil.which(env_term):
            candidates.append((env_term, []))
        if shutil.which("x-terminal-emulator"):
            candidates.append(("x-terminal-emulator", []))
        candidates += terminals

        for binary, args in candidates:
            if shutil.which(binary):
                cmd = [binary] + args
                try:
                    subprocess.Popen(cmd, cwd=path,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                except Exception:
                    continue
                return

    def _open_with_other(self, path: str):
        dlg = OpenWithDialog(path, self._all_apps, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            app = dlg.chosen_app()
            if app:
                _launch_app(app["exec"], path)
                self._recent.add(path)

    def _clipboard_set(self, mode, path):
        sel = self._selected_paths()
        self._set_clipboard(mode, sel if path in sel else [path])

    def _paste(self, dest_dir):
        clip_mode, clip_paths = self._get_clipboard()
        for src in clip_paths:
            name = os.path.basename(src)
            dest = os.path.join(dest_dir, name)
            if os.path.exists(dest):
                r = QMessageBox.question(self, "Overwrite?",
                    f'"{name}" already exists. Overwrite?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if r != QMessageBox.StandardButton.Yes:
                    continue
            try:
                if clip_mode == "copy":
                    shutil.copytree(src, dest, dirs_exist_ok=True) \
                        if os.path.isdir(src) else shutil.copy2(src, dest)
                else:
                    shutil.move(src, dest)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        if clip_mode == "cut":
            self._set_clipboard(None, [])

    def _delete(self, path):
        sel = self._selected_paths()
        paths = sel if path in sel else [path]
        in_trash = self.address_bar.text() == TRASH_PATH

        if in_trash:
            msg = (f'Permanently delete "{os.path.basename(paths[0])}"?' if len(paths) == 1
                   else f"Permanently delete {len(paths)} items?\nThis cannot be undone.")
            r = QMessageBox.question(self, "Delete Forever", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.Yes:
                self._start_delete_job(paths, permanent=True)
        else:
            msg = (f'Move "{os.path.basename(paths[0])}" to Trash?' if len(paths) == 1
                   else f"Move {len(paths)} items to Trash?")
            r = QMessageBox.question(self, "Delete", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.Yes:
                self._start_delete_job(paths, permanent=False)

    def _start_delete_job(self, paths: list, permanent: bool):
        """Kick off a DeleteWorker on a background thread."""
        TRASH_FILES = TRASH_PATH
        TRASH_INFO  = os.path.expanduser("~/.local/share/Trash/info")
        # Park any still-running delete job in the graveyard
        if self._del_thread is not None and self._del_thread.isRunning():
            self._del_graveyard.append((self._del_thread, self._del_worker))
        worker = DeleteWorker(paths, permanent, TRASH_FILES, TRASH_INFO)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_delete_done)
        worker.finished.connect(thread.quit)
        self._del_worker = worker
        self._del_thread = thread
        thread.start()

    def _on_delete_done(self, errors: list):
        """Called on the main thread when the delete worker finishes."""
        # Prune finished graveyard entries
        self._del_graveyard = [(t, w) for t, w in self._del_graveyard if t.isRunning()]
        if errors:
            msg = "\n".join(f"{os.path.basename(p)}: {e}" for p, e in errors)
            QMessageBox.critical(self, "Delete Error", msg)

    def _new_folder(self, parent_dir):
        if self._in_recent or not os.path.isdir(parent_dir):
            return

        # Pick a unique placeholder name ("New Folder", "New Folder (2)", …)
        base = "New Folder"
        name = base
        n = 2
        while os.path.exists(os.path.join(parent_dir, name)):
            name = f"{base} ({n})"
            n += 1

        new_path = os.path.join(parent_dir, name)
        try:
            os.makedirs(new_path, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        # Wait for QFileSystemModel to register the new directory, then edit it.
        # directoryLoaded fires when the model has finished scanning parent_dir.
        def _on_loaded(loaded_path, _new_path=new_path):
            if os.path.normpath(loaded_path) != os.path.normpath(parent_dir):
                return
            try:
                self.model.directoryLoaded.disconnect(_on_loaded)
            except Exception:
                pass
            src_idx = self.model.index(_new_path)
            if not src_idx.isValid():
                return
            proxy_idx = self.proxy.mapFromSource(src_idx)
            if not proxy_idx.isValid():
                return
            active_view = self.icon_view if self._view_stack.currentIndex() == 1 else self.list_view
            active_view.setCurrentIndex(proxy_idx)
            active_view.scrollTo(proxy_idx)
            active_view.edit(proxy_idx)

        self.model.directoryLoaded.connect(_on_loaded)

        # Safety fallback: if directoryLoaded already fired (model had the dir
        # cached) the signal may never come again — try immediately too.
        QTimer.singleShot(0, lambda: _on_loaded(parent_dir))

    def _new_file(self, parent_dir):
        if self._in_recent or not os.path.isdir(parent_dir):
            return

        # Pick a unique placeholder name
        base = "New File"
        name = base
        n = 2
        while os.path.exists(os.path.join(parent_dir, name)):
            name = f"{base} ({n})"
            n += 1

        new_path = os.path.join(parent_dir, name)
        try:
            open(new_path, "w").close()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        def _on_loaded(loaded_path, _new_path=new_path):
            if os.path.normpath(loaded_path) != os.path.normpath(parent_dir):
                return
            try:
                self.model.directoryLoaded.disconnect(_on_loaded)
            except Exception:
                pass
            src_idx = self.model.index(_new_path)
            if not src_idx.isValid():
                return
            proxy_idx = self.proxy.mapFromSource(src_idx)
            if not proxy_idx.isValid():
                return
            active_view = self.icon_view if self._view_stack.currentIndex() == 1 else self.list_view
            active_view.setCurrentIndex(proxy_idx)
            active_view.scrollTo(proxy_idx)
            active_view.edit(proxy_idx)

        self.model.directoryLoaded.connect(_on_loaded)
        QTimer.singleShot(0, lambda: _on_loaded(parent_dir))

    def _show_properties(self, path):
        PropertiesDialog(path, self).exec()

    def _open_current(self):
        """Open all selected items (Enter key).

        - Single folder selected: navigate into it.
        - Multiple items: open every file with xdg-open; if the selection
          contains exactly one folder (and nothing else) navigate into it.
          Mixed selections (files + folders) open files and navigate into
          the first folder found.
        """
        paths = self._selected_paths()
        if not paths:
            return

        dirs  = [p for p in paths if os.path.isdir(p)]
        files = [p for p in paths if not os.path.isdir(p)]

        # Open all files with xdg-open
        for p in files:
            subprocess.Popen(f'xdg-open "{p}"', shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._recent.add(p)

        # Navigate into folder(s): if only one folder and no files, navigate;
        # if multiple folders, open each in a new tab via the parent window.
        if dirs and not files:
            if len(dirs) == 1:
                self.navigate_to(dirs[0])
            else:
                # Open first in current tab, rest in new tabs
                self.navigate_to(dirs[0])
                win = self.window()
                for d in dirs[1:]:
                    if hasattr(win, 'new_tab'):
                        win.new_tab(d)
        elif dirs:
            # Mixed: also open folders in new tabs
            win = self.window()
            for d in dirs:
                if hasattr(win, 'new_tab'):
                    win.new_tab(d)

    def _do_refresh(self):
        """Refresh the current directory view (Ctrl+R)."""
        path = self.address_bar.text()
        if self._in_recent:
            self._show_recent_view()
            return
        if os.path.isdir(path):
            self.navigate_to(path, push_history=False)

    def _on_double_click(self, index):
        if self._in_recent:
            path = self._recent_model.filepath(index.row())
            if path: self._open(path, False)
            return
        if self._in_search:
            path = self._search_model.filepath(index.row())
            if path:
                if os.path.isdir(path):
                    self.navigate_to(path)
                else:
                    self._open(path, False)
            return
        src  = self.proxy.mapToSource(index)
        path = self.model.filePath(src)
        if os.path.isdir(path):
            self.navigate_to(path)
        else:
            self._open(path, False)


# ═══════════════════════════════════════════════════════════════════════════════
#  PLUS TAB BAR  (tab bar with inline "+" button right after the last tab)
# ═══════════════════════════════════════════════════════════════════════════════

class _PlusTabBar(QTabBar):
    """QTabBar with a painted X close button per tab and a '+' after the last tab."""

    new_tab_requested = pyqtSignal()
    _PLUS_W = 28
    _TAB_W  = 204
    _CLOSE_SIZE = 16   # painted close button square

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plus_rect = None
        self._close_rects = {}   # index -> QRect
        self.setMouseTracking(True)
        self.setExpanding(False)
        self.setTabsClosable(False)   # we paint our own X — disable native button

    def tabSizeHint(self, index):
        s = super().tabSizeHint(index)
        return QSize(self._TAB_W, s.height())

    def minimumTabSizeHint(self, index):
        return self.tabSizeHint(index)

    def paintEvent(self, event):
        from PyQt6.QtCore import QRect, QRectF
        super().paintEvent(event)

        n = self.count()
        if n == 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        pal      = self.palette()
        cursor   = self.mapFromGlobal(self.cursor().pos())
        ink_norm = pal.color(QPalette.ColorRole.PlaceholderText)
        ink_hot  = pal.color(QPalette.ColorRole.WindowText)
        hover_bg = QColor(pal.color(QPalette.ColorRole.WindowText))
        hover_bg.setAlpha(35)

        cs = self._CLOSE_SIZE
        self._close_rects = {}

        for i in range(n):
            rect = self.tabRect(i)
            # close button: right-aligned inside tab, vertically centred
            cx = rect.right() - cs - 6
            cy = rect.top() + (rect.height() - cs) // 2
            close_rect = QRect(cx, cy, cs, cs)
            self._close_rects[i] = close_rect

            hovered = close_rect.contains(cursor)

            # hover background pill
            if hovered:
                p.setPen(Qt.PenStyle.NoPen)
                path = QPainterPath()
                path.addRoundedRect(QRectF(close_rect), 3, 3)
                p.fillPath(path, QBrush(hover_bg))

            # draw X — two diagonal lines
            arm = 4
            ccx = close_rect.center().x()
            ccy = close_rect.center().y()
            pen = QPen(ink_hot if hovered else ink_norm, 1.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(ccx - arm, ccy - arm, ccx + arm, ccy + arm)
            p.drawLine(ccx + arm, ccy - arm, ccx - arm, ccy + arm)

        # + button — after last tab
        last = self.tabRect(n - 1)
        bw = self._PLUS_W - 4
        bh = min(bw, self.height() - 6)
        px = last.right() + 4
        py = (self.height() - bh) // 2
        self._plus_rect = QRect(px, py, bw, bh)

        plus_hovered = self._plus_rect.contains(cursor)
        if plus_hovered:
            p.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            path.addRoundedRect(QRectF(self._plus_rect), 3, 3)
            p.fillPath(path, QBrush(hover_bg))

        pen = QPen(ink_hot if plus_hovered else ink_norm, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        pcx = self._plus_rect.center().x()
        pcy = self._plus_rect.center().y()
        arm = 5
        p.drawLine(pcx - arm, pcy, pcx + arm, pcy)
        p.drawLine(pcx, pcy - arm, pcx, pcy + arm)

    def _close_rect_at(self, pos):
        for i, r in self._close_rects.items():
            if r.contains(pos):
                return i
        return -1

    def _is_empty_area(self, pos):
        if self._plus_rect is None:
            return False
        # only the space strictly to the right of the + button is empty
        return pos.x() > self._plus_rect.right()

    def _main_window(self):
        w = self.parent()
        while w and not hasattr(w, '_drag_pos'):
            w = w.parent()
        return w

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._plus_rect and self._plus_rect.contains(event.pos()):
                event.accept()
                return
            if self._close_rect_at(event.pos()) >= 0:
                event.accept()
                return
            if self._is_empty_area(event.pos()):
                mw = self._main_window()
                if mw:
                    if mw._maximized:
                        mw.showNormal()
                        mw._maximized = False
                        mw._btn_max.setText('□')
                    # Use the native window system move — works on all platforms
                    win = mw.windowHandle()
                    if win:
                        win.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._plus_rect and self._plus_rect.contains(event.pos()):
                self.new_tab_requested.emit()
                event.accept()
                return
            idx = self._close_rect_at(event.pos())
            if idx >= 0:
                self.tabCloseRequested.emit(idx)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)


# ═══════════════════════════════════════════════════════════════════════════════
#  WINDOW CONTROL BUTTONS  (painted — no text/font dependency)
# ═══════════════════════════════════════════════════════════════════════════════

class _WinCtrlButton(QToolButton if True else None):
    """
    A frameless window-control button that paints its own icon via QPainter
    so size, stroke, and vertical alignment are fully independent of the font.

    kind: 'min' | 'max' | 'close'
    """

    _KIND_MIN   = "min"
    _KIND_MAX   = "max"
    _KIND_CLOSE = "close"

    def __init__(self, kind: str, obj_name: str, tip: str, parent=None):
        from PyQt6.QtWidgets import QToolButton as _QTB
        super(_WinCtrlButton, self).__init__(parent)
        self._kind = kind
        self.setObjectName(obj_name)
        self.setToolTip(tip)
        self.setFixedSize(46, 40)
        self.setAutoRaise(True)
        self.setText("")           # no text — we paint everything

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        # Draw background via style (handles hover/pressed from QSS)
        from PyQt6.QtWidgets import QStyleOption, QStyle
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)

        # Pick icon colour from palette
        if not self.isEnabled():
            color = self.palette().color(QPalette.ColorRole.PlaceholderText)
        else:
            color = self.palette().color(QPalette.ColorRole.WindowText)

        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(color)
        pen.setWidthF(1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        if self._kind == self._KIND_MIN:
            # Horizontal dash — 10 px wide, vertically centred
            half = 5.0
            p.drawLine(
                QPoint(int(cx - half), int(cy + 1)),
                QPoint(int(cx + half), int(cy + 1)),
            )

        elif self._kind == self._KIND_MAX:
            # Hollow square — 10×10, centred
            s = 5.0
            from PyQt6.QtCore import QRectF
            p.drawRect(QRectF(cx - s, cy - s, s * 2, s * 2))

        elif self._kind == self._KIND_CLOSE:
            # × — two 10-px diagonal lines through centre
            half = 5.0
            p.drawLine(
                QPoint(int(cx - half), int(cy - half)),
                QPoint(int(cx + half), int(cy + half)),
            )
            p.drawLine(
                QPoint(int(cx + half), int(cy - half)),
                QPoint(int(cx - half), int(cy + half)),
            )

        p.end()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  TERMINAL PANEL  –  VT100 screen-buffer renderer
# ═══════════════════════════════════════════════════════════════════════════════
#
#  Architecture
#  ────────────
#  _VTScreen   – a 2-D grid of (char, attrs) cells + a cursor.
#                Parses every byte the PTY emits: SGR colors, cursor movement,
#                erase commands, bracketed-paste/OSC/DCS are silently consumed.
#  _TerminalView – QPlainTextEdit that owns a PTY fd and a _VTScreen.
#                On each timer tick it reads PTY bytes → feeds _VTScreen →
#                re-renders changed lines into the widget.
#  _TerminalPanel – header bar (Clear / Close) + _TerminalView.
#
# ─────────────────────────────────────────────────────────────────────────────

# Standard 16-color xterm palette (indices 0-15)
_PALETTE16 = [
    "#1E1E1E","#CC0000","#4E9A06","#C4A000",
    "#3465A4","#75507B","#06989A","#D3D7CF",
    "#555753","#EF2929","#8AE234","#FCE94F",
    "#729FCF","#AD7FA8","#34E2E2","#EEEEEC",
]

def _xterm_color(n: int) -> str:
    """Map xterm-256 index → hex color string."""
    if n < 16:
        return _PALETTE16[n]
    if 16 <= n <= 231:
        n -= 16
        b = n % 6; n //= 6
        g = n % 6; r = n // 6
        def v(x): return 0 if x == 0 else 55 + x * 40
        return "#{:02X}{:02X}{:02X}".format(v(r), v(g), v(b))
    c = 8 + (n - 232) * 10
    return "#{0:02X}{0:02X}{0:02X}".format(c)


class _Attrs:
    """Character display attributes (colors + style flags)."""
    __slots__ = ("fg","bg","bold","italic","underline","reverse")
    DEFAULT_FG = "#D4D4D4"
    DEFAULT_BG = "#1E1E1E"

    def __init__(self):
        self.fg        = self.DEFAULT_FG
        self.bg        = self.DEFAULT_BG
        self.bold      = False
        self.italic    = False
        self.underline = False
        self.reverse   = False

    def copy(self):
        a = _Attrs()
        a.fg = self.fg; a.bg = self.bg
        a.bold = self.bold; a.italic = self.italic
        a.underline = self.underline; a.reverse = self.reverse
        return a

    def __eq__(self, o):
        return (isinstance(o, _Attrs) and
                self.fg == o.fg and self.bg == o.bg and
                self.bold == o.bold and self.italic == o.italic and
                self.underline == o.underline and self.reverse == o.reverse)


class _VTScreen:
    """
    Minimal VT100/xterm-256 screen buffer.

    Handles:
      • All CSI sequences: SGR (colors/style), cursor movement (A/B/C/D/H/f),
        erase in line/display (EL/ED), scroll up/down, save/restore cursor,
        insert/delete lines, DEC private modes (?…h/l — silently consumed).
      • OSC sequences (title setting etc.) — silently consumed.
      • DCS / PM / APC — silently consumed.
      • Bracketed paste markers — silently consumed.
      • BEL, BS, HT, CR, LF/VT/FF — correctly handled.
    """

    # Tokeniser: matches any complete escape/control sequence OR a single char.
    _RE = re.compile(
        r"\x1b\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]"   # CSI
        r"|\x1b[PX^_].*?\x1b\\"                           # DCS/SOS/PM/APC (ST-terminated)
        r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"            # OSC
        r"|\x1b[^[\]PX^_]"                                # ESC + single char (e.g. ESC M)
        r"|[\x00-\x1f]"                                   # single C0 control
        r"|[^\x00-\x1f\x1b]+",                            # plain text run
        re.DOTALL,
    )

    def __init__(self, rows: int = 24, cols: int = 80):
        self.rows = rows
        self.cols = cols
        # screen: list of rows; each row = list of [char, _Attrs]
        self._screen: list[list[list]] = self._blank_screen()
        # dirty flags — which lines need re-rendering
        self._dirty: set[int] = set(range(rows))
        self._cur_row = 0
        self._cur_col = 0
        self._saved   = (0, 0)
        self._attrs   = _Attrs()
        self._buf     = ""           # leftover incomplete escape data
        # scroll region (DECSTBM) — rows are 0-based inclusive
        self._scroll_top = 0
        self._scroll_bot = rows - 1
        # scrollback: lines pushed off the top are appended here
        self._scrollback: list[list] = []
        self._new_scrollback: list[list] = []  # lines added since last flush

    # ── public ────────────────────────────────────────────────────────────────

    def feed(self, data: bytes):
        text = self._buf + data.decode("utf-8", errors="replace")
        self._buf = ""
        # If text ends mid-escape, hold back
        if text.endswith("\x1b") or re.search(r"\x1b[\[\]][^\x07\x1b]*$", text):
            self._buf = text[text.rfind("\x1b"):]
            text = text[:text.rfind("\x1b")]
        for tok in self._RE.findall(text):
            self._dispatch(tok)

    def resize(self, rows: int, cols: int):
        if rows == self.rows and cols == self.cols:
            return
        new = self._blank_screen_size(rows, cols)
        for r in range(min(rows, self.rows)):
            for c in range(min(cols, self.cols)):
                new[r][c] = self._screen[r][c]
        self._screen = new
        self._dirty  = set(range(rows))
        self.rows = rows; self.cols = cols
        self._cur_row = min(self._cur_row, rows - 1)
        self._cur_col = min(self._cur_col, cols - 1)
        self._scroll_top = 0
        self._scroll_bot = rows - 1
        # scrollback survives resize

    def get_dirty_lines(self) -> list[tuple[int, list]]:
        """Return [(row_index, row_cells), …] for lines that changed since last call."""
        out = [(r, self._screen[r]) for r in sorted(self._dirty)]
        self._dirty.clear()
        return out

    def get_cursor(self) -> tuple[int, int]:
        return self._cur_row, self._cur_col

    def flush_scrollback(self) -> list[list]:
        """Return any lines newly pushed into scrollback since last call, then clear."""
        out = self._new_scrollback
        self._new_scrollback = []
        return out

    def all_lines(self) -> list[list]:
        return self._screen

    # ── internals ─────────────────────────────────────────────────────────────

    def _blank_screen(self):
        return self._blank_screen_size(self.rows, self.cols)

    @staticmethod
    def _blank_screen_size(rows, cols):
        return [[[" ", _Attrs()] for _ in range(cols)] for _ in range(rows)]

    def _blank_line(self):
        return [[" ", _Attrs()] for _ in range(self.cols)]

    def _dispatch(self, tok: str):
        if not tok:
            return

        # ── C0 controls ───────────────────────────────────────────────────────
        if len(tok) == 1 and ord(tok) < 0x20:
            c = ord(tok)
            if c == 0x07:   pass                          # BEL
            elif c == 0x08: self._cur_col = max(0, self._cur_col - 1)  # BS
            elif c == 0x09:                               # HT – next tab stop
                self._cur_col = min(self.cols - 1, (self._cur_col // 8 + 1) * 8)
            elif c == 0x0d:                               # CR
                self._cur_col = 0
                self._dirty.add(self._cur_row)
            elif c in (0x0a, 0x0b, 0x0c):                 # LF/VT/FF
                if self._cur_row == self._scroll_bot:
                    self._scroll_up(1)
                else:
                    self._cur_row = min(self.rows - 1, self._cur_row + 1)
                self._dirty.add(self._cur_row)
            return

        # ── ESC sequences (non-CSI) ───────────────────────────────────────────
        if tok.startswith("\x1b") and not tok.startswith("\x1b["):
            # ESC M = reverse index (scroll down)
            if tok == "\x1bM":
                if self._cur_row == self._scroll_top:
                    self._scroll_down(1)
                else:
                    self._cur_row = max(0, self._cur_row - 1)
            # ESC 7 = save cursor, ESC 8 = restore
            elif tok == "\x1b7": self._saved = (self._cur_row, self._cur_col)
            elif tok == "\x1b8": self._cur_row, self._cur_col = self._saved
            # everything else (OSC, DCS, etc.) → silently ignored
            return

        # ── CSI sequences ─────────────────────────────────────────────────────
        if tok.startswith("\x1b["):
            inner = tok[2:]
            if not inner:
                return
            final = inner[-1]
            params_str = inner[:-1]

            # DEC private: ?…h / ?…l  (bracketed paste, mouse, alt screen …)
            if params_str.startswith("?"):
                return  # silently consume all DEC privates

            # Parse numeric params
            def nums(default=0):
                parts = params_str.split(";") if params_str else []
                return [int(p) if p else default for p in parts] or [default]

            def num(default=0):
                return nums(default)[0]

            if final == "m":                          # SGR
                self._sgr(nums(0))

            elif final in "Hf":                       # CUP / HVP
                ps = nums(1)
                r = (ps[0] if ps else 1) - 1
                c = (ps[1] if len(ps) > 1 else 1) - 1
                self._dirty.add(self._cur_row)
                self._cur_row = max(0, min(self.rows - 1, r))
                self._cur_col = max(0, min(self.cols - 1, c))
                self._dirty.add(self._cur_row)

            elif final == "A":                        # CUU
                self._dirty.add(self._cur_row)
                self._cur_row = max(0, self._cur_row - max(1, num(1)))
                self._dirty.add(self._cur_row)
            elif final == "B":                        # CUD
                self._dirty.add(self._cur_row)
                self._cur_row = min(self.rows - 1, self._cur_row + max(1, num(1)))
                self._dirty.add(self._cur_row)
            elif final == "C":                        # CUF
                self._cur_col = min(self.cols - 1, self._cur_col + max(1, num(1)))
                self._dirty.add(self._cur_row)
            elif final == "D":                        # CUB
                self._cur_col = max(0, self._cur_col - max(1, num(1)))
                self._dirty.add(self._cur_row)
            elif final == "E":                        # CNL
                self._dirty.add(self._cur_row)
                self._cur_row = min(self.rows - 1, self._cur_row + max(1, num(1)))
                self._cur_col = 0
                self._dirty.add(self._cur_row)
            elif final == "F":                        # CPL
                self._dirty.add(self._cur_row)
                self._cur_row = max(0, self._cur_row - max(1, num(1)))
                self._cur_col = 0
                self._dirty.add(self._cur_row)
            elif final == "G":                        # CHA
                self._cur_col = max(0, min(self.cols - 1, num(1) - 1))
                self._dirty.add(self._cur_row)
            elif final == "d":                        # VPA
                self._dirty.add(self._cur_row)
                self._cur_row = max(0, min(self.rows - 1, num(1) - 1))
                self._dirty.add(self._cur_row)

            elif final == "s":                        # SCP
                self._saved = (self._cur_row, self._cur_col)
            elif final == "u":                        # RCP
                self._dirty.add(self._cur_row)
                self._cur_row, self._cur_col = self._saved
                self._dirty.add(self._cur_row)

            elif final == "r":                        # DECSTBM – set scroll region
                ps = nums(0)
                top = max(0, (ps[0] if ps[0] else 1) - 1)
                bot = (ps[1] if len(ps) > 1 and ps[1] else self.rows) - 1
                bot = min(self.rows - 1, bot)
                if top < bot:
                    self._scroll_top = top
                    self._scroll_bot = bot
                # DECSTBM resets cursor to home
                self._dirty.add(self._cur_row)
                self._cur_row = 0
                self._cur_col = 0

            elif final == "J":                        # ED – erase display
                n = num(0)
                if n == 0:   # cursor to end
                    self._erase_line_from(self._cur_row, self._cur_col)
                    for r in range(self._cur_row + 1, self.rows):
                        self._screen[r] = self._blank_line()
                        self._dirty.add(r)
                elif n == 1: # start to cursor
                    for r in range(self._cur_row):
                        self._screen[r] = self._blank_line()
                        self._dirty.add(r)
                    self._erase_line_to(self._cur_row, self._cur_col)
                elif n in (2, 3):  # whole screen
                    self._screen = self._blank_screen()
                    self._dirty = set(range(self.rows))

            elif final == "K":                        # EL – erase line
                n = num(0)
                if n == 0:   self._erase_line_from(self._cur_row, self._cur_col)
                elif n == 1: self._erase_line_to(self._cur_row, self._cur_col)
                elif n == 2: self._screen[self._cur_row] = self._blank_line(); self._dirty.add(self._cur_row)

            elif final == "L":                        # IL – insert lines
                n = max(1, num(1))
                for _ in range(n):
                    self._screen.insert(self._cur_row, self._blank_line())
                    self._screen.pop()
                self._dirty = set(range(self.rows))

            elif final == "M":                        # DL – delete lines
                n = max(1, num(1))
                for _ in range(n):
                    self._screen.pop(self._cur_row)
                    self._screen.append(self._blank_line())
                self._dirty = set(range(self.rows))

            elif final == "S":                        # SU – scroll up
                self._scroll_up(max(1, num(1)))
            elif final == "T":                        # SD – scroll down
                self._scroll_down(max(1, num(1)))

            elif final == "P":                        # DCH – delete chars
                n = max(1, num(1))
                row = self._screen[self._cur_row]
                del row[self._cur_col:self._cur_col + n]
                row.extend([[" ", _Attrs()] for _ in range(n)])
                self._dirty.add(self._cur_row)

            elif final == "@":                        # ICH – insert chars
                n = max(1, num(1))
                row = self._screen[self._cur_row]
                for _ in range(n):
                    row.insert(self._cur_col, [" ", _Attrs()])
                    row.pop()
                self._dirty.add(self._cur_row)

            # All other CSI (cursor style, window ops, etc.) → ignore
            return

        # ── plain text ────────────────────────────────────────────────────────
        for ch in tok:
            if ord(ch) < 0x20:
                continue  # stray control char — skip
            if self._cur_col >= self.cols:
                # auto-wrap
                self._cur_col = 0
                if self._cur_row == self.rows - 1:
                    self._scroll_up(1)
                else:
                    self._cur_row += 1
            self._screen[self._cur_row][self._cur_col] = [ch, self._attrs.copy()]
            self._dirty.add(self._cur_row)
            self._cur_col += 1

    # ── SGR ───────────────────────────────────────────────────────────────────
    def _sgr(self, params: list[int]):
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                self._attrs = _Attrs()
            elif p == 1:  self._attrs.bold      = True
            elif p == 2:  pass                           # dim/faint — ignored (no separate dim attr)
            elif p == 3:  self._attrs.italic    = True
            elif p == 4:  self._attrs.underline = True
            elif p == 7:  self._attrs.reverse   = True
            elif p == 22: self._attrs.bold      = False  # normal intensity
            elif p == 23: self._attrs.italic    = False
            elif p == 24: self._attrs.underline = False
            elif p == 27: self._attrs.reverse   = False
            elif 30 <= p <= 37:
                self._attrs.fg = _PALETTE16[p - 30]     # standard colors (bold brightening done at render)
            elif p == 38:
                if i + 2 < len(params) and params[i+1] == 5:
                    self._attrs.fg = _xterm_color(params[i+2]); i += 2
                elif i + 4 < len(params) and params[i+1] == 2:
                    r,g,b = params[i+2],params[i+3],params[i+4]
                    self._attrs.fg = "#{:02X}{:02X}{:02X}".format(r,g,b); i += 4
            elif p == 39: self._attrs.fg = _Attrs.DEFAULT_FG
            elif 40 <= p <= 47:
                self._attrs.bg = _PALETTE16[p - 40]
            elif p == 48:
                if i + 2 < len(params) and params[i+1] == 5:
                    self._attrs.bg = _xterm_color(params[i+2]); i += 2
                elif i + 4 < len(params) and params[i+1] == 2:
                    r,g,b = params[i+2],params[i+3],params[i+4]
                    self._attrs.bg = "#{:02X}{:02X}{:02X}".format(r,g,b); i += 4
            elif p == 49: self._attrs.bg = _Attrs.DEFAULT_BG
            elif 90 <= p <= 97:  self._attrs.fg = _PALETTE16[p - 90 + 8]
            elif 100 <= p <= 107: self._attrs.bg = _PALETTE16[p - 100 + 8]
            i += 1

    # ── helpers ───────────────────────────────────────────────────────────────
    def _scroll_up(self, n: int):
        top = self._scroll_top
        bot = self._scroll_bot
        for _ in range(n):
            pushed = self._screen.pop(top)
            # Only lines scrolled off the full top (scroll_top==0) go to scrollback
            if top == 0:
                self._scrollback.append(pushed)
                self._new_scrollback.append(pushed)
            self._screen.insert(bot + 1, self._blank_line())
        for r in range(top, bot + 1):
            self._dirty.add(r)

    def _scroll_down(self, n: int):
        top = self._scroll_top
        bot = self._scroll_bot
        for _ in range(n):
            self._screen.pop(bot)
            self._screen.insert(top, self._blank_line())
        for r in range(top, bot + 1):
            self._dirty.add(r)

    def _erase_line_from(self, row: int, col: int):
        for c in range(col, self.cols):
            self._screen[row][c] = [" ", _Attrs()]
        self._dirty.add(row)

    def _erase_line_to(self, row: int, col: int):
        for c in range(0, col + 1):
            self._screen[row][c] = [" ", _Attrs()]
        self._dirty.add(row)


class _TerminalView(QPlainTextEdit):
    """
    Qt widget that owns a PTY + _VTScreen and renders the screen buffer.

    • On each timer tick: read PTY bytes → feed _VTScreen → re-render dirty lines.
    • Every keypress is forwarded as raw VT bytes to the PTY.
    • resizeEvent keeps PTY TIOCSWINSZ in sync with the widget's font metrics.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self.setUndoRedoEnabled(False)
        font = QFont()
        font.setFamily("Cascadia Code")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(12)
        self.setFont(font)
        self.setStyleSheet(
            "QPlainTextEdit { background-color: #1E1E1E; color: #D4D4D4;"
            "  border: none; padding: 4px; }"
            "QScrollBar:vertical { background:#2D2D2D; width:8px; border:none; }"
            "QScrollBar::handle:vertical { background:#555; border-radius:4px; min-height:20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
        )
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        # Hide Qt's own text cursor — we draw our own block cursor in paintEvent
        self.setCursorWidth(0)

        self._fd       = None
        self._pid      = None
        self._cwd      = HOME      # remembered so we can restart after exit
        self._stopping = False     # True when we intentionally killed the shell
        self._vt       = _VTScreen(24, 80)
        self._doc_offset = 0       # number of scrollback lines already in the document

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._sync_size_and_winch)

        # cache: rendered text per line so we skip unchanged lines
        self._rendered: list[str] = [""] * 24

    # ── PTY lifecycle ─────────────────────────────────────────────────────────
    def start(self, cwd: str = HOME):
        if self._pid is not None:
            self.stop()
        self._stopping = False
        self._cwd = cwd
        import pty, fcntl, termios, struct
        shell = os.environ.get("SHELL", "/bin/bash")
        env = os.environ.copy()
        env["TERM"]      = "xterm-256color"
        env["COLORTERM"] = "truecolor"
        # Start PTY with a sane default size so the shell doesn't start broken
        self._pid, self._fd = pty.fork()
        if self._pid == 0:
            os.chdir(cwd)
            os.execvpe(shell, [shell], env)
        else:
            fl = fcntl.fcntl(self._fd, fcntl.F_GETFL)
            fcntl.fcntl(self._fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            try:
                fcntl.ioctl(self._fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
            except Exception:
                pass
            self._timer.start()
            # After widget is painted, sync real size and send SIGWINCH
            QTimer.singleShot(50, self._sync_size_and_winch)

    def stop(self):
        import signal
        self._stopping = True
        self._timer.stop()
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGTERM)
            except Exception:
                pass
            try:
                os.waitpid(self._pid, os.WNOHANG)
            except Exception:
                pass
            self._pid = None
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

    def change_dir(self, path: str):
        if self._fd and os.path.isdir(path):
            safe = path.replace("'", "'\\''")
            self._write_raw(f"cd '{safe}'\n".encode())

    # ── size sync ─────────────────────────────────────────────────────────────
    def _sync_size(self):
        if self._fd is None:
            return
        try:
            import fcntl, termios, struct
            fm   = self.fontMetrics()
            cols = max(8, (self.viewport().width()  - 8) // max(1, fm.horizontalAdvance(' ')))
            rows = max(3, (self.viewport().height() - 8) // max(1, fm.height()))
            self._vt.resize(rows, cols)
            self._rendered = [""] * rows
            fcntl.ioctl(self._fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except Exception:
            pass

    def _sync_size_and_winch(self):
        """Sync real terminal size then send SIGWINCH so shell redraws prompt."""
        self._sync_size()
        if self._pid:
            try:
                import signal
                os.kill(self._pid, signal.SIGWINCH)
            except Exception:
                pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Debounce resizes — don't hammer TIOCSWINSZ on every pixel change
        self._resize_timer.start(80)

    # ── main render tick ──────────────────────────────────────────────────────
    def _tick(self):
        if self._fd is None:
            return
        # drain up to 64 KB per tick (fast paste / burst output)
        data = b""
        dead = False
        try:
            while True:
                chunk = os.read(self._fd, 8192)
                if not chunk:
                    dead = True
                    break
                data += chunk
                if len(data) > 65536:
                    break
        except BlockingIOError:
            pass   # nothing to read right now — normal
        except OSError:
            dead = True   # fd closed / shell exited

        if dead:
            self._reap_and_restart()
            return

        if data:
            self._vt.feed(data)
            self._render_dirty()

    def _reap_and_restart(self):
        """Shell exited (e.g. user typed 'exit'). Clean up and spawn a new one."""
        self._timer.stop()
        if self._pid:
            try:
                os.waitpid(self._pid, os.WNOHANG)
            except Exception:
                pass
            self._pid = None
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None
        if self._stopping:
            return   # intentional close — don't restart
        # Shell exited on its own (e.g. user typed 'exit') — restart it
        self._vt = _VTScreen(self._vt.rows, self._vt.cols)
        self._rendered = [""] * self._vt.rows
        self._doc_offset = 0
        self.clear()
        QTimer.singleShot(50, lambda: self.start(self._cwd))

    def _render_dirty(self):
        # Always dirty the cursor row so its line refreshes on every tick
        cr, cc = self._vt.get_cursor()
        self._vt._dirty.add(cr)

        # ── 1. Append any newly scrolled-off lines to the document ───────────
        new_sb = self._vt.flush_scrollback()
        if new_sb:
            doc = self.document()
            tail = QTextCursor(doc)
            tail.movePosition(QTextCursor.MoveOperation.End)
            tail.beginEditBlock()
            for cells in new_sb:
                # Strip trailing blanks
                last = len(cells) - 1
                while last > 0 and cells[last][0] == " " and not cells[last][1].reverse:
                    last -= 1
                cells_trimmed = cells[:last + 1]
                tail.insertText("\n")
                i = 0
                while i < len(cells_trimmed):
                    ch, attrs = cells_trimmed[i]
                    j = i + 1
                    while j < len(cells_trimmed) and cells_trimmed[j][1] == attrs:
                        j += 1
                    text = "".join(c[0] for c in cells_trimmed[i:j])
                    fmt = QTextCharFormat()
                    fg = attrs.bg if attrs.reverse else attrs.fg
                    bg = attrs.fg if attrs.reverse else attrs.bg
                    if attrs.bold and attrs.fg in _PALETTE16[:8]:
                        fg = _PALETTE16[_PALETTE16.index(attrs.fg) + 8]
                    fmt.setForeground(QColor(fg))
                    fmt.setBackground(QColor(bg))
                    if attrs.bold:      fmt.setFontWeight(QFont.Weight.Bold)
                    if attrs.italic:    fmt.setFontItalic(True)
                    if attrs.underline: fmt.setFontUnderline(True)
                    tail.insertText(text, fmt)
                    i = j
            tail.endEditBlock()
            self._doc_offset += len(new_sb)

        dirty = self._vt.get_dirty_lines()
        if not dirty and not new_sb:
            return

        doc = self.document()

        # ── 2. Ensure document has enough lines for scrollback + screen ───────
        needed = self._doc_offset + self._vt.rows
        deficit = needed - doc.blockCount() + 1
        if deficit > 0:
            tail = QTextCursor(doc)
            tail.movePosition(QTextCursor.MoveOperation.End)
            tail.insertText("\n" * deficit)

        # ── 3. Rewrite dirty screen lines at their correct doc positions ──────
        batch = QTextCursor(doc)
        batch.beginEditBlock()
        try:
            for row, cells in dirty:
                doc_line = self._doc_offset + row
                block = doc.findBlockByLineNumber(doc_line)
                if not block.isValid():
                    continue

                last = len(cells) - 1
                while last > 0 and cells[last][0] == " " and not cells[last][1].reverse:
                    last -= 1
                cells = cells[:last + 1]

                line_cur = QTextCursor(block)
                line_cur.select(QTextCursor.SelectionType.LineUnderCursor)
                line_cur.removeSelectedText()

                i = 0
                while i < len(cells):
                    ch, attrs = cells[i]
                    j = i + 1
                    while j < len(cells) and cells[j][1] == attrs:
                        j += 1
                    text = "".join(c[0] for c in cells[i:j])
                    fmt = QTextCharFormat()
                    fg = attrs.bg if attrs.reverse else attrs.fg
                    bg = attrs.fg if attrs.reverse else attrs.bg
                    if attrs.bold and attrs.fg in _PALETTE16[:8]:
                        fg = _PALETTE16[_PALETTE16.index(attrs.fg) + 8]
                    fmt.setForeground(QColor(fg))
                    fmt.setBackground(QColor(bg))
                    if attrs.bold:      fmt.setFontWeight(QFont.Weight.Bold)
                    if attrs.italic:    fmt.setFontItalic(True)
                    if attrs.underline: fmt.setFontUnderline(True)
                    line_cur.insertText(text, fmt)
                    i = j
        finally:
            batch.endEditBlock()

        # ── 4. Always scroll so the cursor line is visible at the bottom ──────
        doc_cursor_line = self._doc_offset + cr
        b = doc.findBlockByLineNumber(doc_cursor_line)
        if b.isValid():
            tc = QTextCursor(b)
            self.setTextCursor(tc)
            self.ensureCursorVisible()

        self.viewport().update()

    # ── cursor overlay ────────────────────────────────────────────────────────
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._fd is None:
            return
        cr, cc = self._vt.get_cursor()
        doc = self.document()
        block = doc.findBlockByLineNumber(self._doc_offset + cr)
        if not block.isValid():
            return
        fm = self.fontMetrics()
        char_w = fm.horizontalAdvance(' ')
        char_h = fm.height()
        tc0 = QTextCursor(block)
        rect0 = self.cursorRect(tc0)
        x = rect0.x() + cc * char_w
        y = rect0.y()
        from PyQt6.QtGui import QPainter
        painter = QPainter(self.viewport())
        if self.hasFocus():
            painter.fillRect(x, y, 2, char_h, QColor("#D4D4D4"))
        else:
            painter.setPen(QColor("#888888"))
            painter.drawRect(x, y, 1, char_h - 1)
        painter.end()

    # ── keyboard → PTY ───────────────────────────────────────────────────────
    def keyPressEvent(self, event):
        if self._fd is None:
            return
        key  = event.key()
        mods = event.modifiers()
        Ctrl = Qt.KeyboardModifier.ControlModifier
        Shift = Qt.KeyboardModifier.ShiftModifier

        # Ctrl+Shift+C = copy (don't send to PTY)
        if mods & Ctrl and mods & Shift and key == Qt.Key.Key_C:
            self.copy()
            return
        # Ctrl+Shift+V = paste
        if mods & Ctrl and mods & Shift and key == Qt.Key.Key_V:
            text = QApplication.clipboard().text()
            if text:
                self._write_raw(text.encode("utf-8", errors="replace"))
            return

        if mods & Ctrl:
            text = event.text()
            if text:
                self._write_raw(bytes([ord(text) & 0x1F]))
                return
            return

        _KEY_MAP = {
            Qt.Key.Key_Return:    b"\r",
            Qt.Key.Key_Enter:     b"\r",
            Qt.Key.Key_Backspace: b"\x7f",
            Qt.Key.Key_Delete:    b"\x1b[3~",
            Qt.Key.Key_Tab:       b"\t",
            Qt.Key.Key_Escape:    b"\x1b",
            Qt.Key.Key_Up:        b"\x1b[A",
            Qt.Key.Key_Down:      b"\x1b[B",
            Qt.Key.Key_Right:     b"\x1b[C",
            Qt.Key.Key_Left:      b"\x1b[D",
            Qt.Key.Key_Home:      b"\x1b[H",
            Qt.Key.Key_End:       b"\x1b[F",
            Qt.Key.Key_PageUp:    b"\x1b[5~",
            Qt.Key.Key_PageDown:  b"\x1b[6~",
            Qt.Key.Key_Insert:    b"\x1b[2~",
            Qt.Key.Key_F1:  b"\x1bOP", Qt.Key.Key_F2:  b"\x1bOQ",
            Qt.Key.Key_F3:  b"\x1bOR", Qt.Key.Key_F4:  b"\x1bOS",
            Qt.Key.Key_F5:  b"\x1b[15~", Qt.Key.Key_F6:  b"\x1b[17~",
            Qt.Key.Key_F7:  b"\x1b[18~", Qt.Key.Key_F8:  b"\x1b[19~",
            Qt.Key.Key_F9:  b"\x1b[20~", Qt.Key.Key_F10: b"\x1b[21~",
            Qt.Key.Key_F11: b"\x1b[23~", Qt.Key.Key_F12: b"\x1b[24~",
        }
        if key in _KEY_MAP:
            self._write_raw(_KEY_MAP[key])
            return

        text = event.text()
        if text:
            self._write_raw(text.encode("utf-8", errors="replace"))
            return

        event.ignore()

    def _natural_height(self, rows: int = 3) -> int:
        """Pixel height needed to display `rows` lines + padding."""
        return self.fontMetrics().height() * rows + 12

    def minimumSizeHint(self):
        return QSize(0, self._natural_height(3))

    def sizeHint(self):
        return QSize(0, self._natural_height(3))

    def _write_raw(self, data: bytes):
        if self._fd is not None:
            try:
                os.write(self._fd, data)
            except OSError:
                pass

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Copy",  self.copy)
        paste_act = menu.addAction("Paste", lambda: self._write_raw(
            QApplication.clipboard().text().encode("utf-8", errors="replace")))
        menu.addSeparator()
        menu.addAction("Clear", self._do_clear)
        menu.exec(event.globalPos())

    def _do_clear(self):
        self._vt = _VTScreen(self._vt.rows, self._vt.cols)
        self._rendered = [""] * self._vt.rows
        self._doc_offset = 0
        self.clear()
        self._write_raw(b"\x0c")


class _TerminalPanel(QWidget):
    """Header bar + _TerminalView. Public API unchanged."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._setup_ui()
        self._view.start(HOME)   # start shell immediately in background

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = QWidget()
        header.setObjectName("termHeader")
        header.setFixedHeight(34)
        header.setToolTip("Double-click to expand / restore")
        header.mouseDoubleClickEvent = lambda e: self._toggle_expand()
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(12, 0, 7, 0)
        hlay.setSpacing(7)
        lbl = QLabel("TERMINAL")
        lbl.setStyleSheet("font-size:11px; font-weight:600; color:#5C5C5C; background:transparent;")
        hlay.addWidget(lbl)
        hint = QLabel("double click to expand / collapse")
        hint.setStyleSheet("font-size:11px; font-weight:400; color:#5C5C5C; background:transparent;")
        hlay.addWidget(hint)
        hlay.addStretch()

        clear_btn = QToolButton()
        clear_btn.setText("⊘")
        clear_btn.setToolTip("Clear (Ctrl+L)")
        clear_btn.setFixedSize(22, 22)
        clear_btn.setAutoRaise(True)
        clear_btn.setStyleSheet("font-size:12px; color:#5C5C5C;")
        clear_btn.clicked.connect(lambda: self._view._do_clear())
        hlay.addWidget(clear_btn)

        close_btn = QToolButton()
        close_btn.setText("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setAutoRaise(True)
        close_btn.setStyleSheet("font-size:11px; color:#5C5C5C;")
        close_btn.clicked.connect(self.hide_panel)
        hlay.addWidget(close_btn)

        lay.addWidget(header)
        self._view = _TerminalView()
        lay.addWidget(self._view)
        # Panel can't be squeezed below 3 visible lines + header
        self.setMinimumHeight(28 + self._view._natural_height(3))

    def _get_splitter(self):
        w = self.parent()
        while w and not isinstance(w, QSplitter):
            w = w.parent()
        return w if isinstance(w, QSplitter) else None

    def _toggle_expand(self):
        splitter = self._get_splitter()
        if splitter is None:
            return
        idx   = splitter.indexOf(self)
        total = sum(splitter.sizes())
        other = [i for i in range(splitter.count()) if i != idx]
        if not self._expanded:
            # Save current sizes so we can restore them
            self._saved_sizes = list(splitter.sizes())
            sizes = [0] * splitter.count()
            sizes[idx] = total
            for i in other:
                sizes[i] = 0
            splitter.setSizes(sizes)
            self._expanded = True
        else:
            splitter.setSizes(self._saved_sizes)
            self._expanded = False
        self._view.setFocus()

    def show_panel(self):
        self.show()
        # Size the terminal to exactly 3 lines + header on open.
        # Walk up to find the QSplitter that contains us and adjust sizes.
        splitter = self.parent()
        while splitter and not isinstance(splitter, QSplitter):
            splitter = splitter.parent()
        if splitter and isinstance(splitter, QSplitter):
            term_h = 28 + self._view._natural_height(3)   # header + 3 rows
            total  = sum(splitter.sizes())
            idx    = splitter.indexOf(self)
            sizes  = list(splitter.sizes())
            sizes[idx] = term_h
            # give remaining space to the other pane
            other = [i for i in range(len(sizes)) if i != idx]
            if other:
                sizes[other[0]] = max(0, total - term_h)
            splitter.setSizes(sizes)
        self._view.setFocus()

    def hide_panel(self):
        self._expanded = False
        self.hide()

    def change_dir(self, path: str):
        self._view.change_dir(path)

    def closeEvent(self, event):
        self._view.stop()   # kill shell only when the whole app closes
        super().closeEvent(event)


class FileExplorer(QMainWindow):

    def __init__(self, start_path=HOME):
        super().__init__()
        self.setWindowTitle("File Explorer")
        self.setMinimumSize(1440, 720)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._maximized = False
        self._drag_pos = None

        self._recent    = RecentFiles()
        self._favorites = Favorites()
        self._all_apps  = _parse_desktop_files()

        self._build_toolbar()
        self._build_tabs()
        self._setup_shortcuts()

        self._shared_clipboard_mode:  str | None = None
        self._shared_clipboard_paths: list[str]  = []

        # open first tab
        self.new_tab(start_path)

    # ── toolbar ───────────────────────────────────────────────────────────────
    # ── nav icon painter ──────────────────────────────────────────────────────
    @staticmethod
    def _make_nav_icon(kind: str, size: int = 28,
                       normal_color: "QColor | None" = None,
                       disabled_color: "QColor | None" = None) -> QIcon:
        """
        Paint a Fluent-style navigation icon onto a QPixmap.
        kind: 'back' | 'forward' | 'up'
        Stroke: 1.6 px, round caps/joins, colour tokens from WIN11_LIGHT_QSS.
        """
        def _render(color: QColor) -> QPixmap:
            from PyQt6.QtCore import QPointF
            from PyQt6.QtGui import QPolygonF
            px = QPixmap(size, size)
            px.fill(Qt.GlobalColor.transparent)
            p = QPainter(px)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))

            c  = size / 2          # centre
            hw = size * 0.18       # arrowhead half-width (narrower)
            hh = size * 0.30       # arrowhead height (longer)
            sw = size * 0.055      # shaft half-thickness (thinner)
            sl = size * 0.26       # shaft length (longer)

            if kind == "back":
                # ← head points left
                poly = QPolygonF([
                    QPointF(c - hh,      c),
                    QPointF(c,           c - hw),
                    QPointF(c,           c - sw),
                    QPointF(c + sl,      c - sw),
                    QPointF(c + sl,      c + sw),
                    QPointF(c,           c + sw),
                    QPointF(c,           c + hw),
                ])
            elif kind == "forward":
                # → head points right
                poly = QPolygonF([
                    QPointF(c + hh,      c),
                    QPointF(c,           c - hw),
                    QPointF(c,           c - sw),
                    QPointF(c - sl,      c - sw),
                    QPointF(c - sl,      c + sw),
                    QPointF(c,           c + sw),
                    QPointF(c,           c + hw),
                ])
            else:  # "up"
                # ↑ head points up
                poly = QPolygonF([
                    QPointF(c,           c - hh),
                    QPointF(c - hw,      c),
                    QPointF(c - sw,      c),
                    QPointF(c - sw,      c + sl),
                    QPointF(c + sw,      c + sl),
                    QPointF(c + sw,      c),
                    QPointF(c + hw,      c),
                ])

            p.drawPolygon(poly)
            p.end()
            return px

        normal   = _render(normal_color   or QColor("#1A1A1A"))
        disabled = _render(disabled_color or QColor("#9E9E9E"))

        icon = QIcon()
        icon.addPixmap(normal,   QIcon.Mode.Normal,   QIcon.State.Off)
        icon.addPixmap(disabled, QIcon.Mode.Disabled, QIcon.State.Off)
        return icon

    def _build_toolbar(self):
        # Build the nav bar as a plain QWidget (not a QToolBar) so we can
        # place it below the tab bar in the central-widget stack.
        tb_widget = QWidget()
        tb_widget.setObjectName("navBar")
        tb_layout = QHBoxLayout(tb_widget)
        tb_layout.setContentsMargins(5, 4, 5, 4)
        tb_layout.setSpacing(2)
        tb_widget.setFixedHeight(48)

        # We still need a hidden QToolBar so QMainWindow doesn't complain;
        # keep it empty and invisible.
        _dummy = QToolBar(); _dummy.setMovable(False); _dummy.setVisible(False)
        self.addToolBar(_dummy)

        self._nav_widget = tb_widget   # stored so _build_tabs can use it

        def _add_action_button(action):
            """Wrap a QAction in a QToolButton and add to tb_layout."""
            from PyQt6.QtWidgets import QToolButton
            btn = QToolButton()
            btn.setDefaultAction(action)
            btn.setAutoRaise(True)
            tb_layout.addWidget(btn)
            return btn

        self.back_action    = QAction(self._make_nav_icon("back"),    "", self)
        self.back_action.setEnabled(False)
        self.forward_action = QAction(self._make_nav_icon("forward"), "", self)
        self.forward_action.setEnabled(False)
        self.up_action      = QAction(self._make_nav_icon("up"),      "", self)

        self._active_address_bar: BreadcrumbBar | None = None

        for act in (self.back_action, self.forward_action, self.up_action):
            _nav_b = _add_action_button(act)
            _nav_b.setIconSize(QSize(28, 28))

        # ── Favourite star (icon-only, lives in nav bar) ──────────────────────
        from PyQt6.QtWidgets import QToolButton
        self._btn_pin = QToolButton()
        self._btn_pin.setIcon(_cmd_icon("pin_remove"))
        self._btn_pin.setIconSize(QSize(24, 24))
        self._btn_pin.setToolTip("Add to favorites")
        self._btn_pin.setAutoRaise(True)
        self._btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_pin.setFixedSize(32, 32)
        self._btn_pin.clicked.connect(lambda: self._active()._toggle_favorite())
        tb_layout.addWidget(self._btn_pin)

        # address bar container
        self._tb_addr_container = QWidget()
        self._tb_addr_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        clay = QHBoxLayout(self._tb_addr_container)
        clay.setContentsMargins(5, 2, 5, 2)
        self._tb_addr_layout = clay
        tb_layout.addWidget(self._tb_addr_container)

        # search bar
        self._search_bar = SearchBar()
        self._search_bar.search_changed.connect(self._on_search_changed)
        self._search_bar.search_cleared.connect(self._on_search_cleared)
        tb_layout.addWidget(self._search_bar)

        self.back_action.triggered.connect(lambda: self._active().go_back())
        self.forward_action.triggered.connect(lambda: self._active().go_forward())
        self.up_action.triggered.connect(lambda: self._active().go_up())

        # ── dark / light toggle ───────────────────────────────────────────────
        self._dark_mode = self._load_theme()
        app = QApplication.instance()
        if self._dark_mode:
            _apply_win11_dark_palette(app)
            app.setStyleSheet(WIN11_DARK_QSS)
        from PyQt6.QtWidgets import QToolButton
        self._theme_btn = QToolButton()
        self._theme_btn.setText("☀️" if self._dark_mode else "🌙")
        self._theme_btn.setToolTip("Switch to Light Mode" if self._dark_mode else "Switch to Dark Mode")
        self._theme_btn.setAutoRaise(True)
        self._theme_btn.clicked.connect(self._toggle_theme)
        tb_layout.addWidget(self._theme_btn)

        # Store theme action alias so _toggle_theme still works
        self._theme_action = self._theme_btn

    # ── theme toggle ──────────────────────────────────────────────────────────
    @staticmethod
    def _load_theme() -> bool:
        try:
            with open(THEME_JSON, "r", encoding="utf-8") as f:
                return json.load(f).get("dark", False)
        except Exception:
            return False

    def _save_theme(self):
        try:
            with open(THEME_JSON, "w", encoding="utf-8") as f:
                json.dump({"dark": self._dark_mode}, f)
        except Exception:
            pass

    def _toggle_theme(self):
        app = QApplication.instance()
        self._dark_mode = not self._dark_mode
        self._save_theme()
        if self._dark_mode:
            _apply_win11_dark_palette(app)
            app.setStyleSheet(WIN11_DARK_QSS)
            self._theme_btn.setText("☀️")
            self._theme_btn.setToolTip("Switch to Light Mode")
        else:
            _apply_win11_palette(app)
            app.setStyleSheet(WIN11_LIGHT_QSS)
            self._theme_btn.setText("🌙")
            self._theme_btn.setToolTip("Switch to Dark Mode")
        # Repaint all programmatic icons to match new palette
        self._refresh_painted_icons()

    def _refresh_painted_icons(self):
        """Re-render all palette-dependent painted icons after a theme switch."""
        app = QApplication.instance()
        pal = app.palette()
        norm  = pal.color(QPalette.ColorRole.WindowText)
        dis   = pal.color(QPalette.ColorRole.PlaceholderText)
        self.back_action.setIcon(self._make_nav_icon("back",    normal_color=norm, disabled_color=dis))
        self.forward_action.setIcon(self._make_nav_icon("forward", normal_color=norm, disabled_color=dis))
        self.up_action.setIcon(self._make_nav_icon("up",        normal_color=norm, disabled_color=dis))
        # Refresh command bar icons in all open tabs
        for i in range(self._tabs.count()):
            pane = self._tabs.widget(i)
            if hasattr(pane, "_refresh_cmd_icons"):
                pane._refresh_cmd_icons()
        # Repaint visible tab bar
        self._visible_tab_bar.update()
        # Refresh sidebar icons in all open tabs
        for i in range(self._tabs.count()):
            pane = self._tabs.widget(i)
            if hasattr(pane, "sidebar"):
                pane.sidebar.refresh_icons()
        # Repaint window control buttons
        for b in (self._btn_min, self._btn_max, self._btn_close):
            b.update()

    # ── tab widget ────────────────────────────────────────────────────────────
    def _build_tabs(self):
        self._tabs = QTabWidget()
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)

        # Replace the default tab bar with one that has an inline "+" button
        self._tab_bar = _PlusTabBar(self._tabs)
        self._tab_bar.new_tab_requested.connect(
            lambda: self.new_tab(HOME))
        self._tabs.setTabBar(self._tab_bar)

        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # middle-click to close
        self._tab_bar.setMouseTracking(True)
        self._tab_bar.installEventFilter(self)

        # ── Layout: [tab strip] → [nav bar] → [tab content area] ─────────────
        # We want:  row 0 = tab bar strip
        #           row 1 = nav bar (arrows + address + search)
        #           row 2 = tab pane content
        #
        # QTabWidget fuses the tab bar and pane; we can't split them natively.
        # Trick: hide the QTabWidget's own tab bar (setTabBar with a zero-height
        # invisible bar), drive tab switching via a standalone _PlusTabBar placed
        # above the nav_widget, and let the QTabWidget show only its pane area.

        # 1. Create a standalone visible tab bar that the user sees
        self._visible_tab_bar = _PlusTabBar()
        self._visible_tab_bar.setMovable(False)
        self._visible_tab_bar.new_tab_requested.connect(
            lambda: self.new_tab(HOME))
        self._visible_tab_bar.setMouseTracking(True)
        self._visible_tab_bar.installEventFilter(self)

        # 2. Install an invisible zero-height tab bar on the QTabWidget
        #    so its own tab strip disappears
        from PyQt6.QtWidgets import QTabBar as _QTabBar
        class _HiddenTabBar(_QTabBar):
            def sizeHint(self): return QSize(0, 0)
            def minimumSizeHint(self): return QSize(0, 0)
            def tabSizeHint(self, i): return QSize(0, 0)
        self._tabs.setTabBar(_HiddenTabBar(self._tabs))
        self._tabs.tabBar().hide()

        # 3. Sync visible_tab_bar ↔ QTabWidget
        self._visible_tab_bar.currentChanged.connect(self._tabs.setCurrentIndex)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        # Close/move on visible bar
        self._visible_tab_bar.tabCloseRequested.connect(self._close_tab)
        self._visible_tab_bar.tabMoved.connect(self._on_tab_moved)

        # 4. Build container: [title+tabs row] / [nav bar] / [tab pane]
        container = QWidget()
        vlay = QVBoxLayout(container)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # ── Title bar row: drag-area | tab bar | window controls ─────────────
        title_row = QWidget()
        title_row.setObjectName("titleBar")
        title_row.setFixedHeight(43)
        tlay = QHBoxLayout(title_row)
        tlay.setContentsMargins(0, 0, 0, 0)
        tlay.setSpacing(0)

        # tab bar expands in the middle
        tlay.addWidget(self._visible_tab_bar, 1)

        # window control buttons (painted icons — no font dependency)
        self._btn_min   = _WinCtrlButton("min",   "winMin",   "Minimize")
        self._btn_max   = _WinCtrlButton("max",   "winMax",   "Maximize")
        self._btn_close = _WinCtrlButton("close", "winClose", "Close")
        self._btn_min.clicked.connect(self.showMinimized)
        self._btn_max.clicked.connect(self._toggle_maximize)
        self._btn_close.clicked.connect(self.close)
        for b in (self._btn_min, self._btn_max, self._btn_close):
            tlay.addWidget(b)

        title_row.mouseDoubleClickEvent = lambda e: self._toggle_maximize()

        vlay.addWidget(title_row)
        vlay.addWidget(self._nav_widget)

        # ── vertical splitter: file tabs on top, terminal on bottom ───────────
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.setHandleWidth(2)
        self._splitter.addWidget(self._tabs)

        self._terminal = _TerminalPanel()
        self._terminal.hide()
        self._splitter.addWidget(self._terminal)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)

        vlay.addWidget(self._splitter)

        self.setCentralWidget(container)

    def _on_tab_moved(self, from_idx: int, to_idx: int):
        """Keep QTabWidget in sync when tabs are dragged on the visible bar."""
        # QTabWidget has no public moveTab; use the hidden bar's move
        self._tabs.tabBar().moveTab(from_idx, to_idx)

    # ── shortcuts ─────────────────────────────────────────────────────────────
    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(
            lambda: self.new_tab(HOME))
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(
            lambda: self._close_tab(self._visible_tab_bar.currentIndex()))
        QShortcut(QKeySequence("Alt+Left"), self).activated.connect(
            lambda: self._active().go_back())
        QShortcut(QKeySequence("Alt+Up"), self).activated.connect(
            lambda: self._active().navigate_to(HOME))
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(
            lambda: self._active()._do_refresh())
        QShortcut(QKeySequence("Ctrl+Shift+V"), self).activated.connect(
            lambda: self._active()._toggle_view_mode())
        QShortcut(QKeySequence("Ctrl+`"), self).activated.connect(
            self._toggle_terminal)
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(
            self._next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(
            self._prev_tab)

    # ── tab management ────────────────────────────────────────────────────────
    def new_tab(self, path: str = HOME):
        pane = TabPane(self._recent, self._all_apps, self._favorites, self)
        # hide the address bar inside the pane — it lives in the nav bar
        pane.address_bar.hide()
        pane.title_changed.connect(
            lambda title, p=pane: self._on_pane_title_changed(p, title))
        pane.nav_state_changed.connect(self._refresh_nav_buttons)
        pane.open_in_new_tab.connect(self.new_tab)

        idx = self._tabs.addTab(pane, "…")
        self._visible_tab_bar.addTab("…")
        self._visible_tab_bar.setCurrentIndex(idx)
        self._tabs.setCurrentIndex(idx)
        pane.navigate_to(path if os.path.isdir(path) else HOME)

    def _close_tab(self, index: int):
        if self._tabs.count() <= 1:
            return          # never close the last tab
        pane = self._tabs.widget(index)
        self._tabs.removeTab(index)
        self._visible_tab_bar.removeTab(index)
        pane.cleanup_threads()
        pane.deleteLater()

    def _on_tab_changed(self, index: int):
        pane = self._tabs.widget(index)
        if pane is None:
            return
        # swap address bar into toolbar
        self._swap_address_bar(pane)
        self._refresh_nav_buttons()
        # sync search bar: clear it and reset the new tab's filter
        self._search_bar.clear()

    def _on_search_changed(self, text: str):
        pane = self._active()
        if pane:
            pane.set_search_filter(text)

    def _on_search_cleared(self):
        pane = self._active()
        if pane:
            pane.clear_search()

    def _swap_address_bar(self, pane: "TabPane"):
        # remove any existing bar from the container
        while self._tb_addr_layout.count():
            item = self._tb_addr_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)   # type: ignore
                item.widget().hide()
        bar = pane.address_bar
        bar.setParent(self._tb_addr_container)
        bar.show()
        self._tb_addr_layout.addWidget(bar)
        self._active_address_bar = bar

    def _on_pane_title_changed(self, pane: "TabPane", title: str):
        idx = self._tabs.indexOf(pane)
        if idx >= 0:
            short = title if len(title) <= 20 else title[:18] + "…"
            self._tabs.setTabText(idx, short)
            self._tabs.setTabToolTip(idx, title)
            self._visible_tab_bar.setTabText(idx, short)
            self._visible_tab_bar.setTabToolTip(idx, title)

    def _refresh_nav_buttons(self):
        pane = self._active()
        if pane:
            self.back_action.setEnabled(pane.can_go_back())
            self.forward_action.setEnabled(pane.can_go_forward())

    def _active(self) -> "TabPane":
        return self._tabs.currentWidget()

    def _next_tab(self):
        n = self._tabs.count()
        if n < 2:
            return
        idx = (self._tabs.currentIndex() + 1) % n
        self._tabs.setCurrentIndex(idx)
        self._visible_tab_bar.setCurrentIndex(idx)

    def _prev_tab(self):
        n = self._tabs.count()
        if n < 2:
            return
        idx = (self._tabs.currentIndex() - 1) % n
        self._tabs.setCurrentIndex(idx)
        self._visible_tab_bar.setCurrentIndex(idx)

    # ── window drag & maximize ───────────────────────────────────────────────
    def _toggle_terminal(self):
        if self._terminal.isVisible():
            self._terminal.hide_panel()
        else:
            self._terminal.show_panel()

    def _toggle_maximize(self):
        if self._maximized:
            self.showNormal()
            self._btn_max.setText("□")
        else:
            self.showMaximized()
            self._btn_max.setText("❐")
        self._maximized = not self._maximized


    # ── middle-click close ────────────────────────────────────────────────────
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self._visible_tab_bar:
            if event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.MiddleButton:
                    idx = self._visible_tab_bar.tabAt(event.pos())
                    if idx >= 0:
                        self._close_tab(idx)
                        return True

            # ── drag to move window ──────────────────────────────────────────
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    # Only drag on empty tab bar area (not on a tab)
                    if self._visible_tab_bar.tabAt(event.pos()) == -1:
                        self._drag_pos = event.globalPosition().toPoint()

            if event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_pos = None

            if event.type() == QEvent.Type.MouseMove:
                if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
                    if self._maximized:
                        self.showNormal()
                        self._btn_max.setText("□")
                        self._maximized = False
                        self._drag_pos = event.globalPosition().toPoint() - QPoint(self.width() // 2, 10)
                        self.move(self._drag_pos)
                        self._drag_pos = event.globalPosition().toPoint()
                    else:
                        delta = event.globalPosition().toPoint() - self._drag_pos
                        self.move(self.pos() + delta)
                        self._drag_pos = event.globalPosition().toPoint()
                    return True

        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """Drain all background threads in every pane before the app exits."""
        for i in range(self._tabs.count()):
            pane = self._tabs.widget(i)
            if pane is not None:
                pane.cleanup_threads()
        super().closeEvent(event)


# ═══════════════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _apply_win11_palette(app)
    app.setStyleSheet(WIN11_LIGHT_QSS)
    # Open the path passed as argument, fallback to HOME
    start_path = sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else HOME
    w = FileExplorer(start_path=start_path)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
