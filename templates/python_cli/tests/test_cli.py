"""Unit tests for CLI."""

from {{package_name}}.cli import build_parser, main


def test_parser_creation():
    parser = build_parser()
    assert parser.prog == "{{project_name}}"


def test_hello_subcommand(capsys):
    exit_code = main(["hello", "--name", "Antigravity"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Hello, Antigravity!" in captured.out
