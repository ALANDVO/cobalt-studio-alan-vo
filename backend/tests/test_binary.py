"""Tests for binary compatibility checking."""

from __future__ import annotations

import os
import platform
import tempfile
from pathlib import Path

import pytest

from app.core.binary import BinaryInfo, analyze_binary, check_installed_binaries, host_architecture


def test_host_architecture_known():
    arch = host_architecture()
    assert arch in ("x86_64", "aarch64", "armv7l", "unknown")


def test_analyze_missing_file():
    info = analyze_binary("/nonexistent/path/node")
    assert info.path == "/nonexistent/path/node"
    assert info.compatible is False
    assert info.reason is not None
    assert "does not exist" in info.reason


def test_analyze_existing_non_executable():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"not a binary")
        temp_path = f.name
    try:
        info = analyze_binary(temp_path)
        assert info.path == temp_path
        # Non-executable file should be incompatible
        assert info.compatible is False
    finally:
        os.unlink(temp_path)


def test_check_installed_binaries_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        results = check_installed_binaries([], tmpdir)
        assert results == {}


def test_check_installed_binaries_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        results = check_installed_binaries(["20.11.1", "22.14.0"], tmpdir)
        assert "20.11.1" in results
        assert "22.14.0" in results
        for info in results.values():
            assert info.compatible is False
            assert info.reason is not None


def test_check_installed_binaries_with_fake_node():
    """Test with a fake node binary that we create."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        # Create a fake node binary structure
        version_dir = base / "v20.11.1" / "bin"
        version_dir.mkdir(parents=True)
        node_bin = version_dir / "node"
        # Create a simple executable that prints a version
        node_bin.write_text("#!/bin/sh\necho 'v20.11.1'\n")
        node_bin.chmod(0o755)

        results = check_installed_binaries(["20.11.1"], tmpdir)
        assert "20.11.1" in results
        info = results["20.11.1"]
        # Since it runs successfully, it should be compatible
        assert info.compatible is True
        assert info.reason is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])