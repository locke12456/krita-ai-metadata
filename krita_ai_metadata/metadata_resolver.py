from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_diffusion.text import create_img_metadata

from .export_target_scanner import ExportTarget
from .job_params_serializer import JobParamsSerializer


@dataclass(slots=True)
class ResolvedMetadata:
    """Metadata resolution result for one export target."""

    target: ExportTarget
    key: str
    record: dict[str, Any] | None
    params: Any | None
    a1111_parameters: str
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    @property
    def has_metadata(self) -> bool:
        """Return True when A1111 parameters are available."""
        return bool(self.a1111_parameters)


class MetadataResolver:
    """Resolve sync-map records into PNG parameters and sidecar payloads."""

    def __init__(self, serializer: JobParamsSerializer | None = None):
        self._serializer = serializer or JobParamsSerializer()

    def resolve(self, target: ExportTarget) -> ResolvedMetadata:
        """Resolve metadata for an export target."""
        warnings = list(target.warnings)

        if target.record is None:
            payload = self._payload(target, None, "")
            return ResolvedMetadata(
                target=target,
                key=target.key,
                record=None,
                params=None,
                a1111_parameters="",
                payload=payload,
                warnings=warnings,
            )

        params_snapshot = target.record.get("params_snapshot")
        if not isinstance(params_snapshot, dict):
            warnings.append(f"Sync record for '{target.key}' has no params_snapshot.")
            payload = self._payload(target, target.record, "")
            return ResolvedMetadata(
                target=target,
                key=target.key,
                record=target.record,
                params=None,
                a1111_parameters="",
                payload=payload,
                warnings=warnings,
            )

        try:
            params = self._serializer.deserialize_job_params(params_snapshot)
            parameters = create_img_metadata(params)
        except Exception as exc:
            warnings.append(f"Failed to format metadata for '{target.key}': {exc}")
            params = None
            parameters = ""

        payload = self._payload(target, target.record, parameters)
        return ResolvedMetadata(
            target=target,
            key=target.key,
            record=target.record,
            params=params,
            a1111_parameters=parameters,
            payload=payload,
            warnings=warnings,
        )

    def _payload(
        self,
        target: ExportTarget,
        record: dict[str, Any] | None,
        parameters: str,
    ) -> dict[str, Any]:
        """Build the sidecar JSON metadata payload."""
        record = record or {}
        return {
            "version": 1,
            "target_type": record.get("target_type", target.target_type),
            "key": record.get("export_key", target.key),
            "group_name": record.get("group_name"),
            "group_id": record.get("group_id"),
            "layer_ids": list(record.get("layer_ids", [target.layer.id_string])),
            "job_id": record.get("job_id", ""),
            "job_id_short": record.get("job_id_short", ""),
            "image_index": int(record.get("image_index", 0) or 0),
            "seed": int(record.get("seed", 0) or 0),
            "params_snapshot": dict(record.get("params_snapshot", {})),
            "a1111_parameters": parameters,
            "children": self._children_payload(target),
            "warnings": list(target.warnings),
        }

    def _children_payload(self, target: ExportTarget) -> list[dict[str, Any]]:
        """Return summaries for child layers in a group target."""
        children: list[dict[str, Any]] = []
        for child in target.layer.child_layers:
            children.append(
                {
                    "id": child.id_string,
                    "name": child.name,
                    "type": child.type.value,
                    "visible": child.is_visible,
                }
            )
        return children