from __future__ import annotations

import re
from dataclasses import dataclass


INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
WHITESPACE = re.compile(r"\s+")
DASHES = re.compile(r"-+")


@dataclass(frozen=True)
class GroupKey:
    sync_index: int
    job_id: str
    image_index: int
    seed: int
    group_name: str
    key: str
    job_id_short: str
    manual_label: str


class GroupKeyResolver:
    def __init__(self, job_id_length: int = 8) -> None:
        self.job_id_length = job_id_length

    def resolve(
        self,
        sync_index: int,
        manual_label: str | None = None,
        image_index: int = 0,
        job_id: str | None = None,
        seed: int | None = None,
    ) -> GroupKey:
        label = self.clean_label(manual_label)
        safe_job_id = str(job_id or "").strip()
        job_id_short = self.short_job_id(safe_job_id)
        safe_seed = int(seed or 0)
        group_name = f"[{sync_index:04d}] - {label}"
        if image_index:
            group_name = f"{group_name} - img{image_index}"
        key = self.sanitize(group_name)
        return GroupKey(
            sync_index=sync_index,
            job_id=safe_job_id,
            image_index=image_index,
            seed=safe_seed,
            group_name=group_name,
            key=key,
            job_id_short=job_id_short,
            manual_label=label,
        )

    def resolve_for_name(
        self,
        sync_index: int,
        group_name: str,
        job_id: str | None = None,
        image_index: int = 0,
        seed: int | None = None,
    ) -> GroupKey:
        """Use the caller-provided group name without adding a sync prefix."""
        label = self.clean_label(group_name)
        safe_job_id = str(job_id or "").strip()
        job_id_short = self.short_job_id(safe_job_id)
        safe_seed = int(seed or 0)
        return GroupKey(
            sync_index=sync_index,
            job_id=safe_job_id,
            image_index=image_index,
            seed=safe_seed,
            group_name=label,
            key=self.sanitize(label),
            job_id_short=job_id_short,
            manual_label=label,
        )

    def clean_label(self, label: str | None) -> str:
        cleaned = str(label or "").strip()
        return cleaned or "untitled"

    def short_job_id(self, job_id: str) -> str:
        cleaned = str(job_id or "").strip()
        if not cleaned:
            return ""
        return cleaned[: self.job_id_length]

    def sanitize(self, value: str) -> str:
        text = value.strip()
        text = text.replace("[", "").replace("]", "")
        text = INVALID_FILENAME_CHARS.sub("-", text)
        text = WHITESPACE.sub("-", text)
        text = DASHES.sub("-", text)
        return text.strip("-._") or "export"