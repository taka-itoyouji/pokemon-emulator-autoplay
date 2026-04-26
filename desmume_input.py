# action/desmume_input.py
# DeSmuME への入力送信（キー操作・タッチ操作）
# Windows / Linux 対応

import sys
import time
import subprocess
import threading
from typing import Optional, Tuple
from window_utils import WindowRect

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0  # レイテンシ削減
except ImportError:
    raise RuntimeError("pyautogui が必要です: pip install pyautogui")


class DesmumeInput:
    """
    DeSmuME への入力を送信するクラス。

    タッチ操作: DS 下画面座標 (0-255, 0-191) を受け取り、
               ウィンドウ上の実座標に変換してクリックする。
    キー操作:   pyautogui.press / keyDown / keyUp を使用。
    """

    DS_SCREEN_W = 256
    DS_SCREEN_H = 192

    def __init__(self, window: WindowRect, title_bar_height: int = 30):
        self.window = window
        self.title_bar_height = title_bar_height
        self.is_windows = sys.platform == "win32"
        self._mouse_lock = threading.Lock()

    def update_window(self, window: WindowRect):
        self.window = window

    # ---- タッチ操作 ----

    def touch(self, ds_x: int, ds_y: int, duration: float = 0.05):
        """
        DS 下画面をタッチする。
        ds_x, ds_y: DS 座標系 (0-255, 0-191)
        duration:   タッチ持続時間 (秒)
        """
        wx, wy = self._ds_to_window_coords(ds_x, ds_y)
        with self._mouse_lock:
            self._focus()
            self._with_preserved_cursor(lambda: self._touch_at(wx, wy, duration))

    def drag(self, ds_x1: int, ds_y1: int,
             ds_x2: int, ds_y2: int, duration: float = 0.3):
        """DS 下画面上でドラッグ操作を行う。"""
        wx1, wy1 = self._ds_to_window_coords(ds_x1, ds_y1)
        wx2, wy2 = self._ds_to_window_coords(ds_x2, ds_y2)
        with self._mouse_lock:
            self._focus()
            self._with_preserved_cursor(lambda: self._drag_between(wx1, wy1, wx2, wy2, duration))

    # ---- キー操作 ----

    def press_key(self, key: str, duration: float = 0.05):
        """キーを押して離す（一時的な押下）。"""
        self._focus()
        if self.is_windows:
            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)
        else:
            self._xdotool_key(key)

    def hold_key(self, key: str):
        """キーを押したままにする。"""
        self._focus()
        pyautogui.keyDown(key)

    def release_key(self, key: str):
        """押したままのキーを離す。"""
        pyautogui.keyUp(key)

    # ---- 内部メソッド ----

    def _ds_to_window_coords(self, ds_x: int, ds_y: int) -> Tuple[int, int]:
        """
        DS 下画面座標 → スクリーン上の絶対座標に変換。
        DeSmuME ウィンドウの描画領域内で、下半分（タッチ画面）に対応する領域を計算する。
        """
        w = self.window
        tb = self.title_bar_height

        # ウィンドウの描画領域（タイトルバー除く）
        draw_left   = w.x
        draw_top    = w.y + tb
        draw_width  = w.width
        draw_height = w.height - tb

        # 上下2画面があるので、下半分がタッチ画面
        touch_top    = draw_top + draw_height // 2
        touch_height = draw_height // 2

        # DS 座標 → ウィンドウ内の比率 → 実ピクセル
        scale_x = draw_width  / self.DS_SCREEN_W
        scale_y = touch_height / self.DS_SCREEN_H

        screen_x = int(draw_left + ds_x * scale_x)
        screen_y = int(touch_top  + ds_y * scale_y)
        return screen_x, screen_y

    def _focus(self):
        """DeSmuME ウィンドウをフォアグラウンドにする（Windows のみ）。"""
        if self.is_windows:
            try:
                import win32gui
                def cb(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd):
                        if "desmume" in win32gui.GetWindowText(hwnd).lower():
                            win32gui.SetForegroundWindow(hwnd)
                win32gui.EnumWindows(cb, None)
            except Exception:
                pass  # 失敗しても続行

    def _with_preserved_cursor(self, operation):
        """入力後にユーザーカーソルを元位置へ戻す。"""
        prev_x, prev_y = pyautogui.position()
        try:
            operation()
        finally:
            # 復元は高速で行い、ユーザー操作への影響を最小化する。
            pyautogui.moveTo(prev_x, prev_y, duration=0)

    def _touch_at(self, wx: int, wy: int, duration: float):
        pyautogui.mouseDown(wx, wy, button="left")
        time.sleep(duration)
        pyautogui.mouseUp(wx, wy, button="left")

    def _drag_between(self, wx1: int, wy1: int, wx2: int, wy2: int, duration: float):
        pyautogui.mouseDown(wx1, wy1, button="left")
        pyautogui.moveTo(wx2, wy2, duration=duration)
        pyautogui.mouseUp(button="left")

    def _xdotool_key(self, key: str):
        """Linux 環境で xdotool を使ってキー送信する。"""
        subprocess.run(["xdotool", "key", key], check=False)
