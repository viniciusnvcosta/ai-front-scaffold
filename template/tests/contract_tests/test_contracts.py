"""Validate this front's I/O against the schemas in contracts/.

Skeleton: extend with real payloads once contracts are pinned.
"""
import pathlib


def test_contracts_dir_exists():
    assert pathlib.Path("contracts").is_dir()
