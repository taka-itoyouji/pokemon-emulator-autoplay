#!/usr/bin/env python3
# main.py
# DeSmuME ポケモン DS 自動プレイ メインループ
#
# 使い方:
#   python main.py --mode random   # ランダムエージェント
#   python main.py --mode manual   # 手動入力をDeSmuMEに転送

import sys
import time
import argparse

import config
from window_utils import find_desmume_window, focus_window_windows
from screen_capture import ScreenCapture
from state_recognizer import StateRecognizer, Scene
from desmume_input import DesmumeInput
from random_agent import RandomAgent, Action
from manual_agent import ManualAgent
from vlm_agent import VLMAutoplayAgent
from logger import Logger


def parse_args():
    parser = argparse.ArgumentParser(description="DeSmuME 自動プレイ")
    parser.add_argument("--mode", choices=["random", "manual", "vlm-autoplay"],
                        default="random",
                        help="エージェントモード: random（ランダム）/ manual（手動転送）/ vlm-autoplay（VLM自動操作）")
    parser.add_argument("--title-bar", type=int, default=30,
                        help="DeSmuME ウィンドウのタイトルバー高さ（ピクセル）")
    parser.add_argument("--fps", type=int, default=config.FPS,
                        help="行動レート (FPS)")
    parser.add_argument("--cursor-score-log-interval", type=int, default=1,
                        help="カーソル判定スコアを何ステップごとに表示するか")
    return parser.parse_args()


def execute_action(action: Action, input_ctrl: DesmumeInput):
    """Action オブジェクトを受け取り DeSmuME に入力を送信する。"""
    if action is None:
        return
    if action.kind == "touch":
        input_ctrl.touch(action.ds_x, action.ds_y, duration=action.duration)
    elif action.kind == "key":
        input_ctrl.press_key(action.key, duration=action.duration)


def main():
    args = parse_args()
    fps      = args.fps
    interval = 1.0 / fps

    print("=" * 50)
    print(f"  DeSmuME 自動プレイ  モード: {args.mode}  FPS: {fps}")
    print("=" * 50)

    # ---- 1. DeSmuME ウィンドウ検索 ----
    print(f"\n[Init] DeSmuME ウィンドウを検索中...")
    try:
        window = find_desmume_window(config.DESMUME_WINDOW_TITLE)
        print(f"[Init] ウィンドウ検出: ({window.x}, {window.y}) "
              f"{window.width}x{window.height}")
    except RuntimeError as e:
        print(f"[Error] {e}")
        print("DeSmuME を起動してからもう一度実行してください。")
        sys.exit(1)

    # ---- 2. 各コンポーネント初期化 ----
    capture  = ScreenCapture(window, title_bar_height=args.title_bar)
    recognizer = StateRecognizer(match_threshold=0.8)
    input_ctrl = DesmumeInput(window, title_bar_height=args.title_bar)
    logger   = Logger()

    # テンプレート画像が存在すれば読み込む（任意）
    # recognizer.load_template(Scene.BATTLE, "templates/battle.png")
    # recognizer.load_template(Scene.DIALOG, "templates/dialog.png")

    # ---- 3. エージェント選択 ----
    if args.mode == "random":
        agent = RandomAgent()
        print("[Init] ランダムエージェント起動")
    elif args.mode == "manual":
        agent = ManualAgent()
        print("[Init] 手動エージェント起動")
        print("       キーボードで操作してください。Ctrl+C で終了。")
        print(f"       キーマッピング: Z=B A=Y X=DS-A S=DS-X Q=L W=R")
    else:
        agent = VLMAutoplayAgent(
            score_log_interval_steps=args.cursor_score_log_interval,
        )
        print("[Init] VLM 自動操作エージェント起動（model: qwen3-vl-4b）")

    # ---- 4. メインループ ----
    print("\n[Loop] 開始（Ctrl+C で終了）\n")
    step = 0

    try:
        while True:
            t_start = time.perf_counter()

            # 1. 画面キャプチャ
            try:
                frame = capture.capture()
            except Exception as e:
                print(f"[Warning] キャプチャ失敗（ウィンドウが最小化？）: {e}")
                time.sleep(1.0)
                continue

            # 2. 画面認識
            state = recognizer.recognize(frame)

            # 3. 行動選択
            if args.mode == "vlm-autoplay":
                action = agent.select_action(state, frame)
            else:
                action = agent.select_action(state)

            # 4. 入力反映
            execute_action(action, input_ctrl)

            # 5. ロギング
            logger.log(state, action, frame)

            # ---- 進捗表示（10ステップごと）----
            if step % 10 == 0:
                act_str = "-"
                if action:
                    if action.kind == "touch":
                        act_str = f"touch({action.ds_x},{action.ds_y})"
                    else:
                        act_str = f"key({action.key})"
                print(f"[Step {step:5d}] scene={state.scene.name:<10} action={act_str}")

            step += 1

            # FPS 制御
            elapsed = time.perf_counter() - t_start
            wait = interval - elapsed
            if wait > 0:
                time.sleep(wait)

    except KeyboardInterrupt:
        print(f"\n[Loop] 終了（{step} ステップ）")

    finally:
        capture.close()
        if args.mode == "manual" and hasattr(agent, "stop"):
            agent.stop()
        print("[Done] ログ保存先:", logger.log_dir)


if __name__ == "__main__":
    main()
