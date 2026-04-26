import json
import re
from typing import Optional

import config
from random_agent import Action
from state_recognizer import GameState
from cursor_reset_module import CursorResetModule

try:
    from PIL import Image
except ImportError:
    raise RuntimeError("Pillow が必要です: pip install pillow")

try:
    from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
except ImportError:
    raise RuntimeError("transformers が必要です: pip install transformers")


class VLMAutoplayAgent:
    """
    qwen3-vl-4b を使ってフレーム画像から入力ボタンを選ぶエージェント。
    失敗時は None を返してノーオペレーションにする。
    """

    _MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"
    # _VALID_BUTTONS = ("a", "b", "x", "y", "l", "r", "start", "select", "up", "down", "left", "right")x
    _VALID_BUTTONS = ("a", "b", "up", "down", "left", "right")

    def __init__(self, score_log_interval_steps: int = 10):
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            self._MODEL_ID, dtype="auto", device_map="auto"
        )
        self.processor = AutoProcessor.from_pretrained(self._MODEL_ID)
        self.cursor_reset = CursorResetModule.default()
        self._pending_actions = []
        self.score_log_interval_steps = max(1, int(score_log_interval_steps))
        self._step = 0

    def select_action(self, state: GameState, frame) -> Optional[Action]:
        """
        フレーム画像から次に押すべきボタンを1つ推定する。
        推論エラーやパース失敗時は None を返す。
        """
        try:
            self._step += 1
            if self._pending_actions:
                return self._pending_actions.pop(0)

            forced_seq = self.cursor_reset.detect_command(frame.bottom_screen)
            if self._step % self.score_log_interval_steps == 0:
                print(f"[CursorReset] {self.cursor_reset.get_last_debug_line()}")

            if forced_seq:
                forced_actions = []
                for forced in forced_seq:
                    mapped_key = config.KEY_MAP.get(forced)
                    if mapped_key:
                        forced_actions.append(Action(kind="key", key=mapped_key, duration=0.08))

                vlm_action = self._infer_vlm_action(state, frame)
                if forced_actions:
                    print(f"[CursorReset] detected -> {' '.join(forced_seq)}")
                    self._pending_actions.extend(forced_actions)
                    if vlm_action is not None:
                        self._pending_actions.append(vlm_action)
                    return self._pending_actions.pop(0)
                return vlm_action

            return self._infer_vlm_action(state, frame)
        except Exception as e:
            print(f"[VLM] 推論エラー: {e}")
            return None

    def _infer_vlm_action(self, state: GameState, frame) -> Optional[Action]:
        image = Image.fromarray(frame.raw)
        prompt = self._build_prompt(state)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "image": image},
                ],
            }
        ]
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)

        generated_ids = self.model.generate(**inputs, max_new_tokens=64)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        print(f"[VLM raw] {output_text}")
        button = self._extract_button(output_text)
        if button is None:
            return None

        mapped_key = config.KEY_MAP.get(button)
        if mapped_key is None:
            return None

        return Action(kind="key", key=mapped_key, duration=0.08)

    def _build_prompt(self, state: GameState) -> str:
        buttons = ", ".join(self._VALID_BUTTONS)
        return (
            "You are controlling Pokemon on Nintendo DS via emulator.\n"
            f"Current scene hint: {state.scene.name}\n"
            f"Choose exactly one best button from: {buttons}\n"
            "Output format must be exactly this XML:\n"
            "<action_json>{\"button\":\"a\"}</action_json>\n"
            "Rules:\n"
            "1) Do not output thought/reasoning.\n"
            "2) Always include valid JSON in <action_json>.\n"
            "3) button must be one of the allowed buttons."
        )

    def _extract_button(self, text: str) -> Optional[str]:
        text = text.strip()
        normalized = self._normalize_structured_output(text)

        try:
            obj = json.loads(normalized)
            button = str(obj.get("button", "")).strip().lower()
            if button in self._VALID_BUTTONS:
                return button
        except Exception:
            pass

        try:
            obj = json.loads(text)
            button = str(obj.get("button", "")).strip().lower()
            if button in self._VALID_BUTTONS:
                return button
        except Exception:
            pass

        match = re.search(r'"button"\s*:\s*"([a-z]+)"', text.lower())
        if not match:
            return None
        button = match.group(1)
        return button if button in self._VALID_BUTTONS else None

    def _normalize_structured_output(self, text: str) -> str:
        """
        Thought + 構造化出力（XML/JSON混在）から action JSON 文字列を抽出する。
        優先順位:
        1) <action_json>...</action_json>
        2) ```json ... ```
        3) 文字列内の最初の JSON オブジェクト
        """
        xml_match = re.search(r"<action_json>\s*(\{.*?\})\s*</action_json>", text, flags=re.DOTALL)
        if xml_match:
            return xml_match.group(1).strip()

        fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced_match:
            return fenced_match.group(1).strip()

        obj_match = re.search(r"(\{[\s\S]*?\})", text)
        if obj_match:
            return obj_match.group(1).strip()

        return text
