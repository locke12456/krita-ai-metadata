from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class FakeBounds:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    @property
    def is_zero(self) -> bool:
        return self.width == 0 or self.height == 0


class FakeLayerType(Enum):
    group = "grouplayer"
    paint = "paintlayer"

    @property
    def is_image(self) -> bool:
        return True


@dataclass
class FakeJobRegion:
    layer_id: str = ""
    prompt: str = ""
    bounds: FakeBounds = field(default_factory=FakeBounds)
    is_background: bool = False


@dataclass
class FakeJobParams:
    bounds: FakeBounds = field(default_factory=FakeBounds)
    name: str = ""
    regions: list[FakeJobRegion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    has_mask: bool = False
    is_layered: bool = False
    frame: tuple[int, int, int] = (0, 0, 0)
    animation_id: str = ""
    resize_canvas: bool = False

    @staticmethod
    def _coerce_bounds(value: Any) -> FakeBounds:
        if isinstance(value, FakeBounds):
            return value
        if isinstance(value, (list, tuple)):
            return FakeBounds(*value)
        if isinstance(value, dict):
            return FakeBounds(**value)
        return FakeBounds()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FakeJobParams":
        bounds = cls._coerce_bounds(data.get("bounds", FakeBounds()))
        regions = []
        for item in data.get("regions", []):
            if isinstance(item, FakeJobRegion):
                regions.append(item)
                continue
            region_data = dict(item)
            region_data["bounds"] = cls._coerce_bounds(region_data.get("bounds", FakeBounds()))
            regions.append(FakeJobRegion(**region_data))
        frame = data.get("frame", (0, 0, 0))
        if isinstance(frame, list):
            frame = tuple(frame)
        return cls(
            bounds=bounds,
            name=data.get("name", ""),
            regions=regions,
            metadata=dict(data.get("metadata", {})),
            seed=int(data.get("seed", 0) or 0),
            has_mask=bool(data.get("has_mask", False)),
            is_layered=bool(data.get("is_layered", False)),
            frame=frame,
            animation_id=data.get("animation_id", ""),
            resize_canvas=bool(data.get("resize_canvas", False)),
        )
