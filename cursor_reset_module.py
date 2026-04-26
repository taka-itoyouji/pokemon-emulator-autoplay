from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class CursorResetRule:
    name: str
    template_path: str
    command: List[str]
    max_hamming_distance: Optional[int] = None


class CursorResetModule:
    """
    下画面の dHash で特定シーンを軽量判定し、初期カーソル移動列を返す。

    - scene_1 一致時: right, right, up
    - scene_2 一致時: up, up, left
    - 一致が曖昧な場合は None（発動しない）
    """

    def __init__(
        self,
        rules: List[CursorResetRule],
        hash_size: int = 16,
        max_hamming_distance: int = 80,
        min_margin: int = 4,
        cooldown_frames: int = 1,
    ) -> None:
        self.hash_size = hash_size
        self.max_hamming_distance = max_hamming_distance
        self.min_margin = min_margin
        self.cooldown_frames = cooldown_frames
        self._cooldown = 0
        self._templates: Dict[str, np.ndarray] = {}
        self._commands: Dict[str, List[str]] = {}
        self._thresholds: Dict[str, int] = {}
        self._last_distances: Dict[str, int] = {}
        self._last_best: Optional[Tuple[str, int]] = None
        self._last_second: Optional[Tuple[str, int]] = None
        self._last_best_threshold: Optional[int] = None
        self._load_rules(rules)

    @classmethod
    def default(cls) -> "CursorResetModule":
        return cls(
            rules=[
                CursorResetRule(
                    name="scene_1",
                    template_path=(
                        "templates/POKEMON_SS_IPGJ01_00.trim__31728.png"
                    ),
                    command=["right", "right", "up"],
                    max_hamming_distance=65,
                ),
                CursorResetRule(
                    name="scene_2",
                    template_path=(
                        "templates/POKEMON_SS_IPGJ01_00.trim__6972.png"
                    ),
                    command=["up", "up", "left"],
                    max_hamming_distance=75,
                ),
            ]
        )

    def detect_command(self, bottom_screen_rgb: np.ndarray) -> Optional[List[str]]:
        if not self._templates:
            return None

        current = self._dhash_from_rgb(bottom_screen_rgb)
        distances = {}
        for name, template_hash in self._templates.items():
            distances[name] = int(np.count_nonzero(current != template_hash))

        if not distances:
            return None

        sorted_hits = sorted(distances.items(), key=lambda x: x[1])
        best_name, best_dist = sorted_hits[0]
        second_dist = sorted_hits[1][1] if len(sorted_hits) > 1 else 9999
        best_threshold = self._thresholds.get(best_name, self.max_hamming_distance)
        self._last_distances = dict(distances)
        self._last_best = (best_name, best_dist)
        self._last_second = sorted_hits[1] if len(sorted_hits) > 1 else None
        self._last_best_threshold = best_threshold

        if self._cooldown > 0:
            self._cooldown -= 1
            return None

        if best_dist > best_threshold:
            return None
        if (second_dist - best_dist) < self.min_margin:
            return None

        self._cooldown = self.cooldown_frames
        return list(self._commands[best_name])

    def get_last_debug_line(self) -> str:
        if not self._last_distances:
            return "scores: (no templates loaded)"
        score_items = ", ".join(
            f"{name}={dist}" for name, dist in sorted(self._last_distances.items(), key=lambda x: x[0])
        )
        best_txt = "best=none"
        if self._last_best:
            best_txt = f"best={self._last_best[0]}({self._last_best[1]})"
        second_txt = "second=none"
        if self._last_second:
            second_txt = f"second={self._last_second[0]}({self._last_second[1]})"
        th_txt = f"th_best<={self.max_hamming_distance}"
        if self._last_best_threshold is not None and self._last_best:
            th_txt = f"th_{self._last_best[0]}<={self._last_best_threshold}"
        return (
            f"scores: {score_items} | {best_txt} | {second_txt} | "
            f"{th_txt}, th_margin>={self.min_margin}, cooldown={self._cooldown}"
        )

    def _load_rules(self, rules: List[CursorResetRule]) -> None:
        for rule in rules:
            p = Path(rule.template_path)
            if not p.exists():
                continue
            try:
                img = Image.open(p).convert("RGB")
                arr = np.array(img, dtype=np.uint8)
                bottom = arr[arr.shape[0] // 2 :, :, :]
                self._templates[rule.name] = self._dhash_from_rgb(bottom)
                self._commands[rule.name] = list(rule.command)
                threshold = rule.max_hamming_distance
                if threshold is None:
                    threshold = self.max_hamming_distance
                self._thresholds[rule.name] = int(threshold)
            except Exception:
                continue

    def _dhash_from_rgb(self, rgb_img: np.ndarray) -> np.ndarray:
        gray = (
            0.299 * rgb_img[:, :, 0]
            + 0.587 * rgb_img[:, :, 1]
            + 0.114 * rgb_img[:, :, 2]
        ).astype(np.uint8)
        pil = Image.fromarray(gray, mode="L").resize(
            (self.hash_size + 1, self.hash_size), Image.Resampling.BILINEAR
        )
        arr = np.array(pil, dtype=np.uint8)
        diff = arr[:, 1:] > arr[:, :-1]
        return diff.reshape(-1)
