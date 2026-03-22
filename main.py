import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import time
import random
import json
import os
import traceback
import shlex
import math
import requests
import psutil
import pygame
from PIL import Image, ImageTk
from core import start_app

start_app()
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import winsound
except ImportError:
    winsound = None


# =========================================================
# BOTILYOS
# FULL VERSION WITH:
# 5) APP STORE / INSTALLER
# 6) TERMINAL
# 7) LOGIN + USER PROFILES
# 8) SOUND
# =========================================================

SAVE_FILE = "botilyos_data.json"
DEFAULT_BG = "#1e1e2f"
WINDOW_BG = "#2b2b3d"
BTN_COLOR = "#3b3b55"
TASKBAR_COLOR = "#111111"
TITLEBAR_BG = "#181824"
TITLEBAR_ACTIVE = "#25253a"

APP_CATALOG = {
    "Paint": {
        "description": "Simple drawing app.",
        "desktop_label": "Paint",
        "icon": "🎨"
    },
    "TicTacToe": {
        "description": "Play tic tac toe.",
        "desktop_label": "TicTacToe",
        "icon": "❌"
    },
    "Clock": {
        "description": "Clock and alarm style app.",
        "desktop_label": "Clock",
        "icon": "🕒"
    },
    "Music": {
        "description": "Simple  music player.",
        "desktop_label": "Music",
        "icon": "🎵"
    },
    "Gallery": {
        "description": "View image placeholders or imported image paths.",
        "desktop_label": "Gallery",
        "icon": "🖼"
    },
    "Terminal": {
        "description": "Command terminal for  OS.",
        "desktop_label": "Terminal",
        "icon": "⌨"
    }
}

SYSTEM_CONFIG_FILES = {
    "APIrunner.sys": "System API bridge module\nStatus: OK\nVersion: 1.0.0",
    "BootLoader.sys": "Boot sequence handler\nProtected system file",
    "DisplayCore.sys": "Desktop rendering service\nHandles windows and icons",
    "AudioEngine.sys": "Audio playback backend\nUsed by Music app"
}


# =========================================================
# AI
# =========================================================
def ollama_chat(messages):
    try:
        res = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama3.2:3b",
                "messages": messages,
                "stream": False
            },
            timeout=60
        )
        data = res.json()
        return data.get("message", {}).get("content", "No response.")
    except Exception as e:
        return f"Error: {e}"


# =========================================================
# ROOT
# =========================================================
root = tk.Tk()
root.title("BotilyOS")
root.configure(bg=DEFAULT_BG)
root.attributes("-fullscreen", True)

start_menu_visible = False
open_windows = []
notification_toasts = []
minimized_buttons = {}
desktop_icons = []
desktop_icon_refs = []
app_launchers = {}
logged_in_user = None
os_memory = {}
ui_ready = False

desktop = None
desktop_title = None
taskbar = None
clock_label = None
battery_label = None
minimized_windows_frame = None
start_menu = None
login_screen = None
login_user_var = None
login_pass_entry = None
sound_var = tk.BooleanVar(value=True)

_low_battery_notified = False


# =========================================================
# SOUND
# =========================================================
def play_sound(kind="click"):
    if not sound_var.get():
        return
    if winsound is None:
        return

    try:
        if kind == "startup":
            winsound.Beep(740, 120)
            winsound.Beep(880, 140)
        elif kind == "click":
            winsound.Beep(650, 50)
        elif kind == "notify":
            winsound.Beep(950, 110)
        elif kind == "error":
            winsound.Beep(300, 180)
        elif kind == "open":
            winsound.Beep(520, 70)
        elif kind == "close":
            winsound.Beep(420, 60)
        elif kind == "login":
            winsound.Beep(700, 90)
            winsound.Beep(900, 100)
        elif kind == "install":
            winsound.Beep(800, 100)
            winsound.Beep(1000, 130)
        elif kind == "type":
            winsound.Beep(600, 20)
    except Exception:
        pass


# =========================================================
# PERSISTENCE
# =========================================================
def default_user_data():
    return {
        "notes_content": "",
        "wallpaper": DEFAULT_BG,
        "browser_last_page": "home",
        "sound_enabled": True,
        "installed_apps": [],
        "ai_conversations": [
            {"role": "system", "content": "You are BotilyOS AI. Be helpful, short, and friendly."}
        ],
        "gallery_items": [],
        "files": {
            "Desktop": {
                "type": "folder",
                "children": {
                    "welcome.txt": {
                        "type": "file",
                        "content": "Welcome to BotilyOS!\n\nThis is your desktop."
                    },
                    "readme.txt": {
                        "type": "file",
                        "content": "BotilyOS is a fun OS made in Python."
                    },
                    "note.py": {
                        "type": "file",
                        "content": 'print("Hello from BotilyOS")'
                    }
                }
            },
            "Documents": {
                "type": "folder",
                "children": {}
            },
            "System": {
                "type": "folder",
                "children": {
                    "version.txt": {
                        "type": "file",
                        "content": "BotilyOS Version 1.0 BETA"
                    },
                    "Configs": {
                        "type": "folder",
                        "children": {
                            "APIrunner.sys": {
                                "type": "file",
                                "content": "System API bridge module\nStatus: OK\nVersion: 1.0.0"
                            },
                            "BootLoader.sys": {
                                "type": "file",
                                "content": "Boot sequence handler\nProtected system file"
                            },
                            "DisplayCore.sys": {
                                "type": "file",
                                "content": "Desktop rendering service\nHandles windows and icons"
                            },
                            "AudioEngine.sys": {
                                "type": "file",
                                "content": "Audio playback backend\nUsed by Music app"
                            }
                        }
                    }
                }
            }
        }
    }


def default_db():
    return {
        "current_user": "",
        "users": {}
    }


def convert_old_structure_to_new(files):
    if not isinstance(files, dict):
        return default_user_data()["files"]

    new_root = {}
    for name, value in files.items():
        if isinstance(value, dict) and value.get("type") in ("folder", "file", "zip"):
            new_root[name] = value
        elif isinstance(value, dict):
            children = {}
            for fname, fcontent in value.items():
                if isinstance(fcontent, dict) and fcontent.get("type") in ("folder", "file", "zip"):
                    children[fname] = fcontent
                else:
                    children[fname] = {"type": "file", "content": str(fcontent)}
            new_root[name] = {"type": "folder", "children": children}
        else:
            new_root[name] = {"type": "file", "content": str(value)}
    return new_root


def validate_node(node):
    if not isinstance(node, dict):
        return {"type": "folder", "children": {}}

    node_type = node.get("type", "folder")

    if node_type == "file":
        return {"type": "file", "content": str(node.get("content", ""))}

    if node_type in ("folder", "zip"):
        children = node.get("children", {})
        if not isinstance(children, dict):
            children = {}
        return {
            "type": node_type,
            "children": {k: validate_node(v) for k, v in children.items()}
        }

    return {"type": "folder", "children": {}}


def normalize_user_data(data):
    base = default_user_data()
    if not isinstance(data, dict):
        data = {}

    base.update(data)
    base["files"] = convert_old_structure_to_new(base.get("files", {}))
    base["files"] = {k: validate_node(v) for k, v in base["files"].items()}

    for folder in ["Desktop", "Documents", "System"]:
        if folder not in base["files"] or base["files"][folder].get("type") != "folder":
            base["files"][folder] = default_user_data()["files"][folder]

    if not isinstance(base.get("installed_apps"), list):
        base["installed_apps"] = []

    if not isinstance(base.get("gallery_items"), list):
        base["gallery_items"] = []

    if not isinstance(base.get("ai_conversations"), list) or not base["ai_conversations"]:
        base["ai_conversations"] = [
            {"role": "system", "content": "You are BotilyOS AI. Be helpful, short, and friendly."}
        ]

    return base


def load_db():
    data = default_db()
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                # NEW FORMAT
                if "users" in loaded:
                    data.update(loaded)
                else:
                    # OLD SINGLE USER FORMAT -> migrate into one default user
                    migrated_user = normalize_user_data(loaded)
                    data["users"] = {
                        "Player": {
                            "password": "",
                            "data": migrated_user
                        }
                    }
                    data["current_user"] = "Player"
        except Exception:
            pass

    # normalize all users
    fixed_users = {}
    for username, info in data.get("users", {}).items():
        if isinstance(info, dict) and "data" in info:
            fixed_users[username] = {
                "password": str(info.get("password", "")),
                "data": normalize_user_data(info.get("data", {}))
            }
        else:
            fixed_users[username] = {
                "password": "",
                "data": normalize_user_data(info if isinstance(info, dict) else {})
            }
    data["users"] = fixed_users
    return data


db = load_db()


def save_db():
    global db, logged_in_user, os_memory
    if logged_in_user and logged_in_user in db["users"]:
        db["users"][logged_in_user]["data"] = os_memory
        db["users"][logged_in_user]["data"]["sound_enabled"] = bool(sound_var.get())
        db["current_user"] = logged_in_user

    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def load_user(username):
    global logged_in_user, os_memory
    logged_in_user = username
    os_memory = normalize_user_data(db["users"][username]["data"])
    sound_var.set(bool(os_memory.get("sound_enabled", True)))


# =========================================================
# HELPERS
# =========================================================
def center_window_geometry(w=600, h=400):
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    return f"{w}x{h}+{x}+{y}"


def clear_open_windows():
    for win in open_windows[:]:
        try:
            if win.winfo_exists():
                win.destroy()
        except Exception:
            pass
    open_windows.clear()

    for _, btn in list(minimized_buttons.items()):
        try:
            btn.destroy()
        except Exception:
            pass
    minimized_buttons.clear()


def safe_button(parent, text, command, bg=BTN_COLOR, fg="white", **kwargs):
    def wrapper():
        play_sound("click")
        command()
    return tk.Button(parent, text=text, command=wrapper, bg=bg, fg=fg, **kwargs)


def path_to_text(path_list):
    return " / ".join(path_list)


def get_node_by_path(path_list):
    if not path_list:
        return None
    current = os_memory["files"].get(path_list[0])
    if current is None:
        return None
    for part in path_list[1:]:
        if current.get("type") not in ("folder", "zip"):
            return None
        current = current.get("children", {}).get(part)
        if current is None:
            return None
    return current


def get_children_dict(path_list):
    node = get_node_by_path(path_list)
    if node and node.get("type") in ("folder", "zip"):
        return node["children"]
    return None


def ensure_folder(path_list):
    node = get_node_by_path(path_list)
    return node and node.get("type") in ("folder", "zip")


def deep_copy_node(node):
    return json.loads(json.dumps(node))


def add_text_context_menu(widget):
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="Select All", command=lambda: widget.event_generate("<<SelectAll>>"))

    def show_menu(event):
        try:
            widget.focus_force()
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    widget.bind("<Button-3>", show_menu)


def add_entry_context_menu(widget):
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="Select All", command=lambda: widget.selection_range(0, "end"))

    def show_menu(event):
        try:
            widget.focus_force()
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    widget.bind("<Button-3>", show_menu)


# =========================================================
# NOTIFICATIONS
# =========================================================
def reposition_notifications():
    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    base_x = screen_w - 320
    base_y = screen_h - 110

    for i, toast in enumerate(notification_toasts):
        if toast.winfo_exists():
            y = base_y - (i * 90)
            toast.geometry(f"290x70+{base_x}+{y}")


def show_notification(title, message, duration=3200):
    play_sound("notify")

    toast = tk.Toplevel(root)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.configure(bg="#111111")

    outer = tk.Frame(toast, bg="#111111", bd=1, relief="solid")
    outer.pack(fill="both", expand=True)

    tk.Label(
        outer,
        text=title,
        bg="#111111",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        anchor="w"
    ).pack(fill="x", padx=10, pady=(8, 0))

    tk.Label(
        outer,
        text=message,
        bg="#111111",
        fg="#d7d7d7",
        font=("Segoe UI", 9),
        justify="left",
        anchor="w",
        wraplength=260
    ).pack(fill="both", expand=True, padx=10, pady=(2, 8))

    notification_toasts.insert(0, toast)
    reposition_notifications()

    def close_toast():
        if toast in notification_toasts:
            notification_toasts.remove(toast)
        if toast.winfo_exists():
            toast.destroy()
        reposition_notifications()

    toast.after(duration, close_toast)
    toast.bind("<Button-1>", lambda e: close_toast())


# =========================================================
# WINDOWS
# =========================================================
def focus_window(win):
    for w in open_windows:
        if hasattr(w, "titlebar") and w.winfo_exists():
            try:
                w.titlebar.configure(bg=TITLEBAR_BG)
                w.title_label.configure(bg=TITLEBAR_BG)
                w.btns.configure(bg=TITLEBAR_BG)
            except Exception:
                pass

    if win.winfo_exists():
        try:
            win.titlebar.configure(bg=TITLEBAR_ACTIVE)
            win.title_label.configure(bg=TITLEBAR_ACTIVE)
            win.btns.configure(bg=TITLEBAR_ACTIVE)
            win.lift()
        except Exception:
            pass


def restore_window(win):
    if not win.winfo_exists():
        return

    win.deiconify()
    win._is_minimized = False

    try:
        if getattr(win, "_is_fullscreen", False):
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight() - 40
            win.geometry(f"{screen_w}x{screen_h}+0+0")
        else:
            win.geometry(win._restore_geometry)
    except Exception:
        pass

    focus_window(win)

    if win in minimized_buttons:
        minimized_buttons[win].destroy()
        del minimized_buttons[win]


def add_taskbar_window_button(win):
    if minimized_windows_frame is None or win in minimized_buttons:
        return

    btn = tk.Button(
        minimized_windows_frame,
        text=win._window_title[:14],
        bg="#333333",
        fg="white",
        bd=0,
        padx=8,
        command=lambda: restore_window(win)
    )
    btn.pack(side="left", padx=3, pady=5)
    minimized_buttons[win] = btn


def make_draggable_window(win):
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.geometry(center_window_geometry(win._initial_w, win._initial_h))

    win._is_minimized = False
    win._is_fullscreen = False
    win._restore_geometry = center_window_geometry(win._initial_w, win._initial_h)

    border = tk.Frame(win, bg="#08080d", bd=1, relief="solid")
    border.pack(fill="both", expand=True)

    titlebar = tk.Frame(border, bg=TITLEBAR_BG, height=32)
    titlebar.pack(fill="x", side="top")

    title_label = tk.Label(
        titlebar,
        text=win._window_title,
        bg=TITLEBAR_BG,
        fg="white",
        font=("Segoe UI", 10, "bold")
    )
    title_label.pack(side="left", padx=10)

    btns = tk.Frame(titlebar, bg=TITLEBAR_BG)
    btns.pack(side="right", padx=4)

    content = tk.Frame(border, bg=WINDOW_BG)
    content.pack(fill="both", expand=True)

    win.outer = border
    win.titlebar = titlebar
    win.title_label = title_label
    win.btns = btns
    win.client = content

    drag_data = {"x": 0, "y": 0}

    def close_this():
        play_sound("close")
        if win in minimized_buttons:
            minimized_buttons[win].destroy()
            del minimized_buttons[win]
        if win in open_windows:
            open_windows.remove(win)
        win.destroy()

    def minimize_this():
        if win._is_minimized:
            return
        win._is_minimized = True
        try:
            win._restore_geometry = win.geometry()
        except Exception:
            pass
        win.withdraw()
        add_taskbar_window_button(win)

    def toggle_fullscreen():
        if not win.winfo_exists():
            return

        if not win._is_fullscreen:
            try:
                win._restore_geometry = win.geometry()
            except Exception:
                pass
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight() - 40
            win.geometry(f"{screen_w}x{screen_h}+0+0")
            win._is_fullscreen = True
            fullscreen_btn.config(text="❐")
            focus_window(win)
        else:
            win.geometry(win._restore_geometry)
            win._is_fullscreen = False
            fullscreen_btn.config(text="□")
            focus_window(win)

    def start_drag(event):
        if win._is_fullscreen:
            return
        drag_data["x"] = event.x_root - win.winfo_x()
        drag_data["y"] = event.y_root - win.winfo_y()
        focus_window(win)

    def on_drag(event):
        if win._is_fullscreen:
            return

        x = event.x_root - drag_data["x"]
        y = event.y_root - drag_data["y"]

        max_x = root.winfo_screenwidth() - 200
        max_y = root.winfo_screenheight() - 80

        x = max(0, min(x, max_x))
        y = max(0, min(y, max_y))

        win.geometry(f"+{x}+{y}")

    minimize_btn = tk.Button(
        btns, text="—", bg="#444466", fg="white", bd=0, width=3,
        activebackground="#555577", activeforeground="white", command=minimize_this
    )
    minimize_btn.pack(side="right", padx=2, pady=4)

    fullscreen_btn = tk.Button(
        btns, text="□", bg="#2d5a87", fg="white", bd=0, width=3,
        activebackground="#3970a8", activeforeground="white", command=toggle_fullscreen
    )
    fullscreen_btn.pack(side="right", padx=2, pady=4)

    close_btn = tk.Button(
        btns, text="✕", bg="#8d2a2a", fg="white", bd=0, width=3,
        activebackground="#aa3333", activeforeground="white", command=close_this
    )
    close_btn.pack(side="right", padx=2, pady=4)

    for widget in (titlebar, title_label):
        widget.bind("<Button-1>", start_drag)
        widget.bind("<B1-Motion>", on_drag)
        widget.bind("<Double-Button-1>", lambda e: toggle_fullscreen())

    win.bind("<Button-1>", lambda e: focus_window(win))
    win._toggle_fullscreen = toggle_fullscreen
    win._minimize_this = minimize_this


def create_window(title, w=600, h=400):
    play_sound("open")
    win = tk.Toplevel(root)
    win._window_title = title
    win._initial_w = w
    win._initial_h = h
    make_draggable_window(win)
    open_windows.append(win)
    focus_window(win)
    return win


def app_parent(win):
    return win.client if hasattr(win, "client") else win


# =========================================================
# SYSTEM UI
# =========================================================
def update_clock():
    if clock_label is not None:
        clock_label.config(text=time.strftime("%I:%M:%S %p"))
    root.after(1000, update_clock)


def update_battery():
    global _low_battery_notified

    if battery_label is None:
        root.after(15000, update_battery)
        return

    if psutil is None:
        battery_label.config(text="Battery: N/A")
    else:
        try:
            batt = psutil.sensors_battery()
            if batt is None:
                battery_label.config(text="Battery: N/A")
            else:
                percent = int(batt.percent)
                plugged = " ⚡" if batt.power_plugged else ""
                battery_label.config(text=f"Battery: {percent}%{plugged}")

                if percent <= 15 and not batt.power_plugged:
                    if not _low_battery_notified and ui_ready:
                        show_notification("Battery Low", f"Battery is at {percent}%")
                        _low_battery_notified = True
                else:
                    _low_battery_notified = False
        except Exception:
            battery_label.config(text="Battery: N/A")
    root.after(15000, update_battery)


def keep_fullscreen():
    root.attributes("-fullscreen", True)
    root.after(500, keep_fullscreen)


def apply_wallpaper():
    color = os_memory.get("wallpaper", DEFAULT_BG)
    if desktop is not None:
        desktop.configure(bg=color)
    if desktop_title is not None:
        desktop_title.configure(bg=color)

    if desktop is not None:
        for widget in desktop.winfo_children():
            try:
                widget.configure(bg=color)
            except Exception:
                pass


def set_wallpaper(color):
    os_memory["wallpaper"] = color
    apply_wallpaper()
    save_db()
    show_notification("Wallpaper Changed", "Desktop wallpaper updated.")


def toggle_start_menu():
    global start_menu_visible
    if start_menu is None:
        return
    if start_menu_visible:
        start_menu.place_forget()
        start_menu_visible = False
    else:
        root.update_idletasks()

        menu_width = max(start_menu.winfo_reqwidth(), 240)
        menu_height = max(start_menu.winfo_reqheight(), 400)
        taskbar_height = taskbar.winfo_height() if taskbar is not None else 40

        x = 8
        y = max(8, root.winfo_height() - taskbar_height - menu_height - 8)

        start_menu.place(x=x, y=y, width=menu_width, height=menu_height)
        start_menu.lift()
        start_menu_visible = True


def close_start_menu():
    global start_menu_visible
    if start_menu is not None:
        start_menu.place_forget()
    start_menu_visible = False


# =========================================================
# LOGIN / USERS
# =========================================================
def show_login_screen():
    global login_screen, login_user_var, login_pass_entry

    if desktop is not None:
        desktop.pack_forget()
    if taskbar is not None:
        taskbar.pack_forget()
    if start_menu is not None:
        start_menu.place_forget()

    clear_open_windows()

    if login_screen is not None and login_screen.winfo_exists():
        login_screen.destroy()

    login_screen = tk.Frame(root, bg="#0f1020")
    login_screen.pack(fill="both", expand=True)

    card = tk.Frame(login_screen, bg="#1d1f33", bd=2, relief="solid")
    card.place(relx=0.5, rely=0.5, anchor="center", width=460, height=420)

    tk.Label(
        card, text="BotilyOS Login", bg="#1d1f33", fg="white",
        font=("Segoe UI", 20, "bold")
    ).pack(pady=(25, 8))

    tk.Label(
        card, text="Choose user", bg="#1d1f33", fg="white", font=("Segoe UI", 11)
    ).pack()

    usernames = sorted(db["users"].keys()) or ["Player"]
    if "Player" not in db["users"] and not db["users"]:
        db["users"]["Player"] = {"password": "", "data": normalize_user_data({})}
        usernames = ["Player"]

    selected = db["current_user"] if db["current_user"] in db["users"] else usernames[0]
    login_user_var = tk.StringVar(value=selected)

    user_menu = tk.OptionMenu(card, login_user_var, *sorted(db["users"].keys()))
    user_menu.configure(bg=BTN_COLOR, fg="white", activebackground=BTN_COLOR, width=20)
    user_menu.pack(pady=8)

    tk.Label(
        card, text="Password", bg="#1d1f33", fg="white", font=("Segoe UI", 11)
    ).pack(pady=(18, 4))

    login_pass_entry = tk.Entry(card, show="*", font=("Segoe UI", 11))
    login_pass_entry.pack(padx=30, fill="x")
    add_entry_context_menu(login_pass_entry)

    status = tk.Label(card, text="", bg="#1d1f33", fg="#9fe89f", font=("Segoe UI", 10))
    status.pack(pady=10)

    def refresh_users():
        user_menu["menu"].delete(0, "end")
        names = sorted(db["users"].keys())
        if not names:
            db["users"]["Player"] = {"password": "", "data": normalize_user_data({})}
            names = ["Player"]
        for name in names:
            user_menu["menu"].add_command(label=name, command=tk._setit(login_user_var, name))
        if login_user_var.get() not in names:
            login_user_var.set(names[0])

    def do_login():
        username = login_user_var.get().strip()
        password = login_pass_entry.get()

        if username not in db["users"]:
            status.config(text="User not found", fg="#ff8d8d")
            play_sound("error")
            return

        real = db["users"][username].get("password", "")
        if real != password:
            status.config(text="Wrong password", fg="#ff8d8d")
            play_sound("error")
            return

        load_user(username)
        save_db()
        build_desktop_for_user()
        play_sound("login")
        show_notification("BotilyOS", f"Logged in as {username}")

    def create_user():
        username = simpledialog.askstring("Create User", "New username:", parent=root)
        if not username:
            return
        username = username.strip()
        if not username:
            return
        if username in db["users"]:
            messagebox.showerror("BotilyOS", "That user already exists.")
            play_sound("error")
            return

        password = simpledialog.askstring("Create User", "Password (blank allowed):", parent=root, show="*")
        if password is None:
            return

        db["users"][username] = {
            "password": password,
            "data": normalize_user_data({})
        }
        refresh_users()
        login_user_var.set(username)
        login_pass_entry.delete(0, "end")
        save_db()
        status.config(text=f"User '{username}' created", fg="#9fe89f")
        show_notification("Users", f"Created user {username}")

    def delete_user():
        username = login_user_var.get().strip()
        if username not in db["users"]:
            return
        if len(db["users"]) <= 1:
            messagebox.showerror("BotilyOS", "You need at least one user.")
            play_sound("error")
            return

        entered_pass = simpledialog.askstring(
            "Confirm Delete",
            f"Enter password for '{username}' to delete:",
            parent=root,
            show="*"
        )

        if entered_pass is None:
            return

        real_pass = db["users"][username].get("password", "")
        if entered_pass != real_pass:
            messagebox.showerror("BotilyOS", "Incorrect password.")
            play_sound("error")
            return

        del db["users"][username]
        refresh_users()
        login_pass_entry.delete(0, "end")
        save_db()
        status.config(text=f"Deleted user '{username}'", fg="#ffd27f")
        show_notification("Users", f"Deleted user {username}")

    btn_row = tk.Frame(card, bg="#1d1f33")
    btn_row.pack(pady=20)

    safe_button(btn_row, "Login", do_login).pack(side="left", padx=6)
    safe_button(btn_row, "Create User", create_user).pack(side="left", padx=6)
    safe_button(btn_row, "Delete User", delete_user, bg="#7a1f1f").pack(side="left", padx=6)

    tk.Label(
        card,
        text="Each user gets separate notes, files, AI memory, wallpaper, and installed apps.",
        bg="#1d1f33",
        fg="#d7d7d7",
        wraplength=360,
        justify="center",
        font=("Segoe UI", 9)
    ).pack(pady=(8, 0))

    login_pass_entry.bind("<Return>", lambda e: do_login())


def logout():
    global logged_in_user
    if messagebox.askyesno("Logout", f"Log out {logged_in_user}?"):
        save_db()
        logged_in_user = None
        show_login_screen()


# =========================================================
# DESKTOP / START
# =========================================================
def create_desktop_icon(label, command, x, y, icon="🗔"):
    color = os_memory.get("wallpaper", DEFAULT_BG)
    frame = tk.Frame(desktop, bg=color)
    frame.place(x=x, y=y)

    btn = tk.Button(
        frame,
        text=icon,
        font=("Segoe UI Emoji", 24),
        bg=color,
        fg="white",
        bd=0,
        activebackground=color,
        activeforeground="white",
        command=lambda: (play_sound("click"), command())[1]
    )
    btn.pack()

    tk.Label(
        frame,
        text=label,
        bg=color,
        fg="white",
        font=("Segoe UI", 10)
    ).pack()

    desktop_icon_refs.append(frame)


def build_desktop_icons():
    for item in desktop_icon_refs[:]:
        try:
            item.destroy()
        except Exception:
            pass
    desktop_icon_refs.clear()

    icons = [
        ("Notes", open_notes, "📝"),
        ("Calc", open_calc, "🧮"),
        ("Snake", open_snake, "🐍"),
        ("Files", open_files, "📁"),
        ("Botily AI", open_browser, "🤖"),
        ("Store", open_app_store, "🛍"),
        ("Settings", open_settings, "⚙")
    ]

    installed = set(os_memory.get("installed_apps", []))
    for app_name in sorted(installed):
        if app_name in APP_CATALOG and app_name in app_launchers:
            icons.append((
                APP_CATALOG[app_name]["desktop_label"],
                app_launchers[app_name],
                APP_CATALOG[app_name].get("icon", "🗔")
            ))

    y = 100
    for label, command, icon in icons:
        create_desktop_icon(label, command, 40, y, icon)
        y += 90

    desktop.update_idletasks()
    screen_w = desktop.winfo_width()
    if screen_w < 300:
        screen_w = root.winfo_screenwidth()
    create_desktop_icon("System Configs", open_system_configs, screen_w - 170, 40, "🖥")


def rebuild_start_menu():
    global start_menu
    if start_menu is None:
        return

    for child in start_menu.winfo_children():
        child.destroy()

    tk.Label(
        start_menu, text="BotilyOS", bg="#202020", fg="white",
        font=("Segoe UI", 14, "bold")
    ).pack(pady=10)

    menu_items = [
        ("Notes", open_notes),
        ("Calc", open_calc),
        ("Snake", open_snake),
        ("Files", open_files),
        ("Botily AI", open_browser),
        ("App Store", open_app_store),
("Settings", open_settings),
        ("System Configs", open_system_configs),
        ("About", open_about)
    ]

    installed = set(os_memory.get("installed_apps", []))
    for app_name in sorted(installed):
        if app_name in APP_CATALOG and app_name in app_launchers:
            menu_items.append((app_name, app_launchers[app_name]))

    menu_items += [
        ("Logout", logout),
    ]

    for text, cmd in menu_items:
        safe_button(
            start_menu, text, lambda c=cmd: (close_start_menu(), c())[1],
            relief="flat", anchor="w"
        ).pack(fill="x", padx=10, pady=4)


def build_desktop_for_user():
    global login_screen, desktop, desktop_title, taskbar, minimized_windows_frame, clock_label, battery_label, start_menu, ui_ready

    if login_screen is not None and login_screen.winfo_exists():
        login_screen.destroy()
        login_screen = None

    if desktop is None:
        desktop = tk.Frame(root, bg=os_memory.get("wallpaper", DEFAULT_BG))
        desktop.pack(fill="both", expand=True)

        desktop_title = tk.Label(
            desktop,
            text="BotilyOS Desktop",
            bg=os_memory.get("wallpaper", DEFAULT_BG),
            fg="white",
            font=("Segoe UI", 24, "bold")
        )
        desktop_title.place(x=30, y=20)

        taskbar = tk.Frame(root, bg=TASKBAR_COLOR, height=40)
        taskbar.pack(side="bottom", fill="x")

        safe_button(taskbar, "Start", toggle_start_menu).pack(side="left", padx=8, pady=5)

        minimized_windows_frame = tk.Frame(taskbar, bg=TASKBAR_COLOR)
        minimized_windows_frame.pack(side="left", padx=8)

        

        clock_label = tk.Label(taskbar, text="", bg=TASKBAR_COLOR, fg="white", font=("Segoe UI", 10))
        clock_label.pack(side="right", padx=10)

        battery_label = tk.Label(taskbar, text="Battery: N/A", bg=TASKBAR_COLOR, fg="white", font=("Segoe UI", 10))
        battery_label.pack(side="right", padx=10)

        start_menu = tk.Frame(root, bg="#202020", width=240, height=400, bd=2, relief="raised")
    else:
        desktop.pack(fill="both", expand=True)
        taskbar.pack(side="bottom", fill="x")
        apply_wallpaper()

    desktop_title.config(text=f"BotilyOS Desktop - {logged_in_user}")
    apply_wallpaper()
    build_desktop_icons()
    rebuild_start_menu()
    save_db()

    if not ui_ready:
        play_sound("startup")
        show_notification("BotilyOS", f"Welcome, {logged_in_user}")
        ui_ready = True


def open_system_configs():
    win = create_window("System Configs", 520, 360)
    body = app_parent(win)
    body.configure(bg="#111827")

    tk.Label(
        body,
        text="System Config Files",
        bg="#111827",
        fg="white",
        font=("Segoe UI", 14, "bold")
    ).pack(pady=10)

    main_frame = tk.Frame(body, bg="#111827")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    left_frame = tk.Frame(main_frame, bg="#1f2937", width=180)
    left_frame.pack(side="left", fill="y", padx=(0, 10))
    left_frame.pack_propagate(False)

    right_frame = tk.Frame(main_frame, bg="#0f172a")
    right_frame.pack(side="right", fill="both", expand=True)

    file_list = tk.Listbox(
        left_frame,
        bg="#1f2937",
        fg="white",
        selectbackground="#374151",
        selectforeground="white",
        font=("Consolas", 11),
        bd=0,
        highlightthickness=0
    )
    file_list.pack(fill="both", expand=True, padx=8, pady=8)

    text_box = tk.Text(
        right_frame,
        bg="#0f172a",
        fg="#d1d5db",
        insertbackground="white",
        font=("Consolas", 11),
        wrap="word",
        bd=0
    )
    text_box.pack(fill="both", expand=True, padx=8, pady=8)
    add_text_context_menu(text_box)

    def show_selected_file(event=None):
        sel = file_list.curselection()
        if not sel:
            return
        filename = file_list.get(sel[0])
        content = SYSTEM_CONFIG_FILES.get(filename, "")
        text_box.delete("1.0", "end")
        text_box.insert("1.0", f"{filename}\n" + "=" * len(filename) + f"\n\n{content}")

    for fname in SYSTEM_CONFIG_FILES:
        file_list.insert("end", fname)

    file_list.bind("<<ListboxSelect>>", show_selected_file)

    if file_list.size() > 0:
        file_list.selection_set(0)
        show_selected_file()


# =========================================================
# NOTES
# =========================================================
def open_notes():
    win = create_window("Notes", 700, 500)
    body = app_parent(win)

    tk.Label(body, text="Notes", bg=WINDOW_BG, fg="white", font=("Segoe UI", 14, "bold")).pack(pady=5)
    status = tk.Label(body, text="Autosave ON", bg=WINDOW_BG, fg="#9fe89f", font=("Segoe UI", 10))
    status.pack()

    text_frame = tk.Frame(body, bg=WINDOW_BG)
    text_frame.pack(fill="both", expand=True, padx=10, pady=5)

    text = tk.Text(text_frame, wrap="word", bg="white", fg="black", font=("Consolas", 11))
    text.pack(fill="both", expand=True)
    text.insert("1.0", os_memory.get("notes_content", ""))
    add_text_context_menu(text)

    def autosave(event=None):
        os_memory["notes_content"] = text.get("1.0", "end-1c")
        save_db()
        status.config(text="Autosaved")
        if win.winfo_exists():
            win.after(800, lambda: status.config(text="Autosave ON") if win.winfo_exists() else None)

    def save_as_file():
        content = text.get("1.0", "end-1c")
        os_memory["notes_content"] = content
        save_db()

        small = create_window("Save As", 360, 220)
        small_body = app_parent(small)

        tk.Label(small_body, text="Save inside  Files", bg=WINDOW_BG, fg="white", font=("Segoe UI", 11, "bold")).pack(pady=10)
        tk.Label(small_body, text="File name:", bg=WINDOW_BG, fg="white").pack()

        name_entry = tk.Entry(small_body, font=("Segoe UI", 10))
        name_entry.pack(padx=12, fill="x")
        name_entry.insert(0, "note.txt")
        add_entry_context_menu(name_entry)

        top_level_folders = [name for name, node in os_memory["files"].items() if node.get("type") == "folder"]

        tk.Label(small_body, text="Folder:", bg=WINDOW_BG, fg="white").pack(pady=(8, 0))
        folder_var = tk.StringVar(value="Documents")
        folder_menu = tk.OptionMenu(small_body, folder_var, *top_level_folders)
        folder_menu.configure(bg=BTN_COLOR, fg="white", activebackground=BTN_COLOR)
        folder_menu.pack(pady=4)

        def do_save():
            filename = name_entry.get().strip()
            folder = folder_var.get().strip()

            if not filename:
                status.config(text="Missing file name")
                return

            if "." not in filename:
                filename += ".txt"

            folder_node = os_memory["files"].get(folder)
            if not folder_node or folder_node.get("type") != "folder":
                return

            folder_node["children"][filename] = {"type": "file", "content": content}
            save_db()

            status.config(text=f"Saved as {filename} in {folder}")
            show_notification("File Saved", f"{filename} saved in {folder}")
            small.destroy()

        safe_button(small_body, "Save", do_save).pack(pady=10)

    def clear_note():
        text.delete("1.0", "end")
        os_memory["notes_content"] = ""
        save_db()
        status.config(text="Cleared")
        show_notification("Notes", "Note cleared.")

    text.bind("<KeyRelease>", autosave)

    bar = tk.Frame(body, bg="#1a1a2a")
    bar.pack(fill="x", side="bottom")

    safe_button(bar, "Save As", save_as_file).pack(side="left", padx=10, pady=5)
    safe_button(bar, "Clear", clear_note).pack(side="left", padx=5, pady=5)


# =========================================================
# CALC
# =========================================================
def open_calc():
    win = create_window("Calculator", 320, 420)
    body = app_parent(win)
    expr = tk.StringVar()

    entry = tk.Entry(body, textvariable=expr, font=("Segoe UI", 20), justify="right")
    entry.pack(fill="x", padx=10, pady=10)
    add_entry_context_menu(entry)

    def press(v):
        if v == "=":
            try:
                expr.set(str(eval(expr.get())))
            except Exception:
                expr.set("Error")
                play_sound("error")
                show_notification("Calculator", "Invalid expression.")
        elif v == "C":
            expr.set("")
        else:
            expr.set(expr.get() + v)

    buttons = [
        ["7", "8", "9", "/"],
        ["4", "5", "6", "*"],
        ["1", "2", "3", "-"],
        ["0", ".", "=", "+"],
        ["C"]
    ]

    for row in buttons:
        frame = tk.Frame(body, bg=WINDOW_BG)
        frame.pack(fill="both", expand=True, padx=5, pady=3)
        for b in row:
            tk.Button(
                frame, text=b, command=lambda v=b: press(v),
                bg=BTN_COLOR, fg="white", font=("Segoe UI", 16)
            ).pack(side="left", fill="both", expand=True, padx=3, pady=3)


# =========================================================
# SNAKE
# =========================================================
def open_snake():
    win = create_window("Snake", 520, 620)
    body = app_parent(win)

    tk.Label(body, text="Snake", bg=WINDOW_BG, fg="white", font=("Segoe UI", 16, "bold")).pack(pady=8)
    score_var = tk.StringVar(value="Score: 0")
    status_var = tk.StringVar(value="Use arrow keys to move")

    top_bar = tk.Frame(body, bg=WINDOW_BG)
    top_bar.pack(fill="x", padx=10)

    tk.Label(top_bar, textvariable=score_var, bg=WINDOW_BG, fg="white", font=("Segoe UI", 11, "bold")).pack(side="left")
    tk.Label(top_bar, textvariable=status_var, bg=WINDOW_BG, fg="#9fe89f", font=("Segoe UI", 10)).pack(side="right")

    canvas_size = 400
    cell_size = 20
    grid_size = canvas_size // cell_size

    canvas = tk.Canvas(body, width=canvas_size, height=canvas_size, bg="black", highlightthickness=0)
    canvas.pack(pady=10)

    tk.Label(body, text="Controls: Arrow Keys | Eat food | Don't hit walls or yourself", bg=WINDOW_BG, fg="white", font=("Segoe UI", 10)).pack(pady=4)
    btn_frame = tk.Frame(body, bg=WINDOW_BG)
    btn_frame.pack(pady=6)

    game_state = {
        "snake": [(5, 5), (4, 5), (3, 5)],
        "direction": "Right",
        "next_direction": "Right",
        "food": (10, 10),
        "running": True,
        "job": None,
        "score": 0
    }

    def spawn_food():
        while True:
            pos = (random.randint(0, grid_size - 1), random.randint(0, grid_size - 1))
            if pos not in game_state["snake"]:
                return pos

    def draw():
        canvas.delete("all")
        fx, fy = game_state["food"]
        canvas.create_rectangle(fx * cell_size, fy * cell_size, fx * cell_size + cell_size, fy * cell_size + cell_size, fill="red", outline="")
        for i, (x, y) in enumerate(game_state["snake"]):
            color = "#00ff66" if i == 0 else "#55ffaa"
            canvas.create_rectangle(x * cell_size, y * cell_size, x * cell_size + cell_size, y * cell_size + cell_size, fill=color, outline="#111111")

    def change_direction(new_dir):
        opposite = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}
        if opposite[new_dir] != game_state["direction"]:
            game_state["next_direction"] = new_dir

    def on_key(event):
        if event.keysym in ("Up", "Down", "Left", "Right"):
            change_direction(event.keysym)

    def game_over():
        game_state["running"] = False
        status_var.set("Game Over")
        play_sound("error")
        show_notification("Snake", f"Game Over. Score: {game_state['score']}")

    def move():
        if not game_state["running"] or not win.winfo_exists():
            return

        game_state["direction"] = game_state["next_direction"]
        head_x, head_y = game_state["snake"][0]

        if game_state["direction"] == "Up":
            head_y -= 1
        elif game_state["direction"] == "Down":
            head_y += 1
        elif game_state["direction"] == "Left":
            head_x -= 1
        elif game_state["direction"] == "Right":
            head_x += 1

        new_head = (head_x, head_y)

        if head_x < 0 or head_x >= grid_size or head_y < 0 or head_y >= grid_size:
            game_over()
            return

        if new_head in game_state["snake"]:
            game_over()
            return

        game_state["snake"].insert(0, new_head)

        if new_head == game_state["food"]:
            game_state["score"] += 1
            score_var.set(f"Score: {game_state['score']}")
            game_state["food"] = spawn_food()
            status_var.set("Yum")
            play_sound("notify")
        else:
            game_state["snake"].pop()
            status_var.set("Use arrow keys to move")

        draw()
        game_state["job"] = win.after(120, move)

    def restart_game():
        if game_state["job"] is not None:
            try:
                win.after_cancel(game_state["job"])
            except Exception:
                pass
        game_state["snake"] = [(5, 5), (4, 5), (3, 5)]
        game_state["direction"] = "Right"
        game_state["next_direction"] = "Right"
        game_state["food"] = spawn_food()
        game_state["running"] = True
        game_state["score"] = 0
        score_var.set("Score: 0")
        status_var.set("Use arrow keys to move")
        draw()
        move()
        show_notification("Snake", "Game restarted.")

    safe_button(btn_frame, "Restart", restart_game).pack(side="left", padx=5)
    safe_button(btn_frame, "Close", win.destroy, bg="#7a1f1f").pack(side="left", padx=5)

    win.bind("<Up>", on_key)
    win.bind("<Down>", on_key)
    win.bind("<Left>", on_key)
    win.bind("<Right>", on_key)
    win.focus_force()

    draw()
    move()


# =========================================================
# FILE EDITOR / PY RUNNER
# =========================================================
def open_text_file_editor(file_node, filename, on_save=None):
    editor = create_window(filename, 700, 500)
    body = app_parent(editor)

    tk.Label(body, text=filename, bg=WINDOW_BG, fg="white", font=("Segoe UI", 13, "bold")).pack(pady=6)

    text = tk.Text(body, wrap="word", bg="white", fg="black", font=("Consolas", 11))
    text.pack(fill="both", expand=True, padx=10, pady=10)
    text.insert("1.0", file_node.get("content", ""))
    add_text_context_menu(text)

    status = tk.Label(body, text="", bg=WINDOW_BG, fg="#9fe89f", font=("Segoe UI", 10))
    status.pack(pady=(0, 6))

    def save_now():
        file_node["content"] = text.get("1.0", "end-1c")
        save_db()
        status.config(text="Saved")
        show_notification("Saved", f"{filename} saved.")
        if on_save:
            on_save()

    bottom = tk.Frame(body, bg=WINDOW_BG)
    bottom.pack(fill="x", padx=10, pady=5)

    safe_button(bottom, "Save", save_now).pack(side="left", padx=5)
    safe_button(bottom, "Close", editor.destroy, bg="#7a1f1f").pack(side="left", padx=5)


def open_python_runner(file_node, filename):
    runner = create_window(f"Python Runner - {filename}", 900, 650)
    body = app_parent(runner)

    tk.Label(body, text=filename, bg=WINDOW_BG, fg="white", font=("Segoe UI", 13, "bold")).pack(pady=6)

    top_buttons = tk.Frame(body, bg=WINDOW_BG)
    top_buttons.pack(fill="x", padx=10, pady=(0, 6))

    status = tk.Label(top_buttons, text="", bg=WINDOW_BG, fg="#9fe89f", font=("Segoe UI", 10))
    status.pack(side="right", padx=8)

    editor = tk.Text(body, wrap="none", bg="white", fg="black", font=("Consolas", 11))
    editor.pack(fill="both", expand=True, padx=10, pady=(0, 8))
    editor.insert("1.0", file_node.get("content", ""))
    add_text_context_menu(editor)

    tk.Label(body, text="Output", bg=WINDOW_BG, fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10)

    output = tk.Text(body, height=10, bg="black", fg="lime", font=("Consolas", 10))
    output.pack(fill="x", padx=10, pady=(0, 10))
    add_text_context_menu(output)

    def save_code():
        file_node["content"] = editor.get("1.0", "end-1c")
        save_db()
        status.config(text="Saved")
        show_notification("Python File", f"{filename} saved.")

    def run_code():
        save_code()
        code = editor.get("1.0", "end-1c")
        output.delete("1.0", "end")
        _prints = []

        def _print(*args, **kwargs):
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")
            _prints.append(sep.join(str(a) for a in args) + end)

        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            allowed = {
                "random": __import__("random"),
                "string": __import__("string"),
                "math": __import__("math")
            }
            if name in allowed:
                return allowed[name]
            raise ImportError(f"module '{name}' is not allowed in BotilyOS Python Runner")

        safe_builtins = {
            "print": _print,
            "len": len,
            "range": range,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "min": min,
            "max": max,
            "sum": sum,
            "abs": abs,
            "enumerate": enumerate,
            "zip": zip,
            "__import__": safe_import
        }

        safe_globals = {"__builtins__": safe_builtins, "__name__": "__main__"}

        try:
            exec(code, safe_globals, safe_globals)
            result = "".join(_prints).strip()
            if result:
                output.insert("1.0", result)
            else:
                output.insert("1.0", "[Program finished with no output]")
            show_notification("Python Runner", f"{filename} ran successfully.")
        except Exception:
            output.insert("1.0", "Error:\n" + traceback.format_exc())
            play_sound("error")
            show_notification("Python Runner", "Program crashed with an error.")

    safe_button(top_buttons, "Run", run_code).pack(side="left", padx=4)
    safe_button(top_buttons, "Save", save_code).pack(side="left", padx=4)
    safe_button(top_buttons, "Close", runner.destroy, bg="#7a1f1f").pack(side="left", padx=4)


# =========================================================
# FILES
# =========================================================
def open_files():
    win = create_window("Files", 960, 580)
    body = app_parent(win)

    left = tk.Frame(body, bg="#202030", width=220)
    left.pack(side="left", fill="y")

    right = tk.Frame(body, bg=WINDOW_BG)
    right.pack(side="right", fill="both", expand=True)

    path_state = {"path": ["Desktop"]}

    topbar = tk.Frame(right, bg=WINDOW_BG)
    topbar.pack(fill="x", padx=10, pady=(10, 0))

    path_label = tk.Label(topbar, text="", bg=WINDOW_BG, fg="white", font=("Segoe UI", 12, "bold"))
    path_label.pack(side="left")

    list_frame = tk.Frame(right, bg=WINDOW_BG)
    list_frame.pack(fill="both", expand=True, padx=10, pady=10)

    file_list = tk.Listbox(list_frame, font=("Consolas", 11, "bold"), bg="white", fg="black")
    file_list.pack(side="left", fill="both", expand=True)

    scrollbar = tk.Scrollbar(list_frame, command=file_list.yview)
    scrollbar.pack(side="right", fill="y")
    file_list.config(yscrollcommand=scrollbar.set)

    preview_label = tk.Label(right, text="Preview", bg=WINDOW_BG, fg="white", font=("Segoe UI", 11, "bold"))
    preview_label.pack(anchor="w", padx=10)

    preview = tk.Text(right, height=10, bg="#f5f5f5", fg="black", font=("Consolas", 10))
    preview.pack(fill="x", padx=10, pady=(5, 10))
    add_text_context_menu(preview)

    def refresh_left_buttons():
        for widget in left.winfo_children():
            widget.destroy()

        tk.Label(left, text="Root Folders", bg="#202030", fg="white", font=("Segoe UI", 12, "bold")).pack(pady=10)

        for folder_name, node in os_memory["files"].items():
            if node.get("type") == "folder":
                safe_button(left, folder_name, lambda f=folder_name: open_path([f])).pack(fill="x", padx=8, pady=5)

    def current_children():
        return get_children_dict(path_state["path"])

    def get_selected_name():
        selection = file_list.curselection()
        if not selection:
            return None
        raw = file_list.get(selection[0])
        for prefix in ("[DIR] ", "[ZIP] ", "[FILE] "):
            if raw.startswith(prefix):
                return raw[len(prefix):]
        return raw

    def refresh_view():
        file_list.delete(0, "end")
        preview.delete("1.0", "end")
        path_label.config(text=f"Path: {path_to_text(path_state['path'])}")

        children = current_children()
        if children is None:
            return

        folders, zips, files = [], [], []
        for name, node in children.items():
            if node.get("type") == "folder":
                folders.append(name)
            elif node.get("type") == "zip":
                zips.append(name)
            else:
                files.append(name)

        for name in sorted(folders, key=str.lower):
            file_list.insert("end", f"[DIR] {name}")
        for name in sorted(zips, key=str.lower):
            file_list.insert("end", f"[ZIP] {name}")
        for name in sorted(files, key=str.lower):
            file_list.insert("end", f"[FILE] {name}")

    def open_path(path_list):
        node = get_node_by_path(path_list)
        if node and node.get("type") in ("folder", "zip"):
            path_state["path"] = path_list[:]
            refresh_view()

    def go_back():
        if len(path_state["path"]) > 1:
            path_state["path"].pop()
            refresh_view()

    def show_preview(event=None):
        preview.delete("1.0", "end")
        name = get_selected_name()
        if not name:
            return

        children = current_children()
        if children is None or name not in children:
            return

        node = children[name]
        node_type = node.get("type")

        if node_type == "file":
            preview.insert("1.0", node.get("content", ""))
        elif node_type == "folder":
            preview.insert("1.0", f"Folder: {name}\n\nDouble-click to open.")
        elif node_type == "zip":
            preview.insert("1.0", f"Zip: {name}\nContains {len(node.get('children', {}))} item(s)\n\nDouble-click to open.")

    def open_selected(event=None):
        name = get_selected_name()
        if not name:
            return

        children = current_children()
        if children is None or name not in children:
            return

        node = children[name]
        if node.get("type") in ("folder", "zip"):
            path_state["path"].append(name)
            refresh_view()
        elif node.get("type") == "file":
            if name.lower().endswith(".py"):
                open_python_runner(node, name)
            else:
                open_text_file_editor(node, name, on_save=refresh_view)

    def create_new_file():
        children = current_children()
        if children is None:
            return
        name = simpledialog.askstring("New File", "File name:", parent=win)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if "." not in name:
            name += ".txt"
        if name in children:
            messagebox.showerror("Files", "That name already exists.")
            play_sound("error")
            return
        default_content = 'print("Hello from BotilyOS")' if name.lower().endswith(".py") else ""
        children[name] = {"type": "file", "content": default_content}
        save_db()
        refresh_view()
        show_notification("Files", f"Created file: {name}")

    def create_new_folder():
        children = current_children()
        if children is None:
            return
        name = simpledialog.askstring("New Folder", "Folder name:", parent=win)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in children:
            messagebox.showerror("Files", "That name already exists.")
            play_sound("error")
            return
        children[name] = {"type": "folder", "children": {}}
        save_db()
        refresh_view()
        show_notification("Files", f"Created folder: {name}")

    def create_new_zip():
        children = current_children()
        if children is None:
            return
        name = simpledialog.askstring("New Zip", "Zip name:", parent=win)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if not name.lower().endswith(".zip"):
            name += ".zip"
        if name in children:
            messagebox.showerror("Files", "That name already exists.")
            play_sound("error")
            return
        children[name] = {"type": "zip", "children": {}}
        save_db()
        refresh_view()
        show_notification("Files", f"Created zip: {name}")

    def delete_selected():
        name = get_selected_name()
        if not name:
            return
        children = current_children()
        if children is None or name not in children:
            return
        del children[name]
        save_db()
        refresh_view()
        show_notification("Files", f"Deleted: {name}")

    buttons = tk.Frame(right, bg=WINDOW_BG)
    buttons.pack(fill="x", padx=10, pady=(0, 8))

    safe_button(buttons, "Back", go_back).pack(side="left", padx=4)
    safe_button(buttons, "New File", create_new_file).pack(side="left", padx=4)
    safe_button(buttons, "New Folder", create_new_folder).pack(side="left", padx=4)
    safe_button(buttons, "New Zip", create_new_zip).pack(side="left", padx=4)
    safe_button(buttons, "Delete", delete_selected, bg="#7a1f1f").pack(side="left", padx=4)

    file_list.bind("<<ListboxSelect>>", show_preview)
    file_list.bind("<Double-Button-1>", open_selected)

    refresh_left_buttons()
    open_path(["Desktop"])


# =========================================================
# BOTILY AI WITH SAVED MEMORY
# =========================================================
def open_browser():
    win = create_window("Botily AI", 850, 620)
    body = app_parent(win)

    chat = os_memory.get("ai_conversations", [
        {"role": "system", "content": "You are BotilyOS AI. Be helpful, short, and friendly."}
    ])

    top = tk.Frame(body, bg="#1b1b2a")
    top.pack(fill="x")

    entry = tk.Entry(top, font=("Segoe UI", 12))
    entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
    add_entry_context_menu(entry)

    chat_box = tk.Text(body, bg="white", fg="black", font=("Consolas", 11))
    chat_box.pack(fill="both", expand=True, padx=10, pady=10)
    add_text_context_menu(chat_box)

    status = tk.Label(body, text="AI Ready", bg=WINDOW_BG, fg="white")
    status.pack(fill="x")

    def redraw_chat():
        chat_box.delete("1.0", "end")
        chat_box.insert("end", "🤖 Botily AI Ready\n\n")
        for msg in chat:
            if msg["role"] == "system":
                continue
            prefix = "You" if msg["role"] == "user" else "AI"
            chat_box.insert("end", f"{prefix}: {msg['content']}\n\n")
        chat_box.see("end")

    redraw_chat()

    def send():
        user = entry.get().strip()
        if not user:
            return
        entry.delete(0, "end")

        chat.append({"role": "user", "content": user})
        redraw_chat()
        chat_box.insert("end", "AI: ...\n\n")
        chat_box.see("end")
        chat_box.update()

        response = ollama_chat(chat)
        chat.append({"role": "assistant", "content": response})
        os_memory["ai_conversations"] = chat
        save_db()
        redraw_chat()
        status.config(text="Responded")

    def clear():
        chat.clear()
        chat.append({"role": "system", "content": "You are BotilyOS AI. Be helpful, short, and friendly."})
        os_memory["ai_conversations"] = chat
        save_db()
        redraw_chat()
        status.config(text="Chat cleared")

    def save_chat_to_file():
        text = []
        for msg in chat:
            if msg["role"] == "system":
                continue
            prefix = "You" if msg["role"] == "user" else "AI"
            text.append(f"{prefix}: {msg['content']}")
        filename = f"chat_{int(time.time())}.txt"
        os_memory["files"]["Documents"]["children"][filename] = {
            "type": "file",
            "content": "\n\n".join(text)
        }
        save_db()
        show_notification("Botily AI", f"Saved chat as {filename}")

    btn_row = tk.Frame(top, bg="#1b1b2a")
    btn_row.pack(side="right", padx=5)

    safe_button(btn_row, "Send", send).pack(side="left", padx=3)
    safe_button(btn_row, "Save Chat", save_chat_to_file).pack(side="left", padx=3)
    safe_button(btn_row, "Clear", clear, bg="#7a1f1f").pack(side="left", padx=3)

    entry.bind("<Return>", lambda e: send())


# =========================================================
# APP STORE
# =========================================================
def install_app(app_name):
    installed = os_memory.setdefault("installed_apps", [])
    if app_name not in installed:
        installed.append(app_name)
        save_db()
        build_desktop_icons()
        rebuild_start_menu()
        play_sound("install")
        show_notification("App Store", f"Installed {app_name}")


def uninstall_app(app_name):
    if app_name == "Terminal":
        messagebox.showerror("App Store", "Terminal cannot be removed.")
        play_sound("error")
        return

    installed = os_memory.setdefault("installed_apps", [])
    if app_name in installed:
        installed.remove(app_name)
        save_db()
        build_desktop_icons()
        rebuild_start_menu()
        show_notification("App Store", f"Uninstalled {app_name}")


def open_app_store():
    win = create_window("App Store", 760, 560)
    body = app_parent(win)

    tk.Label(body, text="Botily Store", bg=WINDOW_BG, fg="white", font=("Segoe UI", 18, "bold")).pack(pady=10)
    tk.Label(body, text="Install or remove apps for this user profile.", bg=WINDOW_BG, fg="#d7d7d7", font=("Segoe UI", 10)).pack()

    content = tk.Frame(body, bg=WINDOW_BG)
    content.pack(fill="both", expand=True, padx=16, pady=16)

    canvas = tk.Canvas(content, bg=WINDOW_BG, highlightthickness=0)
    scrollbar = tk.Scrollbar(content, command=canvas.yview)
    inner = tk.Frame(canvas, bg=WINDOW_BG)

    inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def refresh():
        for child in inner.winfo_children():
            child.destroy()

        installed = set(os_memory.get("installed_apps", []))

        for app_name, info in APP_CATALOG.items():
            card = tk.Frame(inner, bg="#23233a", bd=1, relief="solid")
            card.pack(fill="x", pady=8, padx=6)

            left = tk.Frame(card, bg="#23233a")
            left.pack(side="left", fill="both", expand=True, padx=12, pady=12)

            tk.Label(left, text=app_name, bg="#23233a", fg="white", font=("Segoe UI", 13, "bold")).pack(anchor="w")
            tk.Label(left, text=info["description"], bg="#23233a", fg="#d7d7d7", font=("Segoe UI", 10), wraplength=430, justify="left").pack(anchor="w", pady=(4, 0))

            right = tk.Frame(card, bg="#23233a")
            right.pack(side="right", padx=12)

            if app_name in installed:
                tk.Label(right, text="Installed", bg="#23233a", fg="#9fe89f", font=("Segoe UI", 10, "bold")).pack(pady=(8, 4))
                safe_button(right, "Uninstall", lambda a=app_name: [uninstall_app(a), refresh()], bg="#7a1f1f", width=12).pack(pady=(0, 8))
            else:
                tk.Label(right, text="Not Installed", bg="#23233a", fg="#ffd27f", font=("Segoe UI", 10, "bold")).pack(pady=(8, 4))
                safe_button(right, "Install", lambda a=app_name: [install_app(a), refresh()], width=12).pack(pady=(0, 8))

    refresh()


# =========================================================
# TERMINAL
# =========================================================
def open_terminal():
    win = create_window("Terminal", 920, 620)
    body = app_parent(win)

    tk.Label(body, text="Botily Terminal", bg=WINDOW_BG, fg="white", font=("Segoe UI", 15, "bold")).pack(pady=(8, 4))

    output = tk.Text(body, bg="black", fg="#3dff7a", font=("Consolas", 11))
    output.pack(fill="both", expand=True, padx=10, pady=(0, 8))
    add_text_context_menu(output)

    bottom = tk.Frame(body, bg=WINDOW_BG)
    bottom.pack(fill="x", padx=10, pady=(0, 10))

    prompt_var = tk.StringVar()
    tk.Label(bottom, text=">", bg=WINDOW_BG, fg="white", font=("Consolas", 12, "bold")).pack(side="left")
    entry = tk.Entry(bottom, textvariable=prompt_var, font=("Consolas", 11))
    entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
    add_entry_context_menu(entry)

    cwd = {"path": ["Desktop"]}

    def writeln(text=""):
        output.insert("end", text + "\n")
        output.see("end")

    def current_dir_name():
        return "/" + "/".join(cwd["path"])

    def resolve_path(arg):
        if not arg or arg == ".":
            return cwd["path"][:]

        if arg.startswith("/"):
            parts = [p for p in arg.strip("/").split("/") if p]
            if not parts:
                return []
            return parts

        path = cwd["path"][:]
        for p in [x for x in arg.split("/") if x]:
            if p == ".":
                continue
            if p == "..":
                if len(path) > 1:
                    path.pop()
            else:
                path.append(p)
        return path

    def run_python_by_path(path_list):
        if not path_list:
            return
        node = get_node_by_path(path_list)
        if not node or node.get("type") != "file":
            writeln("File not found.")
            return
        if not path_list[-1].lower().endswith(".py"):
            writeln("That is not a .py file.")
            return
        open_python_runner(node, path_list[-1])

    def command_help():
        writeln("Commands:")
        writeln("help")
        writeln("pwd")
        writeln("ls")
        writeln("dir")
        writeln("cd <folder>")
        writeln("mkdir <name>")
        writeln("touch <name>")
        writeln("cat <file>")
        writeln("write <file> <text>")
        writeln("del <name>")
        writeln("open notes|files|calc|snake|store|settings|about|terminal|paint|clock|music|gallery|tictactoe")
        writeln("apps")
        writeln("install <AppName>")
        writeln("uninstall <AppName>")
        writeln("whoami")
        writeln("time")
        writeln("clear")
        writeln("run <pythonfile.py>")

    def execute(cmd_line):
        cmd_line = cmd_line.strip()
        if not cmd_line:
            return

        writeln(f"> {cmd_line}")

        try:
            parts = shlex.split(cmd_line)
        except Exception:
            writeln("Bad command syntax.")
            play_sound("error")
            return

        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        children = get_children_dict(cwd["path"])

        if cmd == "help":
            command_help()

        elif cmd in ("pwd",):
            writeln(current_dir_name())

        elif cmd in ("ls", "dir"):
            if children is None:
                writeln("Invalid path.")
                return
            names = []
            for name, node in children.items():
                prefix = "[DIR]" if node.get("type") == "folder" else "[ZIP]" if node.get("type") == "zip" else "[FILE]"
                names.append(f"{prefix} {name}")
            if not names:
                writeln("(empty)")
            else:
                for item in sorted(names, key=str.lower):
                    writeln(item)

        elif cmd == "cd":
            if not args:
                cwd["path"] = ["Desktop"]
                writeln(current_dir_name())
                return
            new_path = resolve_path(args[0])
            if ensure_folder(new_path):
                cwd["path"] = new_path
                writeln(current_dir_name())
            else:
                writeln("Folder not found.")
                play_sound("error")

        elif cmd == "mkdir":
            if not args:
                writeln("Usage: mkdir <name>")
                return
            name = args[0]
            if children is None:
                writeln("Invalid location.")
                return
            if name in children:
                writeln("That already exists.")
                return
            children[name] = {"type": "folder", "children": {}}
            save_db()
            writeln(f"Created folder '{name}'")

        elif cmd == "touch":
            if not args:
                writeln("Usage: touch <name>")
                return
            name = args[0]
            if "." not in name:
                name += ".txt"
            if children is None:
                writeln("Invalid location.")
                return
            if name in children:
                writeln("That already exists.")
                return
            content = 'print("Hello from BotilyOS")' if name.lower().endswith(".py") else ""
            children[name] = {"type": "file", "content": content}
            save_db()
            writeln(f"Created file '{name}'")

        elif cmd == "cat":
            if not args:
                writeln("Usage: cat <file>")
                return
            path = resolve_path(args[0])
            node = get_node_by_path(path)
            if not node or node.get("type") != "file":
                writeln("File not found.")
                return
            writeln(node.get("content", ""))

        elif cmd == "write":
            if len(args) < 2:
                writeln("Usage: write <file> <text>")
                return
            path = resolve_path(args[0])
            node = get_node_by_path(path)
            if not node or node.get("type") != "file":
                writeln("File not found.")
                return
            node["content"] = " ".join(args[1:])
            save_db()
            writeln(f"Wrote to '{path[-1]}'")

        elif cmd == "del":
            if not args:
                writeln("Usage: del <name>")
                return
            name = args[0]
            if children is None or name not in children:
                writeln("Not found.")
                return
            del children[name]
            save_db()
            writeln(f"Deleted '{name}'")

        elif cmd == "clear":
            output.delete("1.0", "end")

        elif cmd == "whoami":
            writeln(logged_in_user or "No user")

        elif cmd == "time":
            writeln(time.strftime("%A, %B %d %Y - %I:%M:%S %p"))

        elif cmd == "apps":
            installed = sorted(os_memory.get("installed_apps", []))
            writeln("Installed apps:")
            for app in installed:
                writeln(f"- {app}")

        elif cmd == "install":
            if not args:
                writeln("Usage: install <AppName>")
                return
            app_name = args[0]
            match = next((name for name in APP_CATALOG if name.lower() == app_name.lower()), None)
            if not match:
                writeln("Unknown app.")
                return
            install_app(match)
            writeln(f"Installed {match}")

        elif cmd == "uninstall":
            if not args:
                writeln("Usage: uninstall <AppName>")
                return
            app_name = args[0]
            match = next((name for name in APP_CATALOG if name.lower() == app_name.lower()), None)
            if not match:
                writeln("Unknown app.")
                return
            uninstall_app(match)
            writeln(f"Uninstall tried for {match}")

        elif cmd == "open":
            if not args:
                writeln("Usage: open <app>")
                return
            name = args[0].lower()
            table = {
                "notes": open_notes,
                "files": open_files,
                "calc": open_calc,
                "snake": open_snake,
                "store": open_app_store,
                "settings": open_settings,
                "about": open_about,
                "terminal": open_terminal,
                "paint": open_paint,
                "clock": open_clock,
                "music": open_music,
                "gallery": open_gallery,
                "tictactoe": open_tictactoe
            }
            if name not in table:
                writeln("Unknown app.")
                return

            needs_install = {
                "terminal": "Terminal",
                "paint": "Paint",
                "clock": "Clock",
                "music": "Music",
                "gallery": "Gallery",
                "tictactoe": "TicTacToe"
            }
            req = needs_install.get(name)
            if req and req not in os_memory.get("installed_apps", []):
                writeln(f"{req} is not installed.")
                return

            table[name]()
            writeln(f"Opened {name}")

        elif cmd == "run":
            if not args:
                writeln("Usage: run <pythonfile.py>")
                return
            path = resolve_path(args[0])
            run_python_by_path(path)
            writeln(f"Running {args[0]}")

        else:
            writeln("Unknown command. Type 'help'.")

    writeln("Botily Terminal")
    writeln("Type 'help' for commands.")
    writeln(f"Logged in as {logged_in_user}")
    writeln("")

    def on_enter(event=None):
        cmd = prompt_var.get()
        prompt_var.set("")
        execute(cmd)

    safe_button(bottom, "Run", on_enter).pack(side="left")
    entry.bind("<Return>", on_enter)
    entry.focus_force()


# =========================================================
# EXTRA APPS
# =========================================================
def open_paint():
    if "Paint" not in os_memory.get("installed_apps", []):
        messagebox.showerror("BotilyOS", "Paint is not installed.")
        return

    win = create_window("Paint", 920, 650)
    body = app_parent(win)

    tk.Label(body, text="Paint", bg=WINDOW_BG, fg="white", font=("Segoe UI", 16, "bold")).pack(pady=6)

    top = tk.Frame(body, bg=WINDOW_BG)
    top.pack(fill="x", padx=10, pady=6)

    color_var = tk.StringVar(value="black")
    size_var = tk.IntVar(value=3)

    for c in ["black", "red", "blue", "green", "purple", "orange"]:
        tk.Radiobutton(
            top, text=c, variable=color_var, value=c,
            bg=WINDOW_BG, fg="white", selectcolor="#222233",
            activebackground=WINDOW_BG, activeforeground="white"
        ).pack(side="left", padx=4)

    tk.Label(top, text="Size", bg=WINDOW_BG, fg="white").pack(side="left", padx=(16, 4))
    tk.Scale(top, from_=1, to=12, orient="horizontal", variable=size_var, bg=WINDOW_BG, fg="white", highlightthickness=0).pack(side="left")

    canvas = tk.Canvas(body, bg="white", width=800, height=500)
    canvas.pack(fill="both", expand=True, padx=10, pady=10)

    last = {"x": None, "y": None}

    def start(event):
        last["x"], last["y"] = event.x, event.y

    def draw(event):
        if last["x"] is not None:
            canvas.create_line(last["x"], last["y"], event.x, event.y, fill=color_var.get(), width=size_var.get(), capstyle="round", smooth=True)
        last["x"], last["y"] = event.x, event.y

    def stop(event):
        last["x"], last["y"] = None, None

    def clear_canvas():
        canvas.delete("all")

    def save_():
        filename = simpledialog.askstring("Save Drawing", "File name:", parent=win)
        if not filename:
            return
        if not filename.lower().endswith(".draw.txt"):
            filename += ".draw.txt"
        os_memory["files"]["Documents"]["children"][filename] = {
            "type": "file",
            "content": "Drawing saved inside Paint (visual canvas state is not exported as image in this version)."
        }
        save_db()
        show_notification("Paint", f"Saved note as {filename}")

    canvas.bind("<Button-1>", start)
    canvas.bind("<B1-Motion>", draw)
    canvas.bind("<ButtonRelease-1>", stop)

    btns = tk.Frame(body, bg=WINDOW_BG)
    btns.pack(fill="x", padx=10, pady=(0, 10))

    safe_button(btns, "Clear", clear_canvas).pack(side="left", padx=4)
    safe_button(btns, "Save Note", save_).pack(side="left", padx=4)


def open_tictactoe():
    if "TicTacToe" not in os_memory.get("installed_apps", []):
        messagebox.showerror("BotilyOS", "TicTacToe is not installed.")
        return

    win = create_window("TicTacToe", 360, 460)
    body = app_parent(win)

    tk.Label(body, text="TicTacToe", bg=WINDOW_BG, fg="white", font=("Segoe UI", 16, "bold")).pack(pady=10)
    status = tk.StringVar(value="X's turn")

    tk.Label(body, textvariable=status, bg=WINDOW_BG, fg="white", font=("Segoe UI", 11)).pack()

    grid = tk.Frame(body, bg=WINDOW_BG)
    grid.pack(pady=16)

    board = [[""] * 3 for _ in range(3)]
    turn = {"value": "X"}
    buttons = []

    def check_winner():
        lines = []
        for i in range(3):
            lines.append(board[i])
            lines.append([board[0][i], board[1][i], board[2][i]])
        lines.append([board[0][0], board[1][1], board[2][2]])
        lines.append([board[0][2], board[1][1], board[2][0]])

        for line in lines:
            if line[0] and line.count(line[0]) == 3:
                return line[0]

        if all(board[r][c] for r in range(3) for c in range(3)):
            return "Draw"
        return None

    def click_cell(r, c):
        if board[r][c]:
            return
        board[r][c] = turn["value"]
        buttons[r][c].config(text=turn["value"])
        winner = check_winner()
        if winner:
            if winner == "Draw":
                status.set("Draw")
            else:
                status.set(f"{winner} wins")
                show_notification("TicTacToe", f"{winner} wins!")
            return
        turn["value"] = "O" if turn["value"] == "X" else "X"
        status.set(f"{turn['value']}'s turn")

    def reset():
        for r in range(3):
            for c in range(3):
                board[r][c] = ""
                buttons[r][c].config(text="")
        turn["value"] = "X"
        status.set("X's turn")

    for r in range(3):
        row = []
        for c in range(3):
            btn = tk.Button(grid, text="", width=6, height=3, font=("Segoe UI", 20), bg="white", command=lambda rr=r, cc=c: click_cell(rr, cc))
            btn.grid(row=r, column=c, padx=3, pady=3)
            row.append(btn)
        buttons.append(row)

    safe_button(body, "Reset", reset).pack(pady=10)


def open_clock():
    if "Clock" not in os_memory.get("installed_apps", []):
        messagebox.showerror("BotilyOS", "Clock is not installed.")
        return

    win = create_window("Clock", 420, 320)
    body = app_parent(win)

    tk.Label(body, text="Clock", bg=WINDOW_BG, fg="white", font=("Segoe UI", 18, "bold")).pack(pady=16)
    time_var = tk.StringVar(value="")
    date_var = tk.StringVar(value="")

    tk.Label(body, textvariable=time_var, bg=WINDOW_BG, fg="white", font=("Segoe UI", 28, "bold")).pack(pady=8)
    tk.Label(body, textvariable=date_var, bg=WINDOW_BG, fg="#d7d7d7", font=("Segoe UI", 12)).pack(pady=4)

    alarm_frame = tk.Frame(body, bg=WINDOW_BG)
    alarm_frame.pack(pady=20)

    tk.Label(alarm_frame, text="Alarm (HH:MM 24h)", bg=WINDOW_BG, fg="white").pack()
    alarm_entry = tk.Entry(alarm_frame, font=("Segoe UI", 12))
    alarm_entry.pack(pady=6)
    add_entry_context_menu(alarm_entry)

    alarm_state = {"value": None, "fired": False}

    def set_alarm():
        txt = alarm_entry.get().strip()
        alarm_state["value"] = txt if txt else None
        alarm_state["fired"] = False
        if txt:
            show_notification("Clock", f"Alarm set for {txt}")

    safe_button(alarm_frame, "Set Alarm", set_alarm).pack()

    def tick():
        if not win.winfo_exists():
            return
        now = time.localtime()
        time_var.set(time.strftime("%I:%M:%S %p"))
        date_var.set(time.strftime("%A, %B %d %Y"))

        if alarm_state["value"]:
            now_hm = time.strftime("%H:%M")
            if now_hm == alarm_state["value"] and not alarm_state["fired"]:
                alarm_state["fired"] = True
                play_sound("notify")
                show_notification("Clock", f"Alarm: {alarm_state['value']}")
        win.after(500, tick)

    tick()


# =========================================================
# MUSIC
# =========================================================
def open_music():
    win = create_window("Music Player", 620, 460)
    body = app_parent(win)

    tk.Label(
        body,
        text="Music Player",
        bg=WINDOW_BG,
        fg="white",
        font=("Segoe UI", 14, "bold")
    ).pack(pady=10)

    info_var = tk.StringVar(value="Music folder: ./music")
    tk.Label(
        body,
        textvariable=info_var,
        bg=WINDOW_BG,
        fg="#d7d7d7",
        font=("Segoe UI", 10)
    ).pack()

    music_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")

    list_frame = tk.Frame(body, bg=WINDOW_BG)
    list_frame.pack(fill="both", expand=True, padx=10, pady=10)

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")

    music_list = tk.Listbox(
        list_frame,
        bg="white",
        fg="black",
        font=("Consolas", 11),
        yscrollcommand=scrollbar.set
    )
    music_list.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=music_list.yview)

    status_label = tk.Label(
        body,
        text="Ready",
        bg=WINDOW_BG,
        fg="#9fe89f",
        font=("Segoe UI", 10, "bold")
    )
    status_label.pack(pady=(0, 8))

    current_song = {"path": None, "name": None}
    pygame_ready = {"ok": False}

    def init_audio():
        if pygame is None:
            status_label.config(text="pygame not installed")
            return False

        if pygame_ready["ok"]:
            return True

        try:
            pygame.mixer.init()
            pygame_ready["ok"] = True
            return True
        except Exception as e:
            status_label.config(text=f"Audio init failed: {e}")
            return False

    def scan_music():
        music_list.delete(0, "end")

        if not os.path.isdir(music_folder):
            info_var.set("No 'music' folder found next to this program.")
            return

        allowed_exts = (".wav", ".mp3", ".ogg")
        songs = []

        try:
            for name in sorted(os.listdir(music_folder), key=str.lower):
                full = os.path.join(music_folder, name)
                if os.path.isfile(full) and name.lower().endswith(allowed_exts):
                    songs.append(name)
        except Exception as e:
            info_var.set(f"Could not read music folder: {e}")
            return

        if not songs:
            info_var.set("Music folder found, but no supported audio files were detected.")
            return

        for song in songs:
            music_list.insert("end", song)

        info_var.set(f"Found {len(songs)} song(s) in: {music_folder}")
        status_label.config(text="Ready")

    def get_selected_song():
        sel = music_list.curselection()
        if not sel:
            return None, None
        filename = music_list.get(sel[0])
        return filename, os.path.join(music_folder, filename)

    def play_selected():
        filename, full_path = get_selected_song()
        if not filename:
            show_notification("Music", "Select a song first.")
            return

        if not init_audio():
            show_notification("Music", "pygame is required for mp3 playback.")
            return

        try:
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.play()
            current_song["path"] = full_path
            current_song["name"] = filename
            status_label.config(text=f"Playing: {filename}")
            info_var.set(f"Now playing: {filename}")
            show_notification("Music", f"Playing {filename}")
        except Exception as e:
            play_sound("error")
            status_label.config(text="Play failed")
            info_var.set(f"Could not play: {filename}")
            show_notification("Music Error", str(e))

    def stop_music():
        if pygame is not None and pygame_ready["ok"]:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        status_label.config(text="Stopped")
        info_var.set("Playback stopped")

    def pause_music():
        if pygame is None or not pygame_ready["ok"]:
            return
        try:
            pygame.mixer.music.pause()
            status_label.config(text="Paused")
            info_var.set("Playback paused")
        except Exception as e:
            show_notification("Music Error", str(e))

    def resume_music():
        if pygame is None or not pygame_ready["ok"]:
            return
        try:
            pygame.mixer.music.unpause()
            if current_song["name"]:
                status_label.config(text=f"Playing: {current_song['name']}")
                info_var.set(f"Resumed: {current_song['name']}")
            else:
                status_label.config(text="Resumed")
        except Exception as e:
            show_notification("Music Error", str(e))

    def refresh_music():
        scan_music()
        show_notification("Music", "Music list refreshed.")

    def set_volume(value):
        if pygame is None or not pygame_ready["ok"]:
            return
        try:
            pygame.mixer.music.set_volume(float(value) / 100.0)
        except Exception:
            pass

    controls = tk.Frame(body, bg=WINDOW_BG)
    controls.pack(pady=(0, 8))

    safe_button(controls, "Play", play_selected).pack(side="left", padx=5)
    safe_button(controls, "Pause", pause_music).pack(side="left", padx=5)
    safe_button(controls, "Resume", resume_music).pack(side="left", padx=5)
    safe_button(controls, "Stop", stop_music, bg="#7a1f1f").pack(side="left", padx=5)
    safe_button(controls, "Refresh", refresh_music).pack(side="left", padx=5)

    volume_row = tk.Frame(body, bg=WINDOW_BG)
    volume_row.pack(fill="x", padx=12, pady=(0, 10))

    tk.Label(
        volume_row,
        text="Volume",
        bg=WINDOW_BG,
        fg="white",
        font=("Segoe UI", 10)
    ).pack(side="left", padx=(0, 8))

    volume_slider = tk.Scale(
        volume_row,
        from_=0,
        to=100,
        orient="horizontal",
        bg=WINDOW_BG,
        fg="white",
        highlightthickness=0,
        troughcolor="#1f1f2f",
        command=set_volume
    )
    volume_slider.set(70)
    volume_slider.pack(side="left", fill="x", expand=True)

    music_list.bind("<Double-Button-1>", lambda e: play_selected())

    def on_close_music():
        try:
            if pygame is not None and pygame_ready["ok"]:
                pygame.mixer.music.stop()
        except Exception:
            pass
        win.destroy()

    if hasattr(win, "btns"):
        for child in win.btns.winfo_children():
            try:
                if child.cget("text") == "✕":
                    child.config(command=on_close_music)
                    break
            except Exception:
                pass

    scan_music()

def normalize_gallery_items():
    raw = os_memory.get("gallery_items", [])
    normalized = []

    for item in raw:
        if isinstance(item, dict):
            item_path = str(item.get("path", "")).strip()
            if not item_path:
                continue
            normalized.append({
                "path": item_path,
                "label": str(item.get("label", os.path.basename(item_path) or "Image")),
                "source": str(item.get("source", "imported")),
                "added_at": float(item.get("added_at", time.time()))
            })
        elif isinstance(item, str):
            item_path = item.strip()
            if not item_path:
                continue
            normalized.append({
                "path": item_path,
                "label": os.path.basename(item_path) or "Image",
                "source": "imported",
                "added_at": time.time()
            })

    normalized = normalized[:200]
    os_memory["gallery_items"] = normalized
    return normalized


def enforce_gallery_limit():
    items = normalize_gallery_items()
    if len(items) > 200:
        os_memory["gallery_items"] = items[-200:]
        save_db()
    return os_memory.get("gallery_items", [])


def add_gallery_image(path, source="imported"):
    path = str(path).strip()
    if not path:
        return False, "Invalid image path."

    items = normalize_gallery_items()

    if not os.path.exists(path):
        return False, "Image path does not exist."

    valid_exts = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
    if not path.lower().endswith(valid_exts):
        return False, "That file is not a supported image."

    items.append({
        "path": path,
        "label": os.path.basename(path) or "Image",
        "source": source,
        "added_at": time.time()
    })

    if len(items) > 200:
        items[:] = items[-200:]

    os_memory["gallery_items"] = items
    save_db()
    return True, f"Added image: {os.path.basename(path)}"


def load_image_preview(image_path, max_size):
    try:
        img = Image.open(image_path)
        img.thumbnail(max_size)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def open_image_viewer(start_index=0):
    items = normalize_gallery_items()
    if not items:
        messagebox.showinfo("Gallery", "There are no images to view yet.")
        return

    if start_index < 0 or start_index >= len(items):
        start_index = 0

    win = create_window("Image Viewer", 980, 700)
    body = app_parent(win)

    top = tk.Frame(body, bg=WINDOW_BG)
    top.pack(fill="x", padx=10, pady=10)

    title_var = tk.StringVar(value="")
    info_var = tk.StringVar(value="")

    tk.Label(top, textvariable=title_var, bg=WINDOW_BG, fg="white", font=("Segoe UI", 13, "bold")).pack(anchor="w")
    tk.Label(top, textvariable=info_var, bg=WINDOW_BG, fg="#d7d7d7", font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))

    viewer_frame = tk.Frame(body, bg="#111111")
    viewer_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    image_label = tk.Label(viewer_frame, bg="#111111")
    image_label.pack(fill="both", expand=True)

    nav = tk.Frame(body, bg=WINDOW_BG)
    nav.pack(fill="x", padx=10, pady=(0, 10))

    state = {"index": start_index, "photo": None}

    def render():
        items_local = normalize_gallery_items()
        if not items_local:
            title_var.set("No images")
            info_var.set("")
            image_label.config(image="", text="No images left.", fg="white", font=("Segoe UI", 16))
            return

        if state["index"] >= len(items_local):
            state["index"] = len(items_local) - 1
        if state["index"] < 0:
            state["index"] = 0

        item = items_local[state["index"]]
        image_path = item["path"]

        title_var.set(f"{item.get('label', os.path.basename(image_path))} ({state['index'] + 1}/{len(items_local)})")
        info_var.set(image_path)

        preview = load_image_preview(image_path, (900, 560))
        if preview is None:
            state["photo"] = None
            image_label.config(
                image="",
                text="Could not load this image.\nThe file may have moved or been deleted.",
                fg="white",
                font=("Segoe UI", 14),
                justify="center"
            )
        else:
            state["photo"] = preview
            image_label.config(image=preview, text="")

    def prev_image():
        state["index"] -= 1
        if state["index"] < 0:
            state["index"] = len(normalize_gallery_items()) - 1
        render()

    def next_image():
        state["index"] += 1
        if state["index"] >= len(normalize_gallery_items()):
            state["index"] = 0
        render()

    safe_button(nav, "◀ Previous", prev_image).pack(side="left", padx=4)
    safe_button(nav, "Next ▶", next_image).pack(side="left", padx=4)
    safe_button(nav, "Close", win.destroy, bg="#7a1f1f").pack(side="right", padx=4)

    render()


def open_camera_capture(refresh_callback=None):
    if cv2 is None:
        messagebox.showerror("Camera", "OpenCV is not installed. Run: pip install opencv-python")
        play_sound("error")
        return

    camera_win = create_window("Camera", 900, 700)
    body = app_parent(camera_win)

    tk.Label(body, text="Camera", bg=WINDOW_BG, fg="white", font=("Segoe UI", 16, "bold")).pack(pady=10)
    tk.Label(body, text="Click Capture to save a photo into Gallery and Photos.", bg=WINDOW_BG, fg="#d7d7d7", font=("Segoe UI", 10)).pack()

    preview_frame = tk.Frame(body, bg="#101010")
    preview_frame.pack(fill="both", expand=True, padx=10, pady=10)

    preview_label = tk.Label(preview_frame, bg="#101010")
    preview_label.pack(fill="both", expand=True)

    status_var = tk.StringVar(value="Opening camera...")
    tk.Label(body, textvariable=status_var, bg=WINDOW_BG, fg="#9fe89f", font=("Segoe UI", 10)).pack(pady=(0, 8))

    controls = tk.Frame(body, bg=WINDOW_BG)
    controls.pack(fill="x", padx=10, pady=(0, 10))

    cap = cv2.VideoCapture(0)
    camera_state = {"cap": cap, "frame": None, "photo": None, "running": True}

    if not cap.isOpened():
        camera_win.destroy()
        messagebox.showerror("Camera", "Camera not found or permission denied.")
        play_sound("error")
        return

    photos_root = os.path.join(os.getcwd(), "BotilyOS_Photos")
    os.makedirs(photos_root, exist_ok=True)

    photos_folder = os_memory["files"].setdefault("Photos", {"type": "folder", "children": {}})
    if photos_folder.get("type") != "folder":
        os_memory["files"]["Photos"] = {"type": "folder", "children": {}}
        photos_folder = os_memory["files"]["Photos"]

    def update_frame():
        if not camera_state["running"] or not camera_win.winfo_exists():
            return

        ret, frame = cap.read()
        if ret:
            camera_state["frame"] = frame
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                img.thumbnail((820, 520))
                photo = ImageTk.PhotoImage(img)
                camera_state["photo"] = photo
                preview_label.config(image=photo, text="")
                status_var.set("Camera ready")
            except Exception:
                preview_label.config(image="", text="Camera preview failed.", fg="white")
                status_var.set("Preview error")
        else:
            preview_label.config(image="", text="No camera frame.", fg="white")
            status_var.set("Camera read failed")

        camera_win.after(40, update_frame)

    def capture_photo():
        frame = camera_state.get("frame")
        if frame is None:
            messagebox.showerror("Camera", "No camera frame available yet.")
            play_sound("error")
            return

        timestamp = int(time.time())
        filename = f"photo_{timestamp}.png"
        filepath = os.path.join(photos_root, filename)

        try:
            cv2.imwrite(filepath, frame)
        except Exception:
            messagebox.showerror("Camera", "Failed to save image.")
            play_sound("error")
            return

        photos_folder["children"][filename] = {
            "type": "file",
            "content": filepath
        }

        ok, message = add_gallery_image(filepath, source="camera")
        if not ok:
            messagebox.showerror("Camera", message)
            play_sound("error")
            return

        if callable(refresh_callback):
            refresh_callback()

        status_var.set(f"Saved {filename}")
        show_notification("Camera", f"Photo saved: {filename}")

    def close_camera():
        camera_state["running"] = False
        try:
            cap.release()
        except Exception:
            pass
        if camera_win.winfo_exists():
            camera_win.destroy()

    safe_button(controls, "Capture 📸", capture_photo).pack(side="left", padx=4)
    safe_button(controls, "Close", close_camera, bg="#7a1f1f").pack(side="left", padx=4)

    camera_win.protocol("WM_DELETE_WINDOW", close_camera)
    update_frame()


def take_photo(refresh_callback=None):
    open_camera_capture(refresh_callback=refresh_callback)


def open_gallery():
    if "Gallery" not in os_memory.get("installed_apps", []):
        messagebox.showerror("BotilyOS", "Gallery is not installed.")
        return

    normalize_gallery_items()

    win = create_window("Gallery", 980, 620)
    body = app_parent(win)

    tk.Label(body, text="Gallery", bg=WINDOW_BG, fg="white", font=("Segoe UI", 16, "bold")).pack(pady=10)

    info_var = tk.StringVar(value=f"0 / 200 images")
    tk.Label(body, textvariable=info_var, bg=WINDOW_BG, fg="#d7d7d7", font=("Segoe UI", 10)).pack()

    top = tk.Frame(body, bg=WINDOW_BG)
    top.pack(fill="x", padx=10, pady=8)

    content = tk.Frame(body, bg=WINDOW_BG)
    content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    left = tk.Frame(content, bg=WINDOW_BG, width=340)
    left.pack(side="left", fill="y")

    right = tk.Frame(content, bg="#1a1a28")
    right.pack(side="right", fill="both", expand=True, padx=(10, 0))

    lb = tk.Listbox(left, font=("Segoe UI", 11), bg="white", fg="black")
    lb.pack(fill="both", expand=True)

    preview_title = tk.StringVar(value="No image selected")
    tk.Label(right, textvariable=preview_title, bg="#1a1a28", fg="white", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 4))

    image_holder = tk.Label(right, bg="#111111")
    image_holder.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    preview_text = tk.Text(right, height=6, bg="#f5f5f5", fg="black", font=("Consolas", 10))
    preview_text.pack(fill="x", padx=12, pady=(0, 12))
    add_text_context_menu(preview_text)

    gallery_state = {"preview_photo": None}

    def get_items():
        return normalize_gallery_items()

    def refresh():
        items = get_items()
        lb.delete(0, "end")
        for item in items:
            source = item.get("source", "imported")
            lb.insert("end", f"{item.get('label', 'Image')}   [{source}]")
        info_var.set(f"{len(items)} / 200 images")

    def import_images():
        paths = filedialog.askopenfilenames(
            title="Import images",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("All files", "*.*")]
        )
        if not paths:
            return

        added = 0
        last_message = ""
        for path in paths:
            ok, message = add_gallery_image(path, source="imported")
            if ok:
                added += 1
            last_message = message

        refresh()
        if added:
            show_notification("Gallery", f"Imported {added} image(s).")
        elif last_message:
            messagebox.showerror("Gallery", last_message)
            play_sound("error")

    def selected_index():
        sel = lb.curselection()
        if not sel:
            return None
        return sel[0]

    def show_selected(event=None):
        preview_text.delete("1.0", "end")
        idx = selected_index()
        items = get_items()

        if idx is None or idx >= len(items):
            preview_title.set("No image selected")
            image_holder.config(image="", text="", fg="white")
            gallery_state["preview_photo"] = None
            return

        item = items[idx]
        image_path = item["path"]

        preview_title.set(item.get("label", os.path.basename(image_path)))
        preview_text.insert(
            "1.0",
            f"Path: {image_path}\n"
            f"Source: {item.get('source', 'imported')}\n"
            f"Added: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item.get('added_at', time.time())))}\n"
        )

        preview = load_image_preview(image_path, (560, 360))
        if preview is None:
            gallery_state["preview_photo"] = None
            image_holder.config(
                image="",
                text="Could not load this image.\nIt may have been moved or deleted.",
                fg="white",
                font=("Segoe UI", 13),
                justify="center"
            )
        else:
            gallery_state["preview_photo"] = preview
            image_holder.config(image=preview, text="")

    def open_selected_viewer():
        idx = selected_index()
        if idx is None:
            messagebox.showinfo("Gallery", "Select an image first.")
            return
        open_image_viewer(idx)

    def remove_selected():
        idx = selected_index()
        items = get_items()
        if idx is None or idx >= len(items):
            return
        del items[idx]
        os_memory["gallery_items"] = items
        save_db()
        refresh()
        preview_text.delete("1.0", "end")
        image_holder.config(image="", text="", fg="white")
        gallery_state["preview_photo"] = None

    safe_button(top, "Import Images", import_images).pack(side="left", padx=4, pady=6)
    safe_button(top, "Open Viewer", open_selected_viewer).pack(side="left", padx=4, pady=6)
    safe_button(top, "Take Photo 📸", lambda: open_camera_capture(refresh)).pack(side="left", padx=4, pady=6)
    safe_button(top, "Remove", remove_selected, bg="#7a1f1f").pack(side="left", padx=4, pady=6)

    lb.bind("<<ListboxSelect>>", show_selected)
    lb.bind("<Double-Button-1>", lambda e: open_selected_viewer())

    refresh()


def open_about():
    win = create_window("About", 520, 420)
    body = app_parent(win)

    tk.Label(body, text="BotilyOS", bg=WINDOW_BG, fg="white", font=("Segoe UI", 18, "bold")).pack(pady=15)

    tk.Label(
        body,
        text=(
            "Features:\n"
            "- Login and user profiles\n"
            "- Notes autosave + Save As to  files\n"
            "- Files app with folders and zips\n"
            "- Python runner\n"
            "- Botily AI with saved memory\n"
            "- App Store / installer\n"
            "- Terminal app\n"
            "- Optional system sounds\n"
            "- Draggable windows\n"
            "- Minimize + fullscreen + notifications"
        ),
        bg=WINDOW_BG,
        fg="white",
        font=("Segoe UI", 11),
        justify="center"
    ).pack(pady=10)


def open_settings():
    win = create_window("Settings", 520, 420)
    body = app_parent(win)

    tk.Label(body, text="Settings", bg=WINDOW_BG, fg="white", font=("Segoe UI", 16, "bold")).pack(pady=10)

    safe_button(body, "Blue Wallpaper", lambda: set_wallpaper("#203a5c"), bg="#203a5c").pack(pady=8)
    safe_button(body, "Purple Wallpaper", lambda: set_wallpaper("#3a2352"), bg="#3a2352").pack(pady=8)
    safe_button(body, "Dark Wallpaper", lambda: set_wallpaper("#1e1e2f"), bg="#1e1e2f").pack(pady=8)

    sound_frame = tk.Frame(body, bg=WINDOW_BG)
    sound_frame.pack(pady=12)

    tk.Checkbutton(
        sound_frame,
        text="Enable Sounds",
        variable=sound_var,
        bg=WINDOW_BG,
        fg="white",
        selectcolor="#222233",
        activebackground=WINDOW_BG,
        activeforeground="white",
        command=save_db
    ).pack()

    safe_button(body, "Logout", logout, bg="#6b4b18").pack(pady=6)


# =========================================================
# APP LAUNCHER TABLE
# =========================================================
app_launchers.update({
    "Terminal": open_terminal,
    "Paint": open_paint,
    "TicTacToe": open_tictactoe,
    "Clock": open_clock,
    "Music": open_music,
    "Gallery": open_gallery
})


# =========================================================
# STARTUP
# =========================================================
update_clock()
update_battery()
keep_fullscreen()

root.bind("<Escape>", lambda e: "break")
show_login_screen()
# ============================================
# FORCE START SYSTEM
# ============================================

def force_start():
    global db

    # If no users exist → create default
    if not db.get("users"):
        db["users"]["Player"] = {
            "password": "",
            "data": normalize_user_data({})
        }
        db["current_user"] = "Player"

    # Pick current user or fallback
    user = db.get("current_user")
    if not user or user not in db["users"]:
        user = list(db["users"].keys())[0]

    # FORCE load user
    load_user(user)

    # BUILD UI immediately
    build_desktop_for_user()

# Run it ONCE when program starts
root.after(0, force_start)

root.mainloop()
