# agent/random_agent.py
# ランダム行動エージェント

import random
from dataclasses import dataclass
from typing import Tuple, Optional
import config
from state_recognizer import GameState, Scene


@dataclass
class Action:
    """1つの行動を表す。"""
    kind: str                     # "touch" or "key"
    key: Optional[str] = None     # キー名（kind=="key" の時）
    ds_x: Optional[int] = None    # DS タッチ X 座標
    ds_y: Optional[int] = None    # DS タッチ Y 座標
    duration: float = 0.08        # 押下時間（秒）


class RandomAgent:
    """
    ランダムに行動を選択するエージェント。
    シーンに応じて行動リストを切り替える（ルールベースの補助あり）。
    """

    def select_action(self, state: GameState) -> Action:
        """GameState を受け取り Action を返す。"""

        # シーン別の優先ルール
        if state.scene == Scene.DIALOG:
            # テキスト送りは A ボタンを押す
            return Action(kind="key", key=config.KEY_MAP["a"])

        if state.scene == Scene.BATTLE:
            # マウス暴走回避のため、ランダムモードではキー入力のみ使う
            return self._random_key()

        if state.scene == Scene.MENU:
            # メニューは十字キー + A ボタンランダム
            return random.choice([
                Action(kind="key", key=config.KEY_MAP["up"]),
                Action(kind="key", key=config.KEY_MAP["down"]),
                Action(kind="key", key=config.KEY_MAP["a"]),
            ])

        # デフォルト: マウス操作は使わずキーのみランダム選択
        return self._random_key()

    def _random_touch(self) -> Action:
        _, ds_x, ds_y = random.choice(config.RANDOM_TOUCH_ACTIONS)
        return Action(kind="touch", ds_x=ds_x, ds_y=ds_y, duration=0.08)

    def _random_key(self) -> Action:
        key_name = random.choice(config.RANDOM_KEY_ACTIONS)
        return Action(kind="key", key=config.KEY_MAP[key_name], duration=0.08)
