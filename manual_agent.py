# agent/manual_agent.py
# ユーザーのキーボード入力を DeSmuME に転送するエージェント
# pynput でキー入力を非同期監視し、押されたキーを Action に変換する

import threading
from typing import Optional
import config
from random_agent import Action
from state_recognizer import GameState

try:
    from pynput import keyboard as kb
except ImportError:
    raise RuntimeError("pynput が必要です: pip install pynput")


# ---- PC キー → DS アクション のマッピング ----
# ユーザーが押すキー → DS ボタン名
_KEY_TO_DS = {
    "x":      "a",       # DS A
    "z":      "b",       # DS B
    "s":      "x",       # DS X
    "a":      "y",       # DS Y
    "q":      "l",       # DS L
    "w":      "r",       # DS R
    "return": "start",
    "up":     "up",
    "down":   "down",
    "left":   "left",
    "right":  "right",
}

_INPUT_PRIORITY = [
    "up", "down", "left", "right",
    "x", "z", "s", "a", "q", "w", "return",
]


class ManualAgent:
    """
    ユーザーのキーボード入力をリアルタイムで監視し、
    select_action() が呼ばれたタイミングで Action を返す。

    メインループからは select_action(state) を呼ぶだけでよい。
    キーが押されていなければ None を返す（ノーオペレーション）。
    """

    def __init__(self):
        self._pressed_lookups: set[str] = set()
        self._lock = threading.Lock()
        self._listener: Optional[kb.Listener] = None
        self._start_listening()

    def _start_listening(self):
        def on_press(key):
            lookup = self._key_to_lookup(key)
            if lookup:
                with self._lock:
                    self._pressed_lookups.add(lookup)

        def on_release(key):
            lookup = self._key_to_lookup(key)
            if lookup:
                with self._lock:
                    self._pressed_lookups.discard(lookup)

        self._listener = kb.Listener(on_press=on_press, on_release=on_release, suppress=False)
        self._listener.daemon = True
        self._listener.start()

    def _key_to_lookup(self, key) -> Optional[str]:
        """pynput のキーオブジェクトを lookup 文字列に変換する。"""
        # 文字キー
        try:
            char = key.char.lower() if key.char else None
        except AttributeError:
            char = None

        # 特殊キー
        special = None
        if key == kb.Key.up:     special = "up"
        elif key == kb.Key.down: special = "down"
        elif key == kb.Key.left: special = "left"
        elif key == kb.Key.right: special = "right"
        elif key == kb.Key.enter: special = "return"

        lookup = char or special
        return lookup if lookup in _KEY_TO_DS else None

    def select_action(self, state: GameState) -> Optional[Action]:
        """select_action 呼び出し時点で押されているキーだけを反映する。"""
        with self._lock:
            if not self._pressed_lookups:
                return None
            for lookup in _INPUT_PRIORITY:
                if lookup in self._pressed_lookups:
                    ds_button = _KEY_TO_DS.get(lookup)
                    mapped_key = config.KEY_MAP.get(ds_button) if ds_button else None
                    if mapped_key:
                        return Action(kind="key", key=mapped_key, duration=0.05)
        return None

    def stop(self):
        if self._listener:
            self._listener.stop()
