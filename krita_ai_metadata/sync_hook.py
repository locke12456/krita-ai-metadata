from __future__ import annotations

from typing import Any

from ai_diffusion.layer import Layer, LayerType

from .group_key import GroupKeyResolver
from .job_params_serializer import JobParamsSerializer
from .layer_move_adapter import LayerMoveAdapter
from .model_access_adapter import ModelAccessAdapter
from .sync_map_store import SyncMapStore, SyncRecord


class SyncHookAdapter:
    def __init__(
        self,
        model_access: ModelAccessAdapter,
        key_resolver: GroupKeyResolver | None = None,
        serializer: JobParamsSerializer | None = None,
        auto_group: bool = False,
    ) -> None:
        self.model_access = model_access
        self.key_resolver = key_resolver or GroupKeyResolver()
        self.serializer = serializer or JobParamsSerializer()
        self.auto_group = auto_group
        self._original_apply: Any | None = None

    def install(self) -> bool:
        model = self.model_access.active_model()
        if model is None:
            return False
        if self._original_apply is not None:
            return True
        self._original_apply = model.apply_generated_result

        def wrapped(job_id: str, index: int) -> Any:
            return self.apply_generated_result(job_id, index)

        model.apply_generated_result = wrapped
        return True

    def uninstall(self) -> None:
        model = self.model_access.active_model()
        if model is not None and self._original_apply is not None:
            model.apply_generated_result = self._original_apply
        self._original_apply = None

    def apply_generated_result(self, job_id: str, index: int) -> Any:
        model = self.model_access.active_model()
        if model is None or self._original_apply is None:
            return None

        before_ids = self._layer_ids(model.layers.all)
        result = self._original_apply(job_id, index)
        model.layers.update()
        after_layers = model.layers.all
        after_ids = self._layer_ids(after_layers)
        new_ids = [layer_id for layer_id in after_ids if layer_id not in before_ids]

        job = model.jobs.find(job_id)
        if job is None or not new_ids:
            return result

        document = model.document
        store = SyncMapStore(document)
        sync_index = store.allocate_sync_index()
        key = self.key_resolver.resolve(
            sync_index=sync_index,
            manual_label=job.id,
            image_index=index,
            job_id=job.id,
            seed=job.params.seed,
        )
        target_layers = [layer for layer in after_layers if layer.id_string in new_ids]

        group_layer = None
        layer_ids = new_ids
        target_type = "layer"
        group_id = None
        group_name = None

        if self.auto_group and target_layers:
            group_layer = self._ensure_group(model, key.group_name)
            mover = LayerMoveAdapter(model.layers)
            moved_layers: list[Layer] = []
            for layer in target_layers:
                moved_layers.append(mover.move_to_group(layer, group_layer))
            model.layers.update()
            layer_ids = [layer.id_string for layer in moved_layers]
            target_type = "group"
            group_id = group_layer.id_string
            group_name = group_layer.name

        record = SyncRecord(
            target_type=target_type,
            export_key=key.key,
            layer_ids=layer_ids,
            group_id=group_id,
            group_name=group_name,
            job_id=key.job_id,
            image_index=index,
            seed=key.seed,
            params_snapshot=self.serializer.serialize_job_params(job.params),
            job_id_short=key.job_id_short,
            sync_index=sync_index,
            manual_label=key.manual_label,
        )
        store.record_apply(record)
        return result

    def _layer_ids(self, layers: list[Layer]) -> list[str]:
        return [layer.id_string for layer in layers]

    def _ensure_group(self, model: Any, group_name: str) -> Layer:
        for layer in model.layers.all:
            if layer.type is LayerType.group and layer.name == group_name:
                return layer
        return model.layers.create_group(group_name)