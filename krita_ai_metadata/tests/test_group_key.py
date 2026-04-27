from __future__ import annotations

from krita_ai_metadata.group_key import GroupKeyResolver


def test_group_key_uses_index_and_manual_label_without_seed():
    resolver = GroupKeyResolver()
    key = resolver.resolve(
        sync_index=1,
        manual_label="castle-test-A",
        job_id="9f2c8a1babcdef",
        image_index=0,
        seed=123456789,
    )

    assert key.group_name == "[0001] - castle-test-A"
    assert key.key == "0001-castle-test-A"
    assert key.job_id_short == "9f2c8a1b"
    assert key.manual_label == "castle-test-A"
    assert key.seed == 123456789


def test_group_key_includes_image_index_when_nonzero():
    resolver = GroupKeyResolver()
    key = resolver.resolve(
        sync_index=2,
        manual_label="castle-test-A",
        job_id="abcdef123456",
        image_index=3,
        seed=42,
    )

    assert key.group_name == "[0002] - castle-test-A - img3"
    assert key.key == "0002-castle-test-A-img3"


def test_sanitize_removes_filename_unsafe_characters():
    resolver = GroupKeyResolver()

    assert resolver.sanitize('[0001] - bad:name / value*') == "0001-bad-name-value"