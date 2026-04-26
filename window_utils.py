# utils/window_utils.py
# DeSmuME ウィンドウの検索・位置取得（Windows / Linux 対応）

import sys
import subprocess
from dataclasses import dataclass

@dataclass
class WindowRect:
    x: int
    y: int
    width: int
    height: int


def find_desmume_window(title_keyword: str) -> WindowRect:
    """DeSmuME ウィンドウを検索してスクリーン上の矩形を返す。"""
    if sys.platform == "win32":
        return _find_window_windows(title_keyword)
    else:
        return _find_window_linux(title_keyword)


# ---- Windows ----
def _find_window_windows(title_keyword: str) -> WindowRect:
    try:
        import win32gui
    except ImportError:
        raise RuntimeError("pywin32 が必要です: pip install pywin32")

    results = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title_keyword.lower() in title.lower():
                rect = win32gui.GetWindowRect(hwnd)  # (left, top, right, bottom)
                results.append((hwnd, rect))

    win32gui.EnumWindows(callback, None)

    if not results:
        raise RuntimeError(f"ウィンドウが見つかりません: '{title_keyword}'")

    _, (left, top, right, bottom) = results[0]
    return WindowRect(x=left, y=top, width=right - left, height=bottom - top)


def focus_window_windows(title_keyword: str):
    """指定ウィンドウをフォアグラウンドに持ってくる (Windows)。"""
    try:
        import win32gui
        import win32con

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                if title_keyword.lower() in win32gui.GetWindowText(hwnd).lower():
                    win32gui.SetForegroundWindow(hwnd)

        win32gui.EnumWindows(callback, None)
    except ImportError:
        pass


# ---- Linux ----
def _find_window_linux(title_keyword: str) -> WindowRect:
    """xdotool を使ってウィンドウを検索する。"""
    try:
        result = subprocess.check_output(
            ["xdotool", "search", "--name", title_keyword],
            text=True
        ).strip()
        wid = result.splitlines()[0]
        geo = subprocess.check_output(
            ["xdotool", "getwindowgeometry", "--shell", wid],
            text=True
        )
        info = {}
        for line in geo.strip().splitlines():
            k, v = line.split("=")
            info[k.strip()] = int(v.strip())
        return WindowRect(x=info["X"], y=info["Y"],
                          width=info["WIDTH"], height=info["HEIGHT"])
    except FileNotFoundError:
        raise RuntimeError("xdotool が必要です: sudo apt install xdotool")
    except (subprocess.CalledProcessError, KeyError, ValueError) as e:
        raise RuntimeError(f"ウィンドウ検索に失敗しました: {e}")
