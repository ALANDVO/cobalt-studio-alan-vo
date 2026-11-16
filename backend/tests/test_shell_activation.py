"""Tests for the shell-activation module."""

from __future__ import annotations

from app.core.shell_activation import ShellActivation, activation_from_resolution


def make_act(source: str, selected_version: str, bin_dir: str = "") -> ShellActivation:
    """Helper to create a ShellActivation directly."""
    return ShellActivation(source=source, selected_version=selected_version, bin_dir=bin_dir)


def test_bash_snippet_missing_pin_returns_exit0():
    """A bash snippet for a missing pin should not crash and should set variables."""
    act = make_act("node-version", "20.11.1", "")
    snippet = act.bash_snippet()
    assert "export NODE_VERSION=20.11.1" in snippet
    assert "export NODE_BIN_DIR=" in snippet
    assert 'if [ -d "$NODE_BIN_DIR" ]; then' in snippet
    # The snippet itself should be valid bash syntax (no syntax error)
    import subprocess
    result = subprocess.run(
        ["bash", "-n", "/dev/stdin"],
        input=snippet.encode(),
        capture_output=True,
    )
    assert result.returncode == 0, f"Bash syntax check failed: {result.stderr.decode()}"


def test_zsh_snippet_missing_pin():
    """A zsh snippet for a missing pin should produce valid syntax."""
    act = make_act("node-version", "20.11.1", "")
    snippet = act.zsh_snippet()
    assert "export NODE_VERSION=20.11.1" in snippet
    assert "export NODE_BIN_DIR=" in snippet
    assert 'if [ -d "$NODE_BIN_DIR" ]; then' in snippet


def test_fish_snippet_missing_pin():
    """A fish snippet for a missing pin should produce valid syntax."""
    act = make_act("node-version", "20.11.1", "")
    snippet = act.fish_snippet()
    assert "set -g NODE_VERSION 20.11.1" in snippet
    assert "set -g NODE_BIN_DIR " in snippet
    assert "if test -d $NODE_BIN_DIR" in snippet


def test_env_file_missing_pin():
    """An env file for a missing pin should contain the variables without interactive profile."""
    act = make_act("node-version", "20.11.1", "")
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".env", delete=False) as f:
        path = f.name
    try:
        act.env_file(path)
        content = open(path).read()
        assert "NODE_VERSION=20.11.1" in content
        assert "NODE_BIN_DIR=" in content
        # Should NOT contain sourcing of interactive profiles
        assert ".bashrc" not in content
        assert ".zshrc" not in content
    finally:
        os.unlink(path)


def test_bash_snippet_satisfied_pin():
    """A bash snippet for a satisfied pin should include the binary dir in PATH."""
    act = make_act("node-version", "20.11.1", "/usr/local/bin")
    snippet = act.bash_snippet()
    assert "export NODE_VERSION=20.11.1" in snippet
    assert "export NODE_BIN_DIR=/usr/local/bin" in snippet
    assert 'if [ -d "$NODE_BIN_DIR" ]; then' in snippet
    assert 'export PATH="$NODE_BIN_DIR:$PATH"' in snippet


def test_fish_snippet_satisfied_pin():
    """A fish snippet for a satisfied pin should include the binary dir in PATH."""
    act = make_act("node-version", "20.11.1", "/usr/local/bin")
    snippet = act.fish_snippet()
    assert "set -g NODE_VERSION 20.11.1" in snippet
    assert "set -g NODE_BIN_DIR /usr/local/bin" in snippet
    assert "if test -d $NODE_BIN_DIR" in snippet
    assert "set -U PATH $NODE_BIN_DIR $PATH" in snippet


def test_activation_from_resolution_type_error():
    """activation_from_resolution should reject non-Resolution objects."""
    try:
        activation_from_resolution("not a resolution")  # type: ignore
        assert False, "Expected TypeError"
    except TypeError:
        pass  # expected
