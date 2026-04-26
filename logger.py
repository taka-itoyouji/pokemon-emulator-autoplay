# utils/logger.py
# 行動ログ・スクリーンショットの保存

import os
import csv
import time
import numpy as np
from datetime import datetime
from typing import Optional
from PIL import Image

import config


class Logger:
    """ゲームプレイのログを CSV とスクリーンショットで記録する。"""

    def __init__(self, run_name: Optional[str] = None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_name = run_name or timestamp
        self.log_dir = os.path.join(config.LOG_DIR, self.run_name)
        self.ss_dir  = os.path.join(self.log_dir, "screenshots")
        os.makedirs(self.ss_dir, exist_ok=True)

        self.csv_path = os.path.join(self.log_dir, "actions.csv")
        self._step = 0
        self._start_time = time.time()

        # CSV ヘッダー書き込み
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["step", "elapsed_sec", "scene", "action_kind",
                             "action_key", "action_ds_x", "action_ds_y"])

    def log(self, state, action, frame=None):
        """
        1ステップ分のデータを記録する。
        state:  GameState
        action: Action または None
        frame:  DSFrame（スクリーンショット保存用、任意）
        """
        elapsed = round(time.time() - self._start_time, 3)

        action_kind  = action.kind  if action else "-"
        action_key   = action.key   if action else "-"
        action_ds_x  = action.ds_x  if action else "-"
        action_ds_y  = action.ds_y  if action else "-"

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                self._step, elapsed,
                state.scene.name,
                action_kind, action_key, action_ds_x, action_ds_y,
            ])

        # スクリーンショット保存
        if (frame is not None and
                config.SAVE_SCREENSHOT_EVERY > 0 and
                self._step % config.SAVE_SCREENSHOT_EVERY == 0):
            self._save_screenshot(frame)

        self._step += 1

    def _save_screenshot(self, frame):
        try:
            img_array = frame.raw  # RGB numpy array
            img = Image.fromarray(img_array.astype(np.uint8))
            fname = os.path.join(self.ss_dir, f"step_{self._step:06d}.png")
            img.save(fname)
        except Exception as e:
            print(f"[Logger] スクリーンショット保存エラー: {e}")
