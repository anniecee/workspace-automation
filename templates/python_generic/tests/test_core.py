"""Unit tests for core module."""

from {{package_name}}.core import run_process


def test_run_process():
    res = run_process()
    assert "initialized successfully" in res
