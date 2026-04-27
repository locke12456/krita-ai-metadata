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


class GroupKeyResolver:
    def __init__(self, job_id_length: int = 8) -> None:
        self.job_id_length = job_id_length

    def resolve(self, sync_index: int, job_id: str | None, image_index: int, seed: int | None) -> GroupKey:
        safe_job_id = job_id or "unknown"
        job_id_short = self.short_job_id(safe_job_id)
        safe_seed = int(seed or 0)
        group_name = f"[{sync_index:04d}] - {job_id_short} - {safe_seed}"
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
        )

    def short_job_id(self, job_id: str) -> str:
        cleaned = str(job_id).strip()
        if not cleaned:
            return "unknown"
        return cleaned[: self.job_id_length]

    def sanitize(self, value: str) -> str:
        text = value.strip()
        text = text.replace("[", "").replace("]", "")
        text = INVALID_FILENAME_CHARS.sub("-", text)
        text = WHITESPACE.sub("-", text)
        text = DASHES.sub("-", text)
        return text.strip("-._") or "export"