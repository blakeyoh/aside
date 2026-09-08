from aside.instance_lock import acquire_engine_lock, release_engine_lock


def test_engine_lock_is_shared_and_recoverable(tmp_path):
    lock_path = tmp_path / "aside.lock"

    first = acquire_engine_lock(lock_path)
    second = acquire_engine_lock(lock_path)

    assert first is not None
    assert second is None
    assert lock_path.stat().st_mode & 0o777 == 0o600
    assert lock_path.parent.stat().st_mode & 0o777 == 0o700

    release_engine_lock(first)
    replacement = acquire_engine_lock(lock_path)
    assert replacement is not None
    release_engine_lock(replacement)
