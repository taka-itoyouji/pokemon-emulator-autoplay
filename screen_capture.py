# capture/screen_capture.py
# DeSmuME の画面をキャプチャし、上下画面に分割して返す

import numpy as np
import mss
import mss.tools
from dataclasses import dataclass
from typing import Optional
from window_utils import WindowRect


@dataclass
class DSFrame:
    """DS の1フレーム分のデータ。"""
    top_screen: np.ndarray     # 上画面 (H, W, 3) RGB
    bottom_screen: np.ndarray  # 下画面/タッチ画面 (H, W, 3) RGB
    raw: np.ndarray            # ウィンドウ全体 RGB


class ScreenCapture:
    """mss を使って DeSmuME ウィンドウをキャプチャする。"""

    def __init__(self, window: WindowRect, title_bar_height: int = 30):
        """
        Parameters
        ----------
        window           : DeSmuME ウィンドウの位置・サイズ
        title_bar_height : OSのタイトルバーの高さ（ピクセル）
                           キャプチャ領域から除外するために使用
        """
        self.window = window
        self.title_bar_height = title_bar_height
        self.sct = mss.mss()

        # キャプチャ対象領域（タイトルバーを除く）
        self.region = {
            "left":   window.x,
            "top":    window.y + title_bar_height,
            "width":  window.width,
            "height": window.height - title_bar_height,
        }

    def capture(self) -> DSFrame:
        """現在のフレームを取得して DSFrame を返す。"""
        shot = self.sct.grab(self.region)
        # BGRA → RGB
        raw = np.array(shot)[:, :, :3][:, :, ::-1].copy()

        top, bottom = self._split_screens(raw)
        return DSFrame(top_screen=top, bottom_screen=bottom, raw=raw)

    def _split_screens(self, img: np.ndarray):
        """
        DeSmuME の描画領域を上下2画面に分割する。
        ウィンドウサイズが 1x の場合: 256x192 × 2 = 256x384
        ウィンドウサイズが 2x の場合: 512x384 × 2 = 512x768
        縦方向の中央で分割する。
        """
        h = img.shape[0]
        mid = h // 2
        top = img[:mid, :, :]
        bottom = img[mid:, :, :]
        return top, bottom

    def update_window(self, window: WindowRect, title_bar_height: Optional[int] = None):
        """ウィンドウ位置が変わった場合に更新する。"""
        self.window = window
        if title_bar_height is not None:
            self.title_bar_height = title_bar_height
        self.region = {
            "left":   window.x,
            "top":    window.y + self.title_bar_height,
            "width":  window.width,
            "height": window.height - self.title_bar_height,
        }

    def close(self):
        self.sct.close()
