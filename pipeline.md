# DeSmuME ポケモン DS 自動プレイ パイプライン

## 概要

DeSmuME エミュレータ上でポケモン DS を自動プレイするための Python パイプラインです。  
**画面キャプチャ → 画面認識 → 行動選択 → 入力反映** のループを繰り返します。

---

## フォルダ構成

```
pokemon_bot/
├── pipeline.md            # この文書
├── main.py                # エントリーポイント・メインループ
├── config.py              # 設定（解像度・FPS・ウィンドウ名など）
├── capture/
│   └── screen_capture.py  # 画面キャプチャ
├── recognition/
│   └── state_recognizer.py # 画面認識・状態抽出
├── agent/
│   ├── base_agent.py      # エージェント基底クラス
│   ├── random_agent.py    # ランダム行動エージェント
│   └── manual_agent.py    # ユーザー手動入力エージェント
├── action/
│   ├── input_mapper.py    # 行動→入力変換
│   └── desmume_input.py   # DeSmuME への入力送信
└── utils/
    ├── logger.py          # ログ・スクリーンショット保存
    └── window_utils.py    # ウィンドウ検索・フォーカス
```

---

## パイプライン各フェーズ

### Phase 0: 初期化

- DeSmuME ウィンドウをタイトル名で検索し、ハンドル取得
- ウィンドウ位置・サイズを取得してキャプチャ領域を確定
- エージェントモード（ランダム / 手動）を選択

### Phase 1: 画面キャプチャ

- DeSmuME ウィンドウの描画領域をスクリーンショット取得
- DS 画面は **上画面 (256×192)** と **下画面/タッチ画面 (256×192)** の2画面
- ライブラリ: `mss`（高速）または `PIL.ImageGrab`
- OS 差異:
  - Windows: `win32gui` でウィンドウ位置取得、`mss` でキャプチャ
  - Linux: `xdotool` または `wmctrl` でウィンドウ位置取得

### Phase 2: 前処理

- NumPy 配列に変換、BGR → RGB 変換
- 上下画面を分割（y座標で切り分け）
- 必要に応じてリサイズ・正規化（認識モデルの入力サイズへ）

### Phase 3: 画面認識・状態抽出

- **シーン判定**: テンプレートマッチング（OpenCV）またはピクセルサンプリングで現在の画面状態を分類
  - 例: フィールド / バトル / メニュー / テキスト送り待ち
- **テキスト認識**: Tesseract OCR（`pytesseract`）でメッセージ内容取得（任意）
- 出力: `GameState` オブジェクト（シーン種別・画面画像を含む）

### Phase 4: 行動選択

#### モード A: ランダム行動エージェント
- 行動空間（タップ座標 or キー）をランダムサンプリング
- シーン別の行動リストを定義し、そこからランダム選択
- 拡張: 簡単なルールベース（テキスト送り待ちなら A ボタン、など）

#### モード B: 手動入力エージェント
- `pynput` でキーボード入力をリアルタイム監視
- キーマッピングテーブル（PC キー → DS ボタン）を参照して変換
- タッチ操作: マウスクリック座標を DS タッチ座標に変換

### Phase 5: DeSmuME への入力反映

#### キー入力（ボタン操作）
- **Windows**: `pyautogui.keyDown/keyUp` または `SendInput` (ctypes)
  - DeSmuME ウィンドウにフォーカスを当ててから送信
- **Linux**: `xdotool key` コマンドをサブプロセスで呼び出し

#### タッチ入力（タッチペン操作）
- DeSmuME の下画面領域内のウィンドウ座標を計算
- `pyautogui.click(x, y)` でマウスクリックを送信
- 長押しは `mouseDown` → `sleep` → `mouseUp`
- DS タッチ座標 (0–255, 0–191) → ウィンドウ座標 へのスケーリング変換が必要

### Phase 6: ログ・状態保存

- フレームごとのスクリーンショット（任意・間引き可）
- 行動ログを CSV / JSON に保存（タイムスタンプ・行動・シーン）
- ループカウンタ・経過時間の表示

---

## メインループ制御

```
while True:
    frame = capture()
    state = recognize(frame)
    action = agent.select_action(state)
    send_input(action)
    logger.log(state, action)
    sleep(1.0 / FPS)  # FPS 制御（推奨: 5〜15 FPS）
```

---

## DeSmuME 設定（事前に行うこと）

1. **キーボード割り当て**: Config → Joystick/Keyboard で設定
   - 推奨マッピング（デフォルト準拠）:
     ```
     A=X, B=Z, X=S, Y=A, L=Q, R=W
     START=Return, SELECT=Right Shift
     上=Up, 下=Down, 左=Left, 右=Right
     ```
2. **ウィンドウサイズ固定**: View → Window Size で 1x または 2x に固定
3. **タッチ入力有効化**: Config → Stylus で Mouse を選択
4. **フレームスキップ無効化**: Config → Frame skip → 0

---

## 依存ライブラリ

```
# requirements.txt
mss>=9.0
Pillow>=10.0
numpy>=1.24
opencv-python>=4.8
pyautogui>=0.9.54
pynput>=1.7
# Windows のみ
pywin32>=306
# Linux のみ
# xdotool（apt install xdotool）
```

---

## 実装ステップ

| Step | 内容 | ファイル |
|------|------|---------|
| 1 | 環境構築・ライブラリインストール | requirements.txt |
| 2 | DeSmuME 起動・ウィンドウ検索確認 | window_utils.py |
| 3 | 画面キャプチャ動作確認 | screen_capture.py |
| 4 | 上下画面分割・表示確認 | screen_capture.py |
| 5 | テンプレート画像収集（バトル画面など） | recognition/ |
| 6 | シーン判定実装 | state_recognizer.py |
| 7 | タッチ入力送信テスト | desmume_input.py |
| 8 | キー入力送信テスト | desmume_input.py |
| 9 | ランダムエージェント組み合わせ | random_agent.py |
| 10 | 手動エージェント組み合わせ | manual_agent.py |
| 11 | メインループ統合 | main.py |
| 12 | ログ機能追加 | logger.py |

---

## OS 別注意事項

### Windows
- DeSmuME の管理者権限不要（通常ユーザーで OK）
- `pywin32` で確実なウィンドウ操作が可能
- `pyautogui.FAILSAFE = False` を設定しておくと安全

### Linux
- `xdotool`, `wmctrl` を apt でインストール
- Wayland 環境では `xdotool` が動作しない場合あり → X11 セッションを使用
- DeSmuME は `desmume-gtk` パッケージ

---

## 拡張案（将来）

- **強化学習**: `gym` / `stable-baselines3` でエージェントを学習
- **画面認識強化**: 軽量 CNN（MobileNet）でシーン分類
- **セーブステート活用**: DeSmuME の savestate をキーで操作し学習効率向上
- **並列実行**: 複数 DeSmuME インスタンスの同時制御
