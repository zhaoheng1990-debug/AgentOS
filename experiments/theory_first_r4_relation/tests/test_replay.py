from theory_first_r4_relation.cli import run


def test_two_runs_are_byte_identical(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run(first)
    run(second)
    for name in ("result.json", "hash_inventory.json", "closure.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
