# recognition/state_recognizer.py
# DS 画面の状態を判定する（シーン分類・テキスト検出など）

import os
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Tuple

try:
    import cv2
except ImportError:
    raise RuntimeError("opencv-python が必要です: pip install opencv-python")


class Scene(Enum):
    UNKNOWN    = auto()
    FIELD      = auto()   # フィールド（歩き回っている）
    BATTLE     = auto()   # バトル画面
    MENU       = auto()   # メニュー画面
    DIALOG     = auto()   # テキスト送り待ち
    TITLE      = auto()   # タイトル画面


@dataclass
class GameState:
    scene: Scene = Scene.UNKNOWN
    top_screen: Optional[np.ndarray] = None
    bottom_screen: Optional[np.ndarray] = None
    extra: Dict = field(default_factory=dict)


class StateRecognizer:
    """
    テンプレートマッチングによる簡易シーン判定クラス。

    使い方:
        recognizer = StateRecognizer()
        recognizer.load_template(Scene.BATTLE, "templates/battle.png")
        state = recognizer.recognize(frame)
    """

    def __init__(self, match_threshold: float = 0.8):
        self.match_threshold = match_threshold
        # {Scene: (template_img, search_region)}
        # search_region: (x, y, w, h) None=全体
        self._templates: Dict[Scene, Tuple[np.ndarray, Optional[Tuple]]] = {}

    def load_template(self,
                      scene: Scene,
                      template_path: str,
                      search_region: Optional[Tuple[int, int, int, int]] = None):
        """
        テンプレート画像を読み込む。
        search_region: (x, y, w, h) - 画面内の探索領域（None で全体）
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"テンプレートが見つかりません: {template_path}")
        tmpl = cv2.imread(template_path, cv2.IMREAD_COLOR)
        tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGR2RGB)
        self._templates[scene] = (tmpl, search_region)

    def recognize(self, frame) -> GameState:
        """
        DSFrame を受け取り GameState を返す。
        テンプレートが登録されていなければ UNKNOWN を返す。
        """
        from screen_capture import DSFrame

        if isinstance(frame, DSFrame):
            top    = frame.top_screen
            bottom = frame.bottom_screen
        else:
            top = bottom = frame

        state = GameState(scene=Scene.UNKNOWN,
                          top_screen=top, bottom_screen=bottom)

        if not self._templates:
            return state

        # 下画面（タッチ画面）を基準にシーン判定
        target = bottom

        best_scene = Scene.UNKNOWN
        best_score = 0.0

        for scene, (tmpl, region) in self._templates.items():
            search_img = self._crop(target, region)
            score = self._match(search_img, tmpl)
            if score > best_score:
                best_score = score
                best_scene = scene

        if best_score >= self.match_threshold:
            state.scene = best_scene
            state.extra["match_score"] = best_score

        return state

    # ---- ピクセルサンプリングによる簡易判定（テンプレートなしでも使える）----

    @staticmethod
    def sample_pixel(img: np.ndarray, x: int, y: int) -> Tuple[int, int, int]:
        """指定座標の RGB 値を返す。"""
        return tuple(img[y, x])

    @staticmethod
    def is_dark_screen(img: np.ndarray, threshold: int = 20) -> bool:
        """画面全体が暗い（黒）かどうかを判定。"""
        return img.mean() < threshold

    @staticmethod
    def has_text_box(bottom_screen: np.ndarray) -> bool:
        """
        下画面の下部に白いテキストボックスがあるか簡易判定。
        ポケモン系のテキストボックスは画面下部に帯状に現れる。
        """
        h = bottom_screen.shape[0]
        # 下部 20% の領域の平均輝度
        region = bottom_screen[int(h * 0.8):, :, :]
        brightness = region.mean()
        return brightness > 200  # 白っぽければテキストボックスと判断

    # ---- 内部メソッド ----

    @staticmethod
    def _crop(img: np.ndarray,
              region: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
        if region is None:
            return img
        x, y, w, h = region
        return img[y:y+h, x:x+w]

    @staticmethod
    def _match(img: np.ndarray, tmpl: np.ndarray) -> float:
        """テンプレートマッチングスコア（0〜1）を返す。"""
        if img.shape[0] < tmpl.shape[0] or img.shape[1] < tmpl.shape[1]:
            return 0.0
        img_bgr  = cv2.cvtColor(img,  cv2.COLOR_RGB2BGR)
        tmpl_bgr = cv2.cvtColor(tmpl, cv2.COLOR_RGB2BGR)
        result = cv2.matchTemplate(img_bgr, tmpl_bgr, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return float(max_val)
