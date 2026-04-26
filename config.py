# config.py
# DeSmuME ポケモン DS 自動プレイ 設定

import os, sys

# ---- DeSmuME ウィンドウ ----
DESMUME_WINDOW_TITLE = "DeSmuME"  # ウィンドウタイトルの一部（部分一致）

# ---- DS 画面仕様 ----
DS_SCREEN_WIDTH  = 256
DS_SCREEN_HEIGHT = 192  # 上画面・下画面それぞれの高さ

# ---- メインループ ----
FPS = 10  # 1秒あたりの行動回数（5〜15 推奨）

# ---- キーマッピング（PC キー → DeSmuME デフォルト設定に合わせる）----
# ポケモン系は A, B, 十字キー, START が主な操作
KEY_MAP = {
    "a":      "x",          # DS A ボタン
    "b":      "z",          # DS B ボタン
    "x":      "s",          # DS X ボタン
    "y":      "a",          # DS Y ボタン
    "l":      "q",          # DS L ボタン
    "r":      "w",          # DS R ボタン
    "start":  "return",     # START
    "select": "right shift", # SELECT
    "up":     "up",
    "down":   "down",
    "left":   "left",
    "right":  "right",
}

# ---- ランダムエージェント行動空間 ----
# タッチ操作: (x, y) は DS 下画面座標 (0-255, 0-191)
RANDOM_TOUCH_ACTIONS = [
    ("touch", 128, 96),   # 中央
    ("touch", 64,  96),   # 左
    ("touch", 192, 96),   # 右
    ("touch", 128, 48),   # 上
    ("touch", 128, 144),  # 下
]
RANDOM_KEY_ACTIONS = ["a", "b", "up", "down", "left", "right", "start"]

# ---- ログ設定 ----
LOG_DIR = "logs"
SAVE_SCREENSHOT_EVERY = 30  # N ステップに1回スクリーンショット保存（0=無効）
