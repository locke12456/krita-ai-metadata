from __future__ import annotations

from krita_export_plugin.group_key import GroupKeyResolver


def test_group_key_uses_index_short_job_id_and_seed():
    resolver = GroupKeyResolver()
    key = resolver.resolve(
        sync_index=1,
        job_id="9f2c8a1babcdef",
        image_index=0,
        seed=123456789,
    )

    assert key.group_name == "[0001] - 9f2c8a1b - 123456789"
    assert key.key == "0001-9f2c8a1b-123456789"
    assert key.job_id_short == "9f2c8a1b"


def test_group_key_includes_image_index_when_nonzero():
    resolver = GroupKeyResolver()
    key = resolver.resolve(
        sync_index=2,
        job_id="abcdef123456",
        image_index=3,
        seed=42,
    )

    assert key.group_name == "[0002] - abcdef12 - 42 - img3"
    assert key.key == "0002-abcdef12-42-img3"


def test_sanitize_removes_filename_unsafe_characters():
    resolver = GroupKeyResolver()

    assert resolver.sanitize('[0001] - bad:name / value*') == "0001-bad-name-value"