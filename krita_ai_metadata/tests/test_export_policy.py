from __future__ import annotations

from krita_export_plugin.export_policy import ExportDecision, ExportPolicy


def test_unresolved_defaults_to_abort():
    policy = ExportPolicy()
    decision = policy.on_unresolved_target(target=None, warning="missing metadata")

    assert decision == ExportDecision.abort
    assert policy.should_abort(decision)


def test_allowed_unresolved_can_skip():
    policy = ExportPolicy(
        allow_unresolved=True,
        default_decision=ExportDecision.skip,
    )
    decision = policy.on_unresolved_target(target=None, warning="missing metadata")

    assert decision == ExportDecision.skip
    assert policy.should_skip(decision)


def test_allowed_unresolved_can_export_without_metadata():
    policy = ExportPolicy(
        allow_unresolved=True,
        default_decision=ExportDecision.export_without_metadata,
    )
    decision = policy.on_unresolved_target(target=None, warning="missing metadata")

    assert decision == ExportDecision.export_without_metadata
    assert policy.should_write_without_metadata(decision)