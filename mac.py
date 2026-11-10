#!/usr/bin/env python3
"""
Clipboard Manager — Mac version
Requires: pip3 install customtkinter pyperclip
"""

import json
import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

try:
    import pyperclip
except ImportError:
    pyperclip = None

import subprocess

# _copy_text is set up after the root window exists — see ClipboardManager.__init__
# We use tkinter's clipboard which handles all Unicode (curly quotes, emojis, etc.)
_tk_root = None

def _copy_text(text):
    """Copy text using tkinter's clipboard — handles all Unicode correctly on Mac."""
    if _tk_root is not None:
        try:
            _tk_root.clipboard_clear()
            _tk_root.clipboard_append(text)
            _tk_root.update()  # keeps clipboard alive after window closes
            return
        except Exception:
            pass
    # Fallback: pbcopy with UTF-8
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True,
                       env={**__import__("os").environ, "LANG": "en_US.UTF-8"})
    except Exception:
        if pyperclip:
            pyperclip.copy(text)

# ── Data location: ~/Library/Application Support/ClipboardManager ──────────────
_APP_SUPPORT = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "ClipboardManager")
os.makedirs(_APP_SUPPORT, exist_ok=True)
DATA_FILE = os.path.join(_APP_SUPPORT, "clipboard_items.json")
CATS_FILE = os.path.join(_APP_SUPPORT, "clipboard_categories.json")

# ── Bundled default data (copied to user dir on first launch) ───────────────────
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _BUNDLE_DIR = sys._MEIPASS
else:
    _BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

def _seed_default_data():
    """
    On first launch (or if data files are empty), copy bundled JSON files
    into Application Support so the user starts with pre-loaded snippets.
    """
    import shutil
    for filename, dest in [("clipboard_items.json", DATA_FILE),
                            ("clipboard_categories.json", CATS_FILE)]:
        src = os.path.join(_BUNDLE_DIR, filename)
        if not os.path.exists(src):
            continue
        should_copy = False
        if not os.path.exists(dest):
            should_copy = True
        else:
            try:
                with open(dest, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if not content or content in ("[]", "{}"):
                    should_copy = True
            except Exception:
                should_copy = True
        if should_copy:
            shutil.copy(src, dest)

_seed_default_data()

# ── Palettes ───────────────────────────────────────────────────────────────────
LIGHT_THEME = dict(
    BG         = "#F5F4F0",
    PANEL      = "#FFFFFF",
    PANEL2     = "#EEECEA",
    BORDER     = "#DEDAD6",
    ACCENT     = "#5B6AF0",
    ACCENT_HOV = "#4554D4",
    DANGER     = "#E05252",
    TEXT       = "#1A1A2E",
    TEXT_MED   = "#6B6B80",
    TEXT_LIGHT = "#A0A0B8",
    SELECT_BG  = "#EEF0FE",
    DRAG_BG    = "#DDE0FC",
    SUCCESS    = "#34A853",
    WARN       = "#F59E0B",
    DELETE_HOV = "#FFF0F0",
)

DARK_THEME = dict(
    BG         = "#1C1C28",
    PANEL      = "#252535",
    PANEL2     = "#2E2E42",
    BORDER     = "#3A3A52",
    ACCENT     = "#7B8BFF",
    ACCENT_HOV = "#6070EE",
    DANGER     = "#FF6B6B",
    TEXT       = "#E8E8F0",
    TEXT_MED   = "#9090B0",
    TEXT_LIGHT = "#5A5A78",
    SELECT_BG  = "#2D2F55",
    DRAG_BG    = "#383A62",
    SUCCESS    = "#4ADE80",
    WARN       = "#FBBF24",
    DELETE_HOV = "#3D2020",
)

_current_theme = LIGHT_THEME.copy()

def _t(key):
    """Look up a colour from the active theme."""
    return _current_theme[key]

# Convenience globals (used by code that references them directly)
def _sync_globals():
    g = globals()
    for k, v in _current_theme.items():
        g[k] = v

_sync_globals()

# Aliases so existing code still works unchanged
BG         = _current_theme["BG"]
PANEL      = _current_theme["PANEL"]
PANEL2     = _current_theme["PANEL2"]
BORDER     = _current_theme["BORDER"]
ACCENT     = _current_theme["ACCENT"]
ACCENT_HOV = _current_theme["ACCENT_HOV"]
DANGER     = _current_theme["DANGER"]
TEXT       = _current_theme["TEXT"]
TEXT_MED   = _current_theme["TEXT_MED"]
TEXT_LIGHT = _current_theme["TEXT_LIGHT"]
SELECT_BG  = _current_theme["SELECT_BG"]
DRAG_BG    = _current_theme["DRAG_BG"]
SUCCESS    = _current_theme["SUCCESS"]
WARN       = _current_theme["WARN"]

FONT_UI    = ("Segoe UI", 10)
FONT_LABEL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI Semibold", 13)
FONT_MONO  = ("Consolas", 10)
FONT_SMALL = ("Segoe UI", 8)


# ── Persistence ────────────────────────────────────────────────────────────────

def _strip_control_chars(text):
    """Remove invalid control characters that break JSON parsing."""
    return "".join(ch for ch in text if ord(ch) >= 32 or ch in ('\n', '\r', '\t'))

def load_items():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = _strip_control_chars(f.read())
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return []
    return []


def save_items(items):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


# ── Categories persistence ──────────────────────────────────────────────────────
# Format: {"Category Name": ["snippet_id1", "snippet_id2", ...], ...}

def load_categories():
    if os.path.exists(CATS_FILE):
        with open(CATS_FILE, "r", encoding="utf-8") as f:
            content = _strip_control_chars(f.read())
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}
    return {}


def save_categories(cats):
    with open(CATS_FILE, "w", encoding="utf-8") as f:
        json.dump(cats, f, indent=2, ensure_ascii=False)


def _ensure_ids(items):
    """Back-fill unique IDs onto snippets that were saved before this version."""
    import uuid
    changed = False
    for item in items:
        if "id" not in item:
            item["id"] = str(uuid.uuid4())
            changed = True
    return changed


def _cleanup_categories(categories, items):
    """Remove null entries and IDs that no longer exist in items. Returns True if changed."""
    valid_ids = {item["id"] for item in items if "id" in item}
    changed = False
    for name in categories:
        before = categories[name]
        after = [sid for sid in before if sid is not None and sid in valid_ids]
        if after != before:
            categories[name] = after
            changed = True
    return changed

# ── Modern UI (CustomTkinter) ──────────────────────────────────────────────────
import re
import tkinter.font as tkfont
import customtkinter as ctk


def _patch_ctk_scrollbar_redraw():
    """CTkScrollbar._draw ends with canvas.update_idletasks(), which forces Tk to
    re-lay-out the whole window synchronously. During a window drag every
    scrollbar redraw (several per frame) re-runs layout for every snippet row,
    making live resizing crawl. Tk repaints at idle anyway, so skip the flush."""
    try:
        from customtkinter.windows.widgets.ctk_scrollbar import CTkScrollbar
    except Exception:
        return
    orig_draw = CTkScrollbar._draw
    if getattr(orig_draw, "_no_idle_flush", False):
        return

    def _draw(self, no_color_updates=False):
        canvas = getattr(self, "_canvas", None)
        if canvas is None:
            return orig_draw(self, no_color_updates)
        canvas.update_idletasks = lambda: None   # instance attr shadows method
        try:
            return orig_draw(self, no_color_updates)
        finally:
            del canvas.update_idletasks

    _draw._no_idle_flush = True
    CTkScrollbar._draw = _draw


_patch_ctk_scrollbar_redraw()

# Palette — every colour is a (light, dark) pair that auto-switches with the
# active appearance mode, so the theme toggle is essentially free.
COL_BG          = ("#F5F6F8", "#0E1014")   # main canvas
COL_SIDEBAR     = ("#ECEEF2", "#13161B")
COL_PANEL       = ("#FFFFFF", "#171A20")   # cards
COL_FIELD       = ("#F0F2F5", "#1E222A")   # inputs / wells inside cards
COL_HOVER       = ("#F1F3F6", "#1E222A")   # row hover on a card
COL_SIDE_HOVER  = ("#E1E4EA", "#1C2027")   # row hover on the sidebar
COL_BORDER      = ("#E2E5EA", "#252A33")
COL_SEG_SEL     = ("#FFFFFF", "#2E343F")
COL_ACCENT      = ("#4A57E8", "#5662E8")   # filled buttons (white text)
COL_ACCENT_HOV  = ("#3B47D1", "#4753D6")
COL_ACCENT_TEXT = ("#3D4AD6", "#A9B0FF")   # accent used as text
COL_TEXT        = ("#15171C", "#ECEEF2")
COL_MUTED       = ("#5B6270", "#9EA5B2")
COL_FAINT       = ("#767C88", "#737A87")   # placeholders / disabled only
COL_SEL         = ("#E8EAFD", "#232849")
COL_DRAG        = ("#D3D8FC", "#2F3670")
COL_DANGER      = ("#C42F40", "#FF7A85")   # danger used as text
COL_DANGER_FILL = ("#CF3445", "#C93342")   # filled danger buttons (white text)
COL_DANGER_HOV  = ("#B42A3A", "#B22C3A")
COL_DANGER_SOFT = ("#FCECEE", "#2E1A1E")
COL_SUCCESS     = ("#17784A", "#5BE08F")
COL_SUCCESS_SOFT= ("#E3F4EA", "#13281B")
COL_NOTICE      = ("#8A4B00", "#F6C350")
COL_NOTICE_SOFT = ("#FFF3DE", "#2E2410")

DENSITY_NAMES = ("Compact", "Cozy", "Roomy")
_ACCEL = "Cmd+Shift+{}" if sys.platform == "darwin" else "Ctrl+Shift+{}"

# Glyphs from Segoe Fluent Icons / MDL2 Assets (Windows); plain-text fallback elsewhere.
_ICON_GLYPHS = {
    "search": ("", ""),
    "clear":  ("", "✕"),
    "add":    ("", "+"),
    "up":     ("", "↑"),
    "down":   ("", "↓"),
    "copy":   ("", ""),
    "chev_up":   ("", "▴"),
    "chev_down": ("", "▾"),
}


def _resolve_fonts(root):
    """Pick the best available UI / display / mono / icon families."""
    try:
        fams = set(tkfont.families(root))
    except Exception:
        fams = set()

    def first(*names):
        for n in names:
            if n in fams:
                return n
        return names[-1]

    if sys.platform == "darwin":
        ui = first(".AppleSystemUIFont", "SF Pro Text", "Helvetica Neue")
        return ui, ui, first("SF Mono", "Menlo"), None
    if sys.platform == "win32":
        ui = first("Segoe UI Variable Text", "Segoe UI")
        disp = first("Segoe UI Variable Display", ui)
        mono = first("Cascadia Mono", "Consolas")
        icons = next((n for n in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if n in fams), None)
        return ui, disp, mono, icons
    ui = first("Inter", "Cantarell", "DejaVu Sans")
    return ui, ui, first("DejaVu Sans Mono", "Monospace"), None


def _asset_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


# ── Display helpers (list titles only — copied text is never altered) ──────────

_RE_CUSTOM_EMOJI = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
_RE_LINK = re.compile(r"\[([^\]]+)\]\(<?[^)>]+>?\)")
_RE_SHORTCODE = re.compile(r":[A-Za-z_]{2,}:")
_RE_HEADING = re.compile(r"^\s*#+\s*", re.M)


def _clean_for_display(text):
    t = _RE_CUSTOM_EMOJI.sub("", text)
    t = _RE_LINK.sub(r"\1", t)
    t = _RE_SHORTCODE.sub("", t)
    t = _RE_HEADING.sub("", t)
    t = t.replace("**", "").replace("__", "").replace("`", "")
    return t


def _snippet_title_sub(item):
    """(title, subtitle) for a list row."""
    cleaned = _clean_for_display(item.get("text", ""))
    lines = [" ".join(ln.split()) for ln in cleaned.splitlines()]
    lines = [ln for ln in lines if ln]
    if item.get("label"):
        return item["label"], " ".join(lines)
    if not lines:
        return "(empty snippet)", ""
    return lines[0], " ".join(lines[1:])


def _settings_get_mode():
    return "dark" if load_settings().get("theme") == "dark" else "light"


def _mode_is_dark():
    return ctk.get_appearance_mode() == "Dark"


def _c(pair):
    """Resolve a (light, dark) colour pair to the active mode — for tk.Menu."""
    if isinstance(pair, tuple):
        return pair[1] if _mode_is_dark() else pair[0]
    return pair


# ── User settings (persisted) ───────────────────────────────────────────────────

SETTINGS_FILE = os.path.join(os.path.dirname(CATS_FILE), "clipboard_settings.json")


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _copy_to_clipboard(text, root):
    """Copy text to the system clipboard, using the best method per platform."""
    if "_copy_text" in globals():          # mac build provides this
        try:
            globals()["_copy_text"](text)
            return True
        except Exception:
            pass
    if pyperclip:
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            pass
    try:                                    # universal tk fallback
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        return True
    except Exception:
        return False


class _EntryVar:
    """StringVar-like wrapper for a CTkEntry that keeps its placeholder working."""

    def __init__(self, entry, on_change):
        self._e = entry
        self._on_change = on_change
        self._last = ""
        entry.bind("<KeyRelease>", lambda e: self._check())
        entry.bind("<<Paste>>", lambda e: entry.after(1, self._check))
        entry.bind("<<Cut>>", lambda e: entry.after(1, self._check))

    def get(self):
        return self._e.get()

    def set(self, value):
        self._e.delete(0, "end")
        if value:
            self._e.insert(0, value)
        self._check()

    def _check(self):
        v = self.get()
        if v != self._last:
            self._last = v
            self._on_change()


# ── Shared dialog base ──────────────────────────────────────────────────────────

class _Dialog(ctk.CTkToplevel):
    """Themed, modal, centred over the parent. Escape closes."""

    def __init__(self, parent, app, title, resizable=False):
        super().__init__(parent)
        self.app = app
        self.title(title)
        self.configure(fg_color=COL_PANEL)
        if not resizable:
            self.resizable(False, False)
        self.transient(parent)
        self.bind("<Escape>", lambda e: self.destroy())

    def _show(self, focus_widget=None):
        self.update_idletasks()
        p = self.master
        try:
            x = p.winfo_rootx() + (p.winfo_width() - self.winfo_reqwidth()) // 2
            y = p.winfo_rooty() + max(40, (p.winfo_height() - self.winfo_reqheight()) // 3)
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        def grab():
            try:
                self.grab_set()
                self.focus_force()
                if focus_widget is not None:
                    focus_widget.focus_set()
            except Exception:
                pass
        self.after(80, grab)
        self.wait_window()

    def _buttons(self, parent, primary_text, primary_cmd, danger=False, cancel=True,
                 enter=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")
        self._primary = ctk.CTkButton(
            row, text=primary_text, command=primary_cmd,
            font=self.app.f_ui_b, height=38, corner_radius=9,
            fg_color=COL_DANGER_FILL if danger else COL_ACCENT,
            hover_color=COL_DANGER_HOV if danger else COL_ACCENT_HOV,
            text_color="#FFFFFF", text_color_disabled=COL_FAINT)
        self._primary.pack(side="right")
        if cancel:
            ctk.CTkButton(row, text="Cancel", command=self.destroy, font=self.app.f_ui,
                          height=38, width=92, corner_radius=9, fg_color=COL_FIELD,
                          hover_color=COL_BORDER, text_color=COL_TEXT
                          ).pack(side="right", padx=(0, 8))
        if enter:   # only for dialogs without a multi-line text field
            self.bind("<Return>", lambda e: primary_cmd()
                      if str(self._primary.cget("state")) != "disabled" else None)
        return row


# ── Edit / Add dialog ───────────────────────────────────────────────────────────

class SnippetDialog(_Dialog):
    """Modal add/edit dialog. Result in .result = {"label", "text"} or None."""

    def __init__(self, parent, app, title="Add Snippet", item=None):
        super().__init__(parent, app, title, resizable=True)
        self.result = None
        self.geometry("560x520")
        self.minsize(460, 400)
        item = item or {}

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=22)

        ctk.CTkLabel(wrap, text=title, font=app.f_h2,
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 16))

        ctk.CTkLabel(wrap, text="Label", font=app.f_ui_b,
                     text_color=COL_TEXT).pack(anchor="w")
        ctk.CTkLabel(wrap, text="Optional — shown in the list instead of the first line",
                     font=app.f_sm, text_color=COL_MUTED).pack(anchor="w", pady=(0, 6))
        self._label_var = ctk.StringVar(value=item.get("label", ""))
        ctk.CTkEntry(wrap, textvariable=self._label_var, font=app.f_ui,
                     height=38, corner_radius=9, border_width=1,
                     fg_color=COL_FIELD, border_color=COL_BORDER,
                     text_color=COL_TEXT, placeholder_text_color=COL_FAINT,
                     placeholder_text="e.g. Welcome message"
                     ).pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(wrap, text="Snippet text", font=app.f_ui_b,
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 6))
        self._text = ctk.CTkTextbox(wrap, font=app.f_mono, corner_radius=9,
                                    border_width=1, fg_color=COL_FIELD,
                                    border_color=COL_BORDER, text_color=COL_TEXT,
                                    wrap="word")
        self._text.pack(fill="both", expand=True, pady=(0, 18))
        if item.get("text"):
            self._text.insert("1.0", item["text"])
        self._text.bind("<Control-Return>", lambda e: (self._save(), "break")[1])

        btns = self._buttons(wrap, "Save snippet", self._save)
        ctk.CTkLabel(btns, text="Ctrl+Enter to save", font=app.f_sm,
                     text_color=COL_MUTED).pack(side="left")

        self._show(self._text)

    def _save(self):
        text = self._text.get("1.0", "end").strip()
        if not text:
            self.app._flash("Please enter some text first")
            return
        self.result = {"label": self._label_var.get().strip(), "text": text}
        self.destroy()


# ── Delete-choice dialog ────────────────────────────────────────────────────────

class DeleteChoiceDialog(_Dialog):
    """.choice = 'category' | 'all' | None (cancel)."""

    def __init__(self, parent, app, snippet_label, cat_name):
        super().__init__(parent, app, "Remove Snippet")
        self.choice = None
        short = (snippet_label[:60] + "…") if len(snippet_label) > 60 else snippet_label

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=22)
        ctk.CTkLabel(wrap, text="Remove this snippet?", font=app.f_h2,
                     text_color=COL_TEXT).pack(anchor="w")
        ctk.CTkLabel(wrap, text=f"“{short}”", font=app.f_ui, text_color=COL_MUTED,
                     wraplength=360, justify="left").pack(anchor="w", pady=(6, 18))

        ctk.CTkButton(wrap, text=f"Remove from “{cat_name}” only",
                      command=lambda: self._pick("category"), font=app.f_ui_b,
                      height=40, width=360, corner_radius=9, fg_color=COL_FIELD,
                      hover_color=COL_BORDER, text_color=COL_TEXT
                      ).pack(fill="x", pady=(0, 8))
        ctk.CTkButton(wrap, text="Delete everywhere",
                      command=lambda: self._pick("all"), font=app.f_ui_b,
                      height=40, corner_radius=9, fg_color=COL_DANGER_FILL,
                      hover_color=COL_DANGER_HOV, text_color="#FFFFFF"
                      ).pack(fill="x", pady=(0, 8))
        ctk.CTkButton(wrap, text="Cancel", command=self.destroy, font=app.f_ui,
                      height=36, corner_radius=9, fg_color="transparent",
                      hover_color=COL_FIELD, text_color=COL_MUTED).pack(fill="x")
        self._show()

    def _pick(self, value):
        self.choice = value
        self.destroy()


# ── Themed prompt / confirm dialogs ─────────────────────────────────────────────

class _TextPrompt(_Dialog):
    def __init__(self, parent, app, title, message, initial=""):
        super().__init__(parent, app, title)
        self.value = None
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=22)
        ctk.CTkLabel(wrap, text=title, font=app.f_h2,
                     text_color=COL_TEXT).pack(anchor="w")
        ctk.CTkLabel(wrap, text=message, font=app.f_ui, text_color=COL_MUTED,
                     wraplength=340, justify="left").pack(anchor="w", pady=(4, 12))
        self._var = ctk.StringVar(value=initial)
        ent = ctk.CTkEntry(wrap, textvariable=self._var, font=app.f_ui, width=340,
                           height=38, corner_radius=9, border_width=1,
                           fg_color=COL_FIELD, border_color=COL_BORDER,
                           text_color=COL_TEXT)
        ent.pack(fill="x", pady=(0, 18))
        ent.bind("<Return>", lambda e: self._ok())
        self._buttons(wrap, "Save", self._ok)
        self._show(ent)

    def _ok(self):
        self.value = self._var.get()
        self.destroy()


class _ConfirmDialog(_Dialog):
    def __init__(self, parent, app, title, message, primary="Delete", danger=True,
                 cancel=True):
        super().__init__(parent, app, title)
        self.ok = False
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=22)
        ctk.CTkLabel(wrap, text=title, font=app.f_h2, text_color=COL_TEXT
                     ).pack(anchor="w")
        ctk.CTkLabel(wrap, text=message, font=app.f_ui, text_color=COL_MUTED,
                     wraplength=360, justify="left").pack(anchor="w", pady=(6, 20))
        self._buttons(wrap, primary, self._confirm, danger=danger, cancel=cancel,
                     enter=True)
        self._show()

    def _confirm(self):
        self.ok = True
        self.destroy()


# ── JSON import / export ────────────────────────────────────────────────────────

EXPORT_FORMAT = "clipboard-manager-snippets"
_RE_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


class SnippetFileError(ValueError):
    """An import file that is valid JSON but holds no usable snippets."""


def parse_snippet_file(data):
    """Normalise an imported JSON document.

    Accepted shapes:
      • this app's export:   {"snippets": [{text, label, categories}], "categories": [...]}
      • a plain list:        [{"text": ..., "label": ...}, "plain string", ...]
        (clipboard_items.json works as-is)
      • grouped by category: {"Category": ["text", {"text": ..., "label": ...}], ...}

    Returns (snippets, category_order, skipped) where each snippet is
    {"text", "label", "id" | None, "categories": [names]}.
    """
    order, out = [], []
    skipped = 0

    def add_cat(name):
        if name and name not in order:
            order.append(name)

    def norm(entry, cats=()):
        if isinstance(entry, str):
            text, label, sid, ecats = entry, "", None, []
        elif isinstance(entry, dict):
            text = next((entry[k] for k in ("text", "content", "snippet")
                         if isinstance(entry.get(k), str)), None)
            if text is None:
                return None
            label = next((entry[k] for k in ("label", "title", "name")
                          if isinstance(entry.get(k), str)), "")
            sid = entry.get("id") if isinstance(entry.get("id"), str) else None
            ecats = entry.get("categories", entry.get("category", []))
            if isinstance(ecats, str):
                ecats = [ecats]
            if not isinstance(ecats, list):
                ecats = []
        else:
            return None
        text = _strip_control_chars(text)
        if not text.strip():
            return None
        names = []
        for c in list(cats) + [c for c in ecats if isinstance(c, str)]:
            c = c.strip()
            if c and c not in names:
                names.append(c)
                add_cat(c)
        return {"text": text, "label": label.strip(), "id": sid, "categories": names}

    def take(entries, cats=()):
        nonlocal skipped
        for e in entries:
            n = norm(e, cats)
            if n:
                out.append(n)
            else:
                skipped += 1

    if isinstance(data, list):
        take(data)
    elif isinstance(data, dict):
        listed = data.get("snippets", data.get("items"))
        if isinstance(listed, list):
            cats = data.get("categories")
            if isinstance(cats, list):
                for c in cats:
                    if isinstance(c, str):
                        add_cat(c.strip())
            take(listed)
        else:
            groups = {k: v for k, v in data.items() if isinstance(v, list)}
            flat = [x for v in groups.values() for x in v]
            if flat and all(isinstance(x, str) and _RE_UUID.match(x.strip()) for x in flat):
                raise SnippetFileError(
                    "This looks like a categories file — it only holds snippet IDs, "
                    "not text. Import clipboard_items.json or an exported file instead.")
            for name, entries in groups.items():
                add_cat(name.strip())
                take(entries, (name.strip(),) if name.strip() else ())
    else:
        raise SnippetFileError("The file doesn't contain a list of snippets.")

    if not out:
        raise SnippetFileError("No snippets with text were found in this file.")
    return out, order, skipped


def build_export(items, categories, only_category=None):
    """Self-contained export document (re-importable, category order kept)."""
    import datetime
    if only_category is not None:
        by_id = {it.get("id"): it for it in items}
        items = [by_id[i] for i in categories.get(only_category, []) if i in by_id]
        cat_names = [only_category]
    else:
        cat_names = list(categories)
    membership = {}
    for name in cat_names:
        for sid in categories.get(name, []):
            membership.setdefault(sid, []).append(name)
    return {
        "format": EXPORT_FORMAT,
        "version": 1,
        "exported": datetime.datetime.now().isoformat(timespec="seconds"),
        "categories": cat_names,
        "snippets": [{"id": it.get("id"), "label": it.get("label", ""),
                      "text": it.get("text", ""),
                      "categories": membership.get(it.get("id"), [])}
                     for it in items],
    }


class ImportDialog(_Dialog):
    """Review an import before applying it.
    .result = {"skip_dupes": bool, "extra_cat": name | None} or None."""

    def __init__(self, parent, app, filename, parsed, active_category):
        super().__init__(parent, app, "Import snippets")
        self.result = None
        self._snips, self._order, skipped = parsed
        self._active = active_category

        library = {it.get("text") for it in app.items}
        seen, self._n_new = set(), 0
        for s in self._snips:
            if s["text"] not in library and s["text"] not in seen:
                self._n_new += 1
            seen.add(s["text"])
        total = len(self._snips)
        self._n_dupes = total - self._n_new

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=22)
        ctk.CTkLabel(wrap, text="Import snippets", font=app.f_h2,
                     text_color=COL_TEXT).pack(anchor="w")
        ctk.CTkLabel(wrap, text=app._elide(filename, app.f_ui, 380), font=app.f_ui,
                     text_color=COL_MUTED).pack(anchor="w", pady=(2, 16))

        # Summary figures
        stats = ctk.CTkFrame(wrap, fg_color=COL_FIELD, corner_radius=10)
        stats.pack(fill="x")
        stats.grid_columnconfigure((0, 1, 2), weight=1, uniform="s")
        for col, (num, cap) in enumerate((
                (total, "in file"), (self._n_new, "new"),
                (self._n_dupes, "already saved"))):
            ctk.CTkLabel(stats, text=f"{num:,}", font=app.f_h2, text_color=COL_TEXT,
                         height=26).grid(row=0, column=col, pady=(12, 0))
            ctk.CTkLabel(stats, text=cap, font=app.f_sm, text_color=COL_MUTED,
                         height=18).grid(row=1, column=col, pady=(0, 12))

        notes = []
        if self._order:
            fresh = [c for c in self._order if c not in app.categories]
            line = f"Categories: {', '.join(self._order)}"
            if fresh:
                line += f"  ({len(fresh)} new)"
            notes.append(line)
        if skipped:
            notes.append(f"{skipped} entr{'y' if skipped == 1 else 'ies'} without text "
                         f"will be ignored.")
        for n in notes:
            ctk.CTkLabel(wrap, text=n, font=app.f_sm, text_color=COL_MUTED,
                         wraplength=400, justify="left", anchor="w"
                         ).pack(fill="x", pady=(10, 0))

        opts = ctk.CTkFrame(wrap, fg_color="transparent")
        opts.pack(fill="x", pady=(16, 20))
        box = dict(font=app.f_ui, text_color=COL_TEXT, fg_color=COL_ACCENT,
                   hover_color=COL_ACCENT_HOV, border_color=COL_FAINT,
                   checkbox_width=18, checkbox_height=18, corner_radius=5,
                   border_width=2, command=self._update)
        self._skip_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opts, text="Skip snippets I already have",
                        variable=self._skip_var, **box).pack(anchor="w")
        self._cat_var = ctk.BooleanVar(value=active_category is not None)
        if active_category is not None:
            ctk.CTkCheckBox(opts, text=f"Also add them to “{app._elide(active_category, app.f_ui, 220)}”",
                            variable=self._cat_var, **box).pack(anchor="w", pady=(10, 0))

        self._buttons(wrap, "", self._ok, enter=True)
        self._update()
        self._show()

    def _count(self):
        return self._n_new if self._skip_var.get() else len(self._snips)

    def _update(self):
        n = self._count()
        linking = self._cat_var.get() and self._active is not None
        if n:
            label = f"Import {n:,} snippet" + ("" if n == 1 else "s")
        elif linking or self._order:
            label = "Update categories"
        else:
            label = "Nothing new to import"
        usable = bool(n) or linking or bool(self._order)
        self._primary.configure(
            text=label, state="normal" if usable else "disabled",
            fg_color=COL_ACCENT if usable else COL_FIELD)

    def _ok(self):
        self.result = {"skip_dupes": bool(self._skip_var.get()),
                       "extra_cat": self._active if self._cat_var.get() else None}
        self.destroy()


# ── Main app ────────────────────────────────────────────────────────────────────

class ClipboardManager:
    SIDEBAR_W = 240
    INSPECTOR_W = 330

    def __init__(self, root):
        self.root = root
        self.root.title("Clipboard Manager")
        self.root.geometry("1120x760")
        self.root.minsize(920, 600)
        self.root.configure(fg_color=COL_BG)

        ui, disp, mono, icons = _resolve_fonts(root)
        self._icon_family = icons
        self.f_title = ctk.CTkFont(family=disp, size=22, weight="bold")
        self.f_brand = ctk.CTkFont(family=disp, size=15, weight="bold")
        self.f_h2    = ctk.CTkFont(family=disp, size=17, weight="bold")
        self.f_h     = ctk.CTkFont(family=ui, size=14, weight="bold")
        self.f_ui_b  = ctk.CTkFont(family=ui, size=13, weight="bold")
        self.f_ui    = ctk.CTkFont(family=ui, size=13)
        self.f_sm    = ctk.CTkFont(family=ui, size=12)
        self.f_sm_b  = ctk.CTkFont(family=ui, size=12, weight="bold")
        self.f_tiny  = ctk.CTkFont(family=ui, size=11, weight="bold")
        self.f_micro = ctk.CTkFont(family=ui, size=11)
        self.f_mono  = ctk.CTkFont(family=mono, size=12)
        self.f_icon  = ctk.CTkFont(family=icons, size=13) if icons else self.f_ui
        self.f_icon_sm = ctk.CTkFont(family=icons, size=11) if icons else self.f_sm

        self.items = load_items()
        if _ensure_ids(self.items):
            save_items(self.items)
        self.categories = load_categories()
        if _cleanup_categories(self.categories, self.items):
            save_categories(self.categories)

        self._settings = load_settings()
        self.density = max(0, min(2, int(self._settings.get("density", 2))))
        self._active_category = None      # None = "All snippets"
        self.filtered = []
        self._sel = None                  # selected filtered index
        self._sel_id = None               # selected snippet id (survives filtering)
        self._status_job = None
        self._relayout_job = None
        self._list_w = 1000
        self._menu_vars = []

        # drag state
        self._sd_src = None; self._sd_dst = None; self._sd_moved = False
        self._cd_src = None; self._cd_dst = None; self._cd_moved = False

        self._snip_rows = []
        self._cat_rows = []
        self._empty_widgets = []

        self._build_ui()
        self._bind_keys()
        self._refresh_cat_list()
        self._select_category("__all__")

    # ── Small widget helpers ────────────────────────────────────────────────────

    def _icon(self, key):
        glyph, fallback = _ICON_GLYPHS[key]
        return glyph if self._icon_family else fallback

    def _scale(self):
        try:
            return ctk.ScalingTracker.get_widget_scaling(self.root)
        except Exception:
            try:
                return self.root._get_widget_scaling()
            except Exception:
                return 1.0

    def _elide(self, text, font, max_px):
        if max_px <= 24:
            return text
        if font.measure(text) <= max_px:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid].rstrip() + "…") <= max_px:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + "…"

    def _ghost_btn(self, parent, text, cmd, width=None, danger=False, font=None,
                   hover=COL_SIDE_HOVER, height=30):
        kw = {"width": width} if width else {}
        return ctk.CTkButton(parent, text=text, command=cmd, font=font or self.f_sm,
                             height=height, corner_radius=8, fg_color="transparent",
                             hover_color=hover,
                             text_color=COL_DANGER if danger else COL_MUTED, **kw)

    def _card(self, parent):
        return ctk.CTkFrame(parent, fg_color=COL_PANEL, corner_radius=14,
                            border_width=1, border_color=COL_BORDER)

    # ── Layout ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_W)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    # ── Sidebar: brand, categories, theme ─────────────────────────────────────

    def _build_sidebar(self):
        side = ctk.CTkFrame(self.root, fg_color=COL_SIDEBAR, corner_radius=0,
                            width=self.SIDEBAR_W)
        side.grid(row=0, column=0, sticky="nsew")
        side.pack_propagate(False)

        # Brand
        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(20, 22))
        try:
            from PIL import Image
            img = ctk.CTkImage(Image.open(_asset_path("icon.png")), size=(26, 26))
            ctk.CTkLabel(brand, image=img, text="").pack(side="left", padx=(0, 10))
        except Exception:
            pass
        ctk.CTkLabel(brand, text="Clipboard Manager", font=self.f_brand,
                     text_color=COL_TEXT).pack(side="left")

        # Section header
        head = ctk.CTkFrame(side, fg_color="transparent")
        head.pack(fill="x", padx=(20, 12), pady=(0, 4))
        ctk.CTkLabel(head, text="CATEGORIES", font=self.f_tiny,
                     text_color=COL_MUTED).pack(side="left")
        self._ghost_btn(head, self._icon("add"), self._new_category, width=28,
                        font=self.f_icon_sm if self._icon_family else self.f_ui_b,
                        height=26).pack(side="right")

        # Bottom area (packed before the list so the list takes what's left)
        bottom = ctk.CTkFrame(side, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=14, pady=(0, 16))

        ctk.CTkFrame(bottom, fg_color=COL_BORDER, height=1).pack(fill="x", pady=(0, 10))
        tools = ctk.CTkFrame(bottom, fg_color="transparent")
        tools.pack(fill="x")
        self._ghost_btn(tools, "Rename", self._rename_category, width=64
                        ).pack(side="left")
        self._ghost_btn(tools, "Delete", self._delete_category, width=60, danger=True
                        ).pack(side="left", padx=(2, 0))
        self._ghost_btn(tools, self._icon("down"), self._cat_move_down, width=30,
                        font=self.f_icon_sm if self._icon_family else self.f_sm
                        ).pack(side="right")
        self._ghost_btn(tools, self._icon("up"), self._cat_move_up, width=30,
                        font=self.f_icon_sm if self._icon_family else self.f_sm
                        ).pack(side="right", padx=(0, 2))
        ctk.CTkLabel(bottom, text="Drag to reorder · double-click to rename",
                     font=self.f_micro, text_color=COL_MUTED, anchor="w",
                     justify="left", wraplength=200).pack(fill="x", padx=6, pady=(4, 12))

        self._theme_var = ctk.BooleanVar(value=_mode_is_dark())
        ctk.CTkSwitch(bottom, text="Dark mode", variable=self._theme_var,
                      command=self._toggle_theme, font=self.f_sm,
                      text_color=COL_TEXT, progress_color=COL_ACCENT,
                      button_color=("#FFFFFF", "#ECEEF2"),
                      button_hover_color=("#F4F5F7", "#FFFFFF"),
                      fg_color=("#C9CDD5", "#3A404C"), switch_width=36,
                      switch_height=18).pack(anchor="w", padx=6)

        # Category list
        self.cat_scroll = ctk.CTkScrollableFrame(
            side, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=COL_SIDEBAR, scrollbar_button_hover_color=COL_BORDER)
        self.cat_scroll.pack(fill="both", expand=True, padx=(10, 4), pady=(0, 8))

    # ── Main column: toolbar, heading, list + inspector ───────────────────────

    def _build_main(self):
        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=24, pady=(20, 22))

        # Toolbar: search + density
        bar = ctk.CTkFrame(main, fg_color="transparent")
        bar.pack(fill="x")

        sbar = ctk.CTkFrame(bar, fg_color=COL_PANEL, corner_radius=10,
                            border_width=1, border_color=COL_BORDER, height=40)
        sbar.pack(side="left", fill="x", expand=True)
        sbar.pack_propagate(False)
        if self._icon_family:
            ctk.CTkLabel(sbar, text=self._icon("search"), font=self.f_icon,
                         text_color=COL_MUTED, width=20).pack(side="left", padx=(14, 0))
        self._search = ctk.CTkEntry(sbar, font=self.f_ui,
                                    border_width=0, fg_color="transparent",
                                    text_color=COL_TEXT, placeholder_text_color=COL_FAINT,
                                    placeholder_text="Search snippets   (Ctrl+F)")
        self._search.pack(side="left", fill="both", expand=True, padx=(6, 4), pady=5)
        self._clear_btn = ctk.CTkButton(
            sbar, text=self._icon("clear"), width=28, height=28, corner_radius=7,
            font=self.f_icon_sm if self._icon_family else self.f_sm,
            fg_color="transparent", hover_color=COL_HOVER, text_color=COL_MUTED,
            command=self._clear_search)
        self.search_var = _EntryVar(self._search, self._on_search)

        dens = ctk.CTkFrame(bar, fg_color="transparent")
        dens.pack(side="right", padx=(16, 0))
        ctk.CTkLabel(dens, text="Density", font=self.f_sm,
                     text_color=COL_MUTED).pack(side="left", padx=(0, 8))
        self._density_seg = ctk.CTkSegmentedButton(
            dens, values=list(DENSITY_NAMES), command=self._set_density_name,
            font=self.f_sm, height=32, corner_radius=8, fg_color=COL_FIELD,
            selected_color=COL_SEG_SEL, selected_hover_color=COL_SEG_SEL,
            unselected_color=COL_FIELD, unselected_hover_color=COL_SIDE_HOVER,
            text_color=COL_TEXT)
        self._density_seg.set(DENSITY_NAMES[self.density])
        self._density_seg.pack(side="left")

        # Heading: category title + count, status pill, New snippet
        hrow = ctk.CTkFrame(main, fg_color="transparent")
        hrow.pack(fill="x", pady=(22, 14))
        tcol = ctk.CTkFrame(hrow, fg_color="transparent")
        tcol.pack(side="left")
        self._snippets_lbl = ctk.CTkLabel(tcol, text="All snippets", font=self.f_title,
                                          text_color=COL_TEXT, anchor="w", height=30)
        self._snippets_lbl.pack(anchor="w")
        self.count_var = ctk.StringVar()
        ctk.CTkLabel(tcol, textvariable=self.count_var, font=self.f_sm,
                     text_color=COL_MUTED, anchor="w", height=18).pack(anchor="w")

        ctk.CTkButton(hrow, text="+  New snippet", command=self._add_with_dialog,
                      font=self.f_ui_b, height=38, width=132, corner_radius=9,
                      fg_color=COL_ACCENT, hover_color=COL_ACCENT_HOV,
                      text_color="#FFFFFF").pack(side="right")
        self._io_btn = ctk.CTkButton(hrow, text="Import / Export  ▾",
                                     command=self._open_io_menu, font=self.f_ui,
                                     height=38, corner_radius=9, fg_color="transparent",
                                     hover_color=COL_SIDE_HOVER, text_color=COL_TEXT,
                                     border_width=1, border_color=COL_BORDER)
        self._io_btn.pack(side="right", padx=(0, 10))
        self._status = ctk.CTkFrame(hrow, fg_color=COL_FIELD, corner_radius=15,
                                    height=30)
        self.status_lbl = ctk.CTkLabel(self._status, text="", font=self.f_sm_b,
                                       text_color=COL_MUTED, height=30)
        self.status_lbl.pack(padx=14)

        # Body: list card + inspector
        body = ctk.CTkFrame(main, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0, minsize=self.INSPECTOR_W)
        body.grid_rowconfigure(0, weight=1)

        list_card = self._card(body)
        list_card.grid(row=0, column=0, sticky="nsew")
        self.snip_scroll = ctk.CTkScrollableFrame(
            list_card, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=COL_BORDER, scrollbar_button_hover_color=COL_FAINT)
        self.snip_scroll.pack(fill="both", expand=True, padx=6, pady=6)
        list_card.bind("<Configure>", self._on_list_resize, add="+")
        # Replace CTk's fit-to-canvas handler: stretching all rows on every drag
        # frame is the bulk of resize cost, so rows keep their width (the canvas
        # clips them) until the drag pauses, then widen once with re-elision.
        self._list_inner_w = None
        self._list_pending_w = None
        self.snip_scroll._parent_canvas.bind("<Configure>", self._on_list_canvas_resize)

        insp = ctk.CTkFrame(body, fg_color="transparent", width=self.INSPECTOR_W)
        insp.grid(row=0, column=1, sticky="nsew", padx=(16, 0))
        insp.pack_propagate(False)
        self._qa_short = False
        self._build_quick_add(insp)
        self._build_preview(insp)
        insp.bind("<Configure>", self._on_insp_resize, add="+")

    def _build_preview(self, parent):
        card = self._card(parent)
        card.pack(fill="both", expand=True)
        self._pv_card = card
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=16, pady=16)

        top = ctk.CTkFrame(pad, fg_color="transparent")
        top.pack(fill="x")
        mv_font = self.f_icon_sm if self._icon_family else self.f_sm
        self._down_btn = self._ghost_btn(top, self._icon("down"), self._move_down,
                                         width=28, font=mv_font, hover=COL_HOVER, height=28)
        self._down_btn.pack(side="right")
        self._up_btn = self._ghost_btn(top, self._icon("up"), self._move_up,
                                       width=28, font=mv_font, hover=COL_HOVER, height=28)
        self._up_btn.pack(side="right", padx=(0, 2))
        self._pv_title = ctk.CTkLabel(top, text="", font=self.f_h, text_color=COL_TEXT,
                                      anchor="w", justify="left")
        self._pv_title.pack(side="left", fill="x", expand=True)
        self._pv_meta = ctk.CTkLabel(pad, text="", font=self.f_sm, text_color=COL_MUTED,
                                     anchor="w", justify="left",
                                     wraplength=self.INSPECTOR_W - 40)
        self._pv_meta.pack(fill="x", pady=(2, 10))

        # Actions (packed bottom-up so the text well takes the remaining height)
        row2 = ctk.CTkFrame(pad, fg_color="transparent")
        row2.pack(side="bottom", fill="x")
        row2.grid_columnconfigure((0, 1, 2), weight=1, uniform="a")
        self._edit_btn = ctk.CTkButton(row2, text="Edit", command=self._edit_selected,
                                       font=self.f_ui, height=34, corner_radius=8,
                                       fg_color=COL_FIELD, hover_color=COL_BORDER,
                                       text_color=COL_TEXT)
        self._edit_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self._cats_btn = ctk.CTkButton(row2, text="Categories ▾",
                                       command=self._open_cats_menu_btn,
                                       font=self.f_ui, height=34, corner_radius=8,
                                       fg_color=COL_FIELD, hover_color=COL_BORDER,
                                       text_color=COL_TEXT)
        self._cats_btn.grid(row=0, column=1, sticky="ew", padx=3)
        self._del_btn = ctk.CTkButton(row2, text="Delete", command=self._delete_selected,
                                      font=self.f_ui, height=34, corner_radius=8,
                                      fg_color="transparent", hover_color=COL_DANGER_SOFT,
                                      text_color=COL_DANGER, border_width=1,
                                      border_color=COL_BORDER)
        self._del_btn.grid(row=0, column=2, sticky="ew", padx=(3, 0))

        self._copy_btn = ctk.CTkButton(pad, text="Copy to clipboard",
                                       command=self._copy_selected, font=self.f_ui_b,
                                       height=40, corner_radius=9, fg_color=COL_ACCENT,
                                       hover_color=COL_ACCENT_HOV, text_color="#FFFFFF")
        self._copy_btn.pack(side="bottom", fill="x", pady=(12, 6))

        self._pv_text = ctk.CTkTextbox(pad, font=self.f_ui, corner_radius=10,
                                       border_width=0, fg_color=COL_FIELD,
                                       text_color=COL_TEXT, wrap="word",
                                       scrollbar_button_color=COL_BORDER,
                                       scrollbar_button_hover_color=COL_FAINT)
        self._pv_text.pack(fill="both", expand=True)
        self._pv_text.bind("<Double-Button-1>", lambda e: self._copy_selected())

    def _build_quick_add(self, parent):
        card = self._card(parent)
        card.pack(side="bottom", fill="x", pady=(16, 0))
        self._qa_card = card
        outer = ctk.CTkFrame(card, fg_color="transparent")
        outer.pack(fill="x", padx=16, pady=(10, 12))

        head = ctk.CTkFrame(outer, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text="Quick add", font=self.f_h,
                     text_color=COL_TEXT).pack(side="left")
        self._qa_toggle = ctk.CTkButton(
            head, text="", width=30, height=28, corner_radius=7,
            font=self.f_icon_sm if self._icon_family else self.f_sm,
            fg_color="transparent", hover_color=COL_HOVER, text_color=COL_MUTED,
            command=self._toggle_quick_add)
        self._qa_toggle.pack(side="right")
        self._qa_target = ctk.CTkLabel(head, text="", font=self.f_sm,
                                       text_color=COL_MUTED)
        self._qa_target.pack(side="right", padx=(0, 4))

        pad = ctk.CTkFrame(outer, fg_color="transparent")
        self._qa_body = pad
        self._qa_collapsed = bool(self._settings.get("quick_add_collapsed", False))

        self.text_input = ctk.CTkTextbox(pad, height=84, font=self.f_ui,
                                         corner_radius=9, border_width=0,
                                         fg_color=COL_FIELD, text_color=COL_TEXT,
                                         wrap="word")
        self.text_input.pack(fill="x", pady=(8, 0))
        self._add_placeholder(self.text_input, "Paste or type a snippet…")
        self.text_input.bind("<Control-Return>", lambda e: (self._save_snippet(), "break")[1])

        self.label_input = ctk.CTkEntry(pad, font=self.f_ui, height=36,
                                        corner_radius=9, border_width=0,
                                        fg_color=COL_FIELD, text_color=COL_TEXT,
                                        placeholder_text_color=COL_FAINT,
                                        placeholder_text="Label (optional)")
        self.label_input.pack(fill="x", pady=(8, 12))
        self.label_input.bind("<Return>", lambda e: self._save_snippet())

        brow = ctk.CTkFrame(pad, fg_color="transparent")
        brow.pack(fill="x")
        ctk.CTkButton(brow, text="Save", command=self._save_snippet,
                      font=self.f_ui_b, height=36, corner_radius=9,
                      fg_color=COL_ACCENT, hover_color=COL_ACCENT_HOV,
                      text_color="#FFFFFF").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(brow, text="Open editor", command=self._add_with_dialog,
                      font=self.f_ui, height=36, width=108, corner_radius=9,
                      fg_color=COL_FIELD, hover_color=COL_BORDER,
                      text_color=COL_TEXT).pack(side="right", padx=(8, 0))
        self._apply_quick_add()

    # ── Keyboard ────────────────────────────────────────────────────────────────

    def _typing(self):
        try:
            w = self.root.focus_get()
        except Exception:
            return False
        return w is not None and w.winfo_class() in ("Entry", "Text")

    def _bind_keys(self):
        r = self.root
        r.bind("<Control-f>", lambda e: (self._search.focus_set(),
                                         self._search.select_range(0, "end"), "break")[2])
        r.bind("<Control-n>", lambda e: self._add_with_dialog())
        r.bind("<Up>", lambda e: None if self._typing() else self._step(-1))
        r.bind("<Down>", lambda e: None if self._typing() else self._step(+1))
        r.bind("<Return>", lambda e: None if self._typing() else self._copy_selected())
        r.bind("<Delete>", lambda e: None if self._typing() else self._delete_selected())
        r.bind("<Alt-Up>", lambda e: self._move_up())
        r.bind("<Alt-Down>", lambda e: self._move_down())
        mod = "Command" if sys.platform == "darwin" else "Control"
        r.bind(f"<{mod}-I>", lambda e: self._import_json())      # Ctrl/Cmd+Shift+I
        r.bind(f"<{mod}-E>", lambda e: self._export_json())      # Ctrl/Cmd+Shift+E

        # From the search box: arrows pick a result, Enter copies it, Esc clears.
        s = self._search
        s.bind("<Down>", lambda e: (self._step(+1), "break")[1])
        s.bind("<Up>", lambda e: (self._step(-1), "break")[1])
        s.bind("<Return>", lambda e: self._search_enter())
        s.bind("<Escape>", lambda e: self._clear_search())

    def _step(self, d):
        if not self.filtered:
            return
        if self._sel is None:
            self._select_snip(0 if d > 0 else len(self.filtered) - 1)
        else:
            self._select_snip(max(0, min(len(self.filtered) - 1, self._sel + d)))

    def _search_enter(self):
        if self._sel is None and self.filtered:
            self._select_snip(0)
        self._copy_selected()

    def _clear_search(self):
        if self.search_var.get():
            self.search_var.set("")

    def _on_search(self):
        if self.search_var.get():
            if not self._clear_btn.winfo_ismapped():
                self._clear_btn.pack(side="right", padx=(0, 6))
        else:
            self._clear_btn.pack_forget()
        self._refresh_list()

    # ── Placeholder for CTkTextbox ──────────────────────────────────────────────

    def _add_placeholder(self, w, ph):
        w._ph = ph
        w.insert("1.0", ph)
        w.configure(text_color=COL_FAINT)

        def on_in(_=None):
            if getattr(w, "_is_ph", True) and w.get("1.0", "end").strip() == ph:
                w.delete("1.0", "end")
                w.configure(text_color=COL_TEXT)
            w._is_ph = False

        def on_out(_=None):
            if not w.get("1.0", "end").strip():
                w.delete("1.0", "end")
                w.insert("1.0", ph)
                w.configure(text_color=COL_FAINT)
                w._is_ph = True

        w._is_ph = True
        w.bind("<FocusIn>", on_in)
        w.bind("<FocusOut>", on_out)

    def _get_text(self):
        if getattr(self.text_input, "_is_ph", False):
            return ""
        v = self.text_input.get("1.0", "end").strip()
        return "" if v == getattr(self.text_input, "_ph", "") else v

    def _get_label(self):
        return self.label_input.get().strip()

    def _clear_add_form(self):
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", self.text_input._ph)
        self.text_input.configure(text_color=COL_FAINT)
        self.text_input._is_ph = True
        self.label_input.delete(0, "end")
        self.root.focus_set()

    # ── Density / theme ─────────────────────────────────────────────────────────

    def _set_density_name(self, name):
        self._set_density(DENSITY_NAMES.index(name))

    def _set_density(self, value):
        d = int(round(float(value)))
        if d == self.density:
            return
        self.density = d
        if self._density_seg.get() != DENSITY_NAMES[d]:
            self._density_seg.set(DENSITY_NAMES[d])
        self._settings["density"] = d
        save_settings(self._settings)
        self._refresh_cat_list()
        self._refresh_list()

    def _toggle_theme(self):
        dark = bool(self._theme_var.get())
        ctk.set_appearance_mode("dark" if dark else "light")
        self._settings["theme"] = "dark" if dark else "light"
        save_settings(self._settings)

    # ── Category list ───────────────────────────────────────────────────────────

    def _cat_names(self):
        return list(self.categories.keys())

    def _refresh_cat_list(self):
        for r in self._cat_rows:
            r["frame"].destroy()
        self._cat_rows = []
        valid_ids = {i["id"] for i in self.items if "id" in i}

        rows = [("__all__", "All snippets", len(self.items))]
        for name in self.categories:
            cnt = sum(1 for sid in self.categories[name] if sid in valid_ids)
            rows.append((name, name, cnt))

        for pos, (key, label, cnt) in enumerate(rows):
            self._make_cat_row(pos, key, label, cnt)
        self._paint_cat_selection()

    def _make_cat_row(self, pos, key, label, cnt):
        d = self.density
        h = (28, 32, 36)[d]
        f = ctk.CTkFrame(self.cat_scroll, fg_color="transparent", corner_radius=8,
                         height=h)
        f.pack(fill="x", pady=(0 if d == 0 else 1))
        f.pack_propagate(False)
        shown = label if len(label) <= 22 else label[:21] + "…"
        name_lbl = ctk.CTkLabel(f, text=shown, height=h - 4,
                                font=(self.f_sm if d == 0 else self.f_ui),
                                text_color=COL_TEXT, anchor="w")
        name_lbl.pack(side="left", padx=(10, 4))
        cnt_lbl = ctk.CTkLabel(f, text=str(cnt), height=h - 4, font=self.f_micro,
                               text_color=COL_MUTED, anchor="e")
        cnt_lbl.pack(side="right", padx=(0, 10))

        r = {"frame": f, "name_lbl": name_lbl, "cnt_lbl": cnt_lbl,
             "key": key, "pos": pos}
        self._cat_rows.append(r)

        for w in (f, name_lbl, cnt_lbl):
            w.bind("<Button-1>", lambda e, p=pos: self._cat_press(p))
            w.bind("<B1-Motion>", lambda e, p=pos: self._cat_motion(e))
            w.bind("<ButtonRelease-1>", lambda e, p=pos: self._cat_release(p))
            w.bind("<Double-Button-1>", lambda e, p=pos: self._rename_category())
            w.bind("<Button-3>", lambda e, p=pos: self._cat_context(e, p))
            w.bind("<Enter>", lambda e, rr=r: self._cat_hover(rr, True))
            w.bind("<Leave>", lambda e, rr=r: self._cat_hover(rr, False))

    def _cat_is_active(self, r):
        return (r["key"] == "__all__" and self._active_category is None) or \
               (r["key"] == self._active_category)

    def _cat_hover(self, r, on):
        if self._cat_is_active(r):
            return
        r["frame"].configure(fg_color=COL_SIDE_HOVER if on else "transparent")

    def _paint_cat_selection(self):
        d = self.density
        for r in self._cat_rows:
            active = self._cat_is_active(r)
            r["frame"].configure(fg_color=COL_SEL if active else "transparent")
            r["name_lbl"].configure(
                text_color=COL_ACCENT_TEXT if active else COL_TEXT,
                font=(self.f_sm_b if d == 0 else self.f_ui_b) if active
                else (self.f_sm if d == 0 else self.f_ui))
            r["cnt_lbl"].configure(text_color=COL_ACCENT_TEXT if active else COL_MUTED)

    def _select_category(self, key):
        self._active_category = None if key == "__all__" else key
        self._snippets_lbl.configure(
            text="All snippets" if self._active_category is None else key)
        self._qa_target.configure(
            text="" if self._active_category is None
            else f"into {self._elide(key, self.f_sm, 150)}")
        self._paint_cat_selection()
        self._sel = None
        self._sel_id = None
        self._refresh_list()

    # category drag
    def _cat_press(self, pos):
        self._cd_src = pos; self._cd_dst = pos; self._cd_moved = False

    def _cat_motion(self, event):
        if self._cd_src is None:
            return
        self._cd_moved = True
        t = self._row_at_pointer(self._cat_rows, event.y_root)
        if t == 0:                          # can't drop above "All snippets"
            t = 1 if len(self._cat_rows) > 1 else 0
        if t == self._cd_dst:
            return
        self._cd_dst = t
        for i, r in enumerate(self._cat_rows):
            r["frame"].configure(fg_color=COL_DRAG if i == t else "transparent")

    def _cat_release(self, pos):
        src, dst, moved = self._cd_src, self._cd_dst, self._cd_moved
        self._cd_src = self._cd_dst = None
        if not moved or src is None or dst is None or src == dst or src == 0:
            self._paint_cat_selection()
            if not moved:
                key = self._cat_rows[pos]["key"] if pos < len(self._cat_rows) else "__all__"
                self._select_category(key)
            return
        names = self._cat_names()
        cs, cd = src - 1, dst - 1
        if 0 <= cs < len(names) and 0 <= cd < len(names):
            names.insert(cd, names.pop(cs))
            self.categories = {n: self.categories[n] for n in names}
            save_categories(self.categories)
            self._refresh_cat_list()
            self._flash("✓  Categories reordered")

    def _cat_selected_pos(self):
        if self._active_category is None:
            return 0
        names = self._cat_names()
        return names.index(self._active_category) + 1 if self._active_category in names else 0

    def _cat_move_up(self):
        self._cat_move(-1)

    def _cat_move_down(self):
        self._cat_move(+1)

    def _cat_move(self, d):
        pos = self._cat_selected_pos()
        if pos == 0:
            self._flash("Select a category first")
            return
        names = self._cat_names()
        cp = pos - 1
        np_ = cp + d
        if np_ < 0 or np_ >= len(names):
            return
        names.insert(np_, names.pop(cp))
        self.categories = {n: self.categories[n] for n in names}
        save_categories(self.categories)
        self._refresh_cat_list()
        self._flash("✓  Category moved")

    def _new_category(self):
        name = self._prompt("New category", "Name for the new category:")
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.categories:
            self._flash("That category already exists")
            return
        self.categories[name] = []
        save_categories(self.categories)
        self._active_category = name
        self._refresh_cat_list()
        self._select_category(name)
        self._flash(f'✓  Category "{name}" created')
        return name

    def _rename_category(self):
        if self._active_category is None:
            self._flash("Select a category to rename")
            return
        old = self._active_category
        new = self._prompt("Rename category", f'Rename "{old}" to:', old)
        if not new:
            return
        new = new.strip()
        if not new or new == old:
            return
        if new in self.categories:
            self._flash("That category already exists")
            return
        self.categories = {(new if k == old else k): v
                           for k, v in self.categories.items()}
        self._active_category = new
        save_categories(self.categories)
        self._refresh_cat_list()
        self._select_category(new)
        self._flash(f'✓  Renamed to "{new}"')

    def _delete_category(self):
        if self._active_category is None:
            self._flash("Select a category to delete")
            return
        name = self._active_category
        if not self._confirm("Delete category",
                             f'Delete "{name}"? Snippets inside are kept — only the '
                             f'category is removed.'):
            return
        del self.categories[name]
        self._active_category = None
        save_categories(self.categories)
        self._refresh_cat_list()
        self._select_category("__all__")
        self._flash(f'✓  Category "{name}" deleted')

    # ── Snippet list ────────────────────────────────────────────────────────────

    def _refresh_list(self):
        raw = self.search_var.get()
        query = raw.lower().strip()

        if self._active_category is not None:
            by_id = {it.get("id"): (i, it) for i, it in enumerate(self.items)}
            cat_ids = self.categories.get(self._active_category, [])
            pool = [by_id[sid] for sid in cat_ids if sid in by_id]
        else:
            pool = list(enumerate(self.items))

        self.filtered = [
            (i, it) for i, it in pool
            if query in it.get("label", "").lower() or query in it["text"].lower()
        ]

        for r in self._snip_rows:
            r["frame"].destroy()
        for w in self._empty_widgets:
            w.destroy()
        self._snip_rows = []
        self._empty_widgets = []
        for pos, (real_i, item) in enumerate(self.filtered):
            self._make_snip_row(pos, item)

        if not self.filtered:
            self._show_empty_state(raw.strip(), bool(pool))
        else:
            self._schedule_relayout(30)

        base = len(pool)
        if query:
            self.count_var.set(f"{len(self.filtered)} of {base} match “{raw.strip()}”")
        else:
            self.count_var.set(f"{base} snippet" + ("" if base == 1 else "s"))

        # Keep the same snippet selected if it's still visible
        self._sel = None
        if self._sel_id is not None:
            for pos, (_, it) in enumerate(self.filtered):
                if it.get("id") == self._sel_id:
                    self._sel = pos
                    break
        if self._sel is not None:
            self._paint_snip_selection()
            self._show_preview(self.filtered[self._sel][1])
        else:
            self._sel_id = None
            self._show_preview(None)

    def _show_empty_state(self, query, pool_has_items):
        if query:
            head, sub = f"No matches for “{query}”", "Try another word, or press Esc to clear the search."
        elif self._active_category is not None and not pool_has_items:
            head, sub = ("This category is empty",
                         "Right-click any snippet in All snippets — or use Categories ▾ — to file it here.")
        else:
            head, sub = ("No snippets yet",
                         "Use New snippet or Quick add to create one, or bring in a "
                         "batch with Import / Export ▸ Import from JSON.")
        a = ctk.CTkLabel(self.snip_scroll, text=head, font=self.f_h, text_color=COL_TEXT)
        a.pack(pady=(56, 4))
        b = ctk.CTkLabel(self.snip_scroll, text=sub, font=self.f_sm, text_color=COL_MUTED,
                         wraplength=320, justify="center")
        b.pack()
        self._empty_widgets = [a, b]

    def _make_snip_row(self, pos, item):
        d = self.density
        f = ctk.CTkFrame(self.snip_scroll, fg_color="transparent",
                         corner_radius=(6, 8, 10)[d])
        f.pack(fill="x", pady=(0, 1, 2)[d], padx=(0, 4))

        title, sub = _snippet_title_sub(item)
        padx = (10, 12, 14)[d]
        subl = None
        if d == 2:
            tfont = self.f_ui_b
            tl = ctk.CTkLabel(f, text=title, font=tfont, text_color=COL_TEXT,
                              anchor="w", justify="left", height=20)
            if sub:
                tl.pack(fill="x", padx=padx, pady=(10, 0))
                subl = ctk.CTkLabel(f, text=sub, font=self.f_sm, text_color=COL_MUTED,
                                    anchor="w", justify="left", height=18)
                subl.pack(fill="x", padx=padx, pady=(1, 10))
            else:
                tl.pack(fill="x", padx=padx, pady=(10, 10))
        else:
            tfont = self.f_sm if d == 0 else self.f_ui
            tl = ctk.CTkLabel(f, text=title, font=tfont, height=(26, 34)[d],
                              text_color=COL_TEXT, anchor="w", justify="left")
            tl.pack(fill="x", padx=padx)

        r = {"frame": f, "title": tl, "sub": subl, "pos": pos,
             "full_title": title, "full_sub": sub, "tfont": tfont, "padx": padx}
        self._snip_rows.append(r)
        self._elide_row(r)

        widgets = [f, tl] + ([subl] if subl else [])
        for w in widgets:
            w.bind("<Button-1>", lambda e, p=pos: self._snip_press(p))
            w.bind("<B1-Motion>", lambda e: self._snip_motion(e))
            w.bind("<ButtonRelease-1>", lambda e, p=pos: self._snip_release(p))
            w.bind("<Double-Button-1>", lambda e, p=pos: self._snip_dbl(p))
            w.bind("<Button-3>", lambda e, p=pos: self._snip_context(e, p))
            w.bind("<Enter>", lambda e, rr=r: self._snip_hover(rr, True))
            w.bind("<Leave>", lambda e, rr=r: self._snip_hover(rr, False))

    def _elide_row(self, r):
        # list card width (set by the window, not by row content) minus the
        # card padding, scrollbar and row padding
        avail = self._list_w / self._scale() - 2 * r["padx"] - 40
        r["title"].configure(text=self._elide(r["full_title"], r["tfont"], avail))
        if r["sub"] is not None:
            r["sub"].configure(text=self._elide(r["full_sub"], self.f_sm, avail))

    def _on_list_canvas_resize(self, event):
        self._list_pending_w = event.width
        if self._list_inner_w is None:          # first layout: apply at once
            self._apply_list_inner_width()
        else:
            self._schedule_relayout(90)

    def _apply_list_inner_width(self):
        w = self._list_pending_w
        if w is None or w == self._list_inner_w:
            return
        self._list_inner_w = w
        sf = self.snip_scroll
        sf._parent_canvas.itemconfigure(sf._create_window_id, width=w)

    def _on_list_resize(self, event):
        w = event.width
        if abs(w - self._list_w) < 4:
            return
        self._list_w = w
        self._schedule_relayout(90)

    def _schedule_relayout(self, delay):
        if self._relayout_job:
            self.root.after_cancel(self._relayout_job)

        def run():
            self._relayout_job = None
            self._apply_list_inner_width()
            for r in self._snip_rows:
                self._elide_row(r)
        self._relayout_job = self.root.after(delay, run)

    def _snip_hover(self, r, on):
        if r["pos"] == self._sel:
            return
        r["frame"].configure(fg_color=COL_HOVER if on else "transparent")

    def _paint_snip_selection(self):
        for r in self._snip_rows:
            sel = r["pos"] == self._sel
            r["frame"].configure(fg_color=COL_SEL if sel else "transparent")
            r["title"].configure(text_color=COL_ACCENT_TEXT if sel else COL_TEXT)

    def _select_snip(self, pos):
        if pos is None or pos >= len(self.filtered):
            return
        self._sel = pos
        _, item = self.filtered[pos]
        self._sel_id = item.get("id")
        self._paint_snip_selection()
        self._show_preview(item)
        self._ensure_visible(pos)

    def _ensure_visible(self, pos):
        try:
            canvas = self.snip_scroll._parent_canvas
            f = self._snip_rows[pos]["frame"]
            self.snip_scroll.update_idletasks()
            total = max(1, self.snip_scroll.winfo_height())
            y, h = f.winfo_y(), f.winfo_height()
            top, bot = canvas.yview()
            if y < top * total:
                canvas.yview_moveto(max(0.0, (y - 4) / total))
            elif y + h > bot * total:
                canvas.yview_moveto(max(0.0, (y + h + 4) / total - (bot - top)))
        except Exception:
            pass

    # ── Preview / inspector ─────────────────────────────────────────────────────

    def _show_preview(self, item):
        tb = self._pv_text
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        has = item is not None
        if has:
            title, _ = _snippet_title_sub(item)
            self._pv_title.configure(
                text=self._elide(title, self.f_h, self.INSPECTOR_W - 96),
                text_color=COL_TEXT)
            text = item.get("text", "")
            member = [n for n, ids in self.categories.items() if item.get("id") in ids]
            meta = f"{len(text):,} characters  ·  " + (", ".join(member) if member
                                                       else "No category")
            self._pv_meta.configure(text=meta)
            tb.insert("1.0", text)
            tb.configure(text_color=COL_TEXT)
        else:
            self._pv_title.configure(text="Nothing selected", text_color=COL_MUTED)
            self._pv_meta.configure(text="Click a snippet to preview it. "
                                         "Double-click to copy instantly.")
        tb.configure(state="disabled")
        self._set_actions_enabled(has)

    def _set_actions_enabled(self, on):
        st = "normal" if on else "disabled"
        self._copy_btn.configure(state=st,
                                 fg_color=COL_ACCENT if on else COL_FIELD,
                                 text_color="#FFFFFF" if on else COL_FAINT,
                                 text_color_disabled=COL_FAINT)
        for b in (self._edit_btn, self._cats_btn, self._del_btn,
                  self._up_btn, self._down_btn):
            b.configure(state=st, text_color_disabled=COL_FAINT)

    # snippet drag / click
    def _snip_press(self, pos):
        self._sd_src = pos; self._sd_dst = pos; self._sd_moved = False
        self._select_snip(pos)

    def _snip_motion(self, event):
        if self._sd_src is None:
            return
        self._sd_moved = True
        t = self._row_at_pointer(self._snip_rows, event.y_root)
        if t == self._sd_dst:
            return
        self._sd_dst = t
        for i, r in enumerate(self._snip_rows):
            if i == t:
                r["frame"].configure(fg_color=COL_DRAG)
            elif i == self._sel:
                r["frame"].configure(fg_color=COL_SEL)
            else:
                r["frame"].configure(fg_color="transparent")

    def _snip_release(self, pos):
        src, dst, moved = self._sd_src, self._sd_dst, self._sd_moved
        self._sd_src = self._sd_dst = None
        if not moved or src is None or dst is None or src == dst:
            self._paint_snip_selection()
            return
        if self.search_var.get().strip():
            self._flash("Clear search to reorder")
            self._refresh_list()
            return
        self._reorder(src, dst)
        self._refresh_list()
        self._select_snip(dst)
        self._flash("✓  Reordered")

    def _reorder(self, src, dst):
        if self._active_category is not None:
            cat_ids = self.categories[self._active_category]
            sid = self.filtered[src][1].get("id")
            did = self.filtered[dst][1].get("id")
            if sid in cat_ids and did in cat_ids:
                si, di = cat_ids.index(sid), cat_ids.index(did)
                cat_ids.insert(di, cat_ids.pop(si))
                save_categories(self.categories)
        else:
            rs = self.filtered[src][0]; rd = self.filtered[dst][0]
            it = self.items.pop(rs)
            self.items.insert(rd, it)
            save_items(self.items)

    def _snip_dbl(self, pos):
        self._select_snip(pos)
        self._copy_selected()

    def _move_up(self):
        self._move(-1)

    def _move_down(self):
        self._move(+1)

    def _move(self, d):
        if self._sel is None:
            self._flash("Select a snippet first")
            return
        if self.search_var.get().strip():
            self._flash("Clear search to reorder")
            return
        new = self._sel + d
        if new < 0 or new >= len(self.filtered):
            return
        self._reorder(self._sel, new)
        self._refresh_list()
        self._select_snip(new)

    def _row_at_pointer(self, rows, y_root):
        for i, r in enumerate(rows):
            f = r["frame"]
            try:
                top = f.winfo_rooty(); h = f.winfo_height()
            except Exception:
                continue
            if y_root < top + h:
                return i
        return len(rows) - 1

    # ── CRUD ────────────────────────────────────────────────────────────────────

    def _add_item(self, item):
        import uuid
        item.setdefault("id", str(uuid.uuid4()))
        self.items.append(item)
        if self._active_category is not None:
            self.categories[self._active_category].append(item["id"])
            save_categories(self.categories)
        save_items(self.items)
        self._clear_add_form()
        self._sel_id = item["id"]
        self._refresh_cat_list()
        self._refresh_list()
        if self._sel is not None:
            self._ensure_visible(self._sel)
        self._flash("✓  Snippet saved")

    def _save_snippet(self):
        text = self._get_text()
        if not text:
            self._flash("Enter some text first")
            return
        self._add_item({"label": self._get_label(), "text": text})

    def _add_with_dialog(self):
        prefill = {"label": self._get_label(), "text": self._get_text()}
        dlg = SnippetDialog(self.root, self, title="New snippet", item=prefill)
        if dlg.result:
            self._add_item(dlg.result)

    def _edit_selected(self):
        if self._sel is None:
            self._flash("Select a snippet first")
            return
        idx, item = self.filtered[self._sel]
        dlg = SnippetDialog(self.root, self, title="Edit snippet", item=item)
        if dlg.result:
            dlg.result["id"] = item.get("id", str(__import__("uuid").uuid4()))
            self.items[idx] = dlg.result
            save_items(self.items)
            self._refresh_list()
            self._flash("✓  Snippet updated")

    def _copy_selected(self):
        if self._sel is None:
            self._flash("Select a snippet first")
            return
        _, item = self.filtered[self._sel]
        if _copy_to_clipboard(item["text"], self.root):
            self._flash("✓  Copied to clipboard")
        else:
            self._flash("Copy failed — install pyperclip")

    def _delete_selected(self):
        if self._sel is None:
            self._flash("Select a snippet first")
            return
        idx, item = self.filtered[self._sel]
        label = item.get("label") or _snippet_title_sub(item)[0]
        item_id = item.get("id")

        if self._active_category is not None:
            dlg = DeleteChoiceDialog(self.root, self, label, self._active_category)
            if dlg.choice is None:
                return
            if dlg.choice == "category":
                if item_id in self.categories[self._active_category]:
                    self.categories[self._active_category].remove(item_id)
                    save_categories(self.categories)
                self._sel = None; self._sel_id = None
                self._refresh_cat_list()
                self._refresh_list()
                self._flash("✓  Removed from category")
                return
        else:
            if not self._confirm("Delete snippet", f'Delete “{label}”? This can’t be undone.'):
                return

        if item_id:
            for ids in self.categories.values():
                if item_id in ids:
                    ids.remove(item_id)
            save_categories(self.categories)
        self.items.pop(idx)
        save_items(self.items)
        self._sel = None; self._sel_id = None
        self._refresh_cat_list()
        self._refresh_list()
        self._flash("✓  Deleted")

    # ── Quick add: collapse + auto-hide on short windows ────────────────────────

    def _toggle_quick_add(self):
        self._qa_collapsed = not self._qa_collapsed
        self._settings["quick_add_collapsed"] = self._qa_collapsed
        save_settings(self._settings)
        self._apply_quick_add()
        if not self._qa_collapsed:
            self.text_input.focus_set()

    def _apply_quick_add(self):
        if self._qa_collapsed:
            self._qa_body.pack_forget()
        elif not self._qa_body.winfo_ismapped():
            self._qa_body.pack(fill="x", pady=(2, 4))
        self._qa_toggle.configure(
            text=self._icon("chev_down" if self._qa_collapsed else "chev_up"))

    def _on_insp_resize(self, event):
        # The preview needs ~300px to stay usable (text well + Copy + actions) and
        # the expanded Quick add takes ~260px. On short windows the preview wins;
        # New snippet (Ctrl+N) still covers adding.
        short = event.height / self._scale() < 590
        if short == self._qa_short:
            return
        self._qa_short = short
        if short:
            self._qa_card.pack_forget()
        else:
            self._qa_card.pack(side="bottom", fill="x", pady=(16, 0),
                               before=self._pv_card)

    # ── Import / export (JSON) ──────────────────────────────────────────────────

    def _open_io_menu(self):
        m = self._menu()
        m.add_command(label="Import from JSON…", accelerator=_ACCEL.format("I"),
                      command=self._import_json)
        m.add_separator()
        m.add_command(label=f"Export all snippets ({len(self.items)})…",
                      accelerator=_ACCEL.format("E"), command=self._export_json)
        if self._active_category is not None:
            cat = self._active_category
            n = len(self.categories.get(cat, []))
            m.add_command(label=f"Export “{cat}” only ({n})…",
                          command=lambda: self._export_json(cat))
        b = self._io_btn
        self._popup(m, b.winfo_rootx(), b.winfo_rooty() + b.winfo_height() + 2)

    def _export_json(self, category=None):
        from tkinter import filedialog
        import datetime
        doc = build_export(self.items, self.categories, category)
        n = len(doc["snippets"])
        if not n:
            self._flash("Nothing to export yet")
            return
        slug = ""
        if category is not None:
            slug = re.sub(r"[^\w\- ]+", "", category).strip().replace(" ", "-")
            slug = (slug or "category") + "-"
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export snippets", defaultextension=".json",
            initialfile=f"snippets-{slug}{datetime.date.today().isoformat()}.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
        except OSError as e:
            self._alert("Export failed", f"Couldn't write the file:\n{e.strerror or e}")
            return
        self._flash(f"✓  Exported {n:,} snippet" + ("" if n == 1 else "s"))

    def _import_json(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self.root, title="Import snippets",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            self._import_path(path)

    def _import_path(self, path):
        name = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.loads(_strip_control_chars(f.read()))
            parsed = parse_snippet_file(data)
        except json.JSONDecodeError as e:
            self._alert("Couldn't import",
                        f"“{name}” isn't valid JSON (line {e.lineno}, column {e.colno}).")
            return
        except UnicodeDecodeError:
            self._alert("Couldn't import", f"“{name}” isn't a UTF-8 text file.")
            return
        except SnippetFileError as e:
            self._alert("Couldn't import", str(e))
            return
        except OSError as e:
            self._alert("Couldn't import", f"Couldn't read the file:\n{e.strerror or e}")
            return

        dlg = ImportDialog(self.root, self, name, parsed, self._active_category)
        if dlg.result:
            self._apply_import(parsed, **dlg.result)

    def _apply_import(self, parsed, skip_dupes, extra_cat):
        import uuid
        snippets, order, _ = parsed
        by_text = {it.get("text"): it["id"] for it in self.items}
        ids = {it["id"] for it in self.items}
        new_cats = 0
        for name in order:
            if name not in self.categories:
                self.categories[name] = []
                new_cats += 1
        added = 0
        for s in snippets:
            sid = by_text.get(s["text"]) if skip_dupes else None
            if sid is None:
                sid = s["id"] if s["id"] and s["id"] not in ids else str(uuid.uuid4())
                self.items.append({"text": s["text"], "label": s["label"], "id": sid})
                ids.add(sid)
                by_text.setdefault(s["text"], sid)
                added += 1
            for name in s["categories"] + ([extra_cat] if extra_cat else []):
                if name in self.categories and sid not in self.categories[name]:
                    self.categories[name].append(sid)
        save_items(self.items)
        save_categories(self.categories)
        self._refresh_cat_list()
        self._refresh_list()
        msg = f"✓  Imported {added:,} snippet" + ("" if added == 1 else "s")
        if new_cats:
            msg += f" · {new_cats} new categor" + ("y" if new_cats == 1 else "ies")
        self._flash(msg)

    # ── Menus (native, themed) ──────────────────────────────────────────────────

    def _menu(self):
        return tk.Menu(self.root, tearoff=0, bg=_c(COL_PANEL), fg=_c(COL_TEXT),
                       activebackground=_c(COL_SEL), activeforeground=_c(COL_ACCENT_TEXT),
                       selectcolor=_c(COL_ACCENT_TEXT), relief="flat", bd=0,
                       font=(self.f_ui.cget("family"), 10))

    def _categories_menu(self, item_id):
        """Checkable list of categories — tick to add, untick to remove."""
        m = self._menu()
        self._menu_vars = []
        for name, ids in self.categories.items():
            var = tk.BooleanVar(value=item_id in ids)
            self._menu_vars.append(var)
            m.add_checkbutton(label=name, variable=var, onvalue=True, offvalue=False,
                              command=lambda n=name, v=var, s=item_id: self._toggle_membership(n, s, v.get()))
        if self.categories:
            m.add_separator()
        m.add_command(label="New category…",
                      command=lambda s=item_id: self._new_category_with(s))
        return m

    def _toggle_membership(self, name, sid, on):
        if on:
            self._ctx_add(name, sid)
        else:
            self._ctx_remove(name, sid)

    def _new_category_with(self, sid):
        name = self._new_category()
        if name and sid:
            self._ctx_add(name, sid)
            self._refresh_list()

    def _popup(self, m, x, y):
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def _open_cats_menu_btn(self):
        if self._sel is None:
            return
        item_id = self.filtered[self._sel][1].get("id")
        b = self._cats_btn
        self._popup(self._categories_menu(item_id), b.winfo_rootx(),
                    b.winfo_rooty() + b.winfo_height() + 2)

    def _snip_context(self, event, pos):
        self._snip_press(pos)
        self._sd_src = None
        if pos >= len(self.filtered):
            return
        _, item = self.filtered[pos]
        m = self._menu()
        m.add_command(label="Copy", accelerator="Enter", command=self._copy_selected)
        m.add_command(label="Edit…", command=self._edit_selected)
        m.add_separator()
        m.add_cascade(label="Categories", menu=self._categories_menu(item.get("id")))
        m.add_separator()
        m.add_command(label="Delete…", accelerator="Del", foreground=_c(COL_DANGER),
                      command=self._delete_selected)
        self._popup(m, event.x_root, event.y_root)
        return "break"

    def _cat_context(self, event, pos):
        if pos < len(self._cat_rows):
            self._select_category(self._cat_rows[pos]["key"])
        m = self._menu()
        m.add_command(label="New category…", command=self._new_category)
        if pos > 0:
            m.add_command(label="Rename…", command=self._rename_category)
            m.add_separator()
            m.add_command(label="Delete category…", foreground=_c(COL_DANGER),
                          command=self._delete_category)
        self._popup(m, event.x_root, event.y_root)
        return "break"

    def _ctx_add(self, name, sid):
        if sid not in self.categories[name]:
            self.categories[name].append(sid)
            save_categories(self.categories)
            self._refresh_cat_list()
            self._refresh_list()
            self._flash(f'✓  Added to "{name}"')

    def _ctx_remove(self, name, sid):
        if sid in self.categories[name]:
            self.categories[name].remove(sid)
            save_categories(self.categories)
            self._refresh_cat_list()
            self._refresh_list()
            self._flash(f'✓  Removed from "{name}"')

    # ── Small modal helpers (themed) ────────────────────────────────────────────

    def _prompt(self, title, message, initial=""):
        return _TextPrompt(self.root, self, title, message, initial).value

    def _confirm(self, title, message):
        return _ConfirmDialog(self.root, self, title, message).ok

    def _alert(self, title, message):
        _ConfirmDialog(self.root, self, title, message, primary="OK", danger=False,
                       cancel=False)

    # ── Status pill ─────────────────────────────────────────────────────────────

    def _flash(self, msg):
        if self._status_job:
            self.root.after_cancel(self._status_job)
        ok = msg.startswith("✓")
        text = msg.lstrip("✓").strip()
        self._status.configure(fg_color=COL_SUCCESS_SOFT if ok else COL_NOTICE_SOFT)
        self.status_lbl.configure(text=("✓  " + text) if ok else text,
                                  text_color=COL_SUCCESS if ok else COL_NOTICE)
        if not self._status.winfo_ismapped():
            self._status.pack(side="right", padx=(0, 12))
        self._status_job = self.root.after(2600, self._status.pack_forget)


# ── Entry point ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ctk.set_appearance_mode(_settings_get_mode())
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    if "_copy_text" in globals():          # macOS build: give _copy_text the tk root
        _tk_root = root
    # Window / taskbar / dock icon
    try:
        _ibase = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        if sys.platform == "win32" and os.path.exists(os.path.join(_ibase, "icon.ico")):
            root.iconbitmap(os.path.join(_ibase, "icon.ico"))
        elif os.path.exists(os.path.join(_ibase, "icon.png")):
            root.iconphoto(True, tk.PhotoImage(file=os.path.join(_ibase, "icon.png")))
    except Exception:
        pass
    ClipboardManager(root)
    root.mainloop()
