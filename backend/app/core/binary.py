"""Detect the architecture and interpreter of a Node binary."""

from __future__ import annotations

import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class BinaryInfo:
    """Information extracted from a Node binary."""

    path: str
    architecture: Literal["x86_64", "aarch64", "armv7l", "unknown"]
    format: Literal["ELF", "Mach-O", "unknown"]
    interpreter: str | None
    compatible: bool
    reason: str | None


def host_architecture() -> Literal["x86_64", "aarch64", "armv7l", "unknown"]:
    """Return the normalized host architecture."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    if machine in ("aarch64", "arm64"):
        return "aarch64"
    if machine in ("armv7l", "armv7"):
        return "armv7l"
    return "unknown"


def _read_elf_interpreter(path: Path) -> tuple[str, str] | None:
    """Read the PT_INTERP segment from an ELF binary using readelf."""
    try:
        result = subprocess.run(
            ["readelf", "-l", str(path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            if "INTERP" in line and "Requesting program interpreter" in line:
                # Line format: "      [Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]"
                parts = line.split(":")
                if len(parts) >= 2:
                    interp = parts[-1].strip().strip("]")
                    return "ELF", interp
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _read_macho_arch(path: Path) -> tuple[str, str] | None:
    """Read architecture from a Mach-O binary using file command."""
    try:
        result = subprocess.run(
            ["file", "-b", str(path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        output = result.stdout.lower()
        if "mach-o" not in output:
            return None
        arch = "unknown"
        if "x86_64" in output:
            arch = "x86_64"
        elif "arm64" in output or "aarch64" in output:
            arch = "aarch64"
        elif "arm" in output:
            arch = "armv7l"
        return "Mach-O", arch
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def analyze_binary(path: str) -> BinaryInfo:
    """Analyze a Node binary and return its compatibility with the host."""
    binary_path = Path(path)
    host_arch = host_architecture()

    if not binary_path.exists() or not binary_path.is_file():
        return BinaryInfo(
            path=path,
            architecture="unknown",
            format="unknown",
            interpreter=None,
            compatible=False,
            reason="File does not exist or is not a regular file",
        )

    # Try ELF first (Linux)
    elf_result = _read_elf_interpreter(binary_path)
    if elf_result:
        fmt, interpreter = elf_result
        # Determine architecture from interpreter path
        arch = "unknown"
        if "x86_64" in interpreter or "x86-64" in interpreter:
            arch = "x86_64"
        elif "aarch64" in interpreter or "arm64" in interpreter:
            arch = "aarch64"
        elif "arm" in interpreter:
            arch = "armv7l"

        compatible = arch == host_arch or host_arch == "unknown"
        reason = None if compatible else f"Binary architecture {arch} does not match host {host_arch}"

        return BinaryInfo(
            path=path,
            architecture=arch,
            format=fmt,
            interpreter=interpreter,
            compatible=compatible,
            reason=reason,
        )

    # Try Mach-O (macOS)
    macho_result = _read_macho_arch(binary_path)
    if macho_result:
        fmt, arch = macho_result
        compatible = arch == host_arch or host_arch == "unknown"
        reason = None if compatible else f"Binary architecture {arch} does not match host {host_arch}"

        return BinaryInfo(
            path=path,
            architecture=arch,
            format=fmt,
            interpreter=None,
            compatible=compatible,
            reason=reason,
        )

    # Fallback: check if it's executable and try to run --version
    if binary_path.stat().st_mode & 0o111:
        try:
            result = subprocess.run(
                [str(binary_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # It runs, assume compatible
                return BinaryInfo(
                    path=path,
                    architecture=host_arch,
                    format="unknown",
                    interpreter=None,
                    compatible=True,
                    reason=None,
                )
        except (OSError, subprocess.TimeoutExpired):
            pass

    return BinaryInfo(
        path=path,
        architecture="unknown",
        format="unknown",
        interpreter=None,
        compatible=False,
        reason="Unable to determine binary format or architecture",
    )


def check_installed_binaries(versions: list[str], base_path: str) -> dict[str, BinaryInfo]:
    """Check a list of installed Node versions for binary compatibility.

    Args:
        versions: List of version strings like ["20.11.1", "22.14.0"]
        base_path: Base directory containing version subdirectories (e.g., ~/.nvm/versions/node)

    Returns:
        Dict mapping version string to BinaryInfo
    """
    results: dict[str, BinaryInfo] = {}
    base = Path(base_path)

    for version in versions:
        # Typical nvm layout: base/version/bin/node
        node_bin = base / version / "bin" / "node"
        if not node_bin.exists():
            # Try without version prefix
            node_bin = base / f"v{version}" / "bin" / "node"
        if not node_bin.exists():
            results[version] = BinaryInfo(
                path=str(node_bin),
                architecture="unknown",
                format="unknown",
                interpreter=None,
                compatible=False,
                reason="Node binary not found at expected path",
            )
            continue
        results[version] = analyze_binary(str(node_bin))

    return results


if __name__ == "__main__":
    # Quick manual test
    import sys

    if len(sys.argv) > 1:
        info = analyze_binary(sys.argv[1])
        print(f"Path: {info.path}")
        print(f"Architecture: {info.architecture}")
        print(f"Format: {info.format}")
        print(f"Interpreter: {info.interpreter}")
        print(f"Compatible: {info.compatible}")
        print(f"Reason: {info.reason}")
    else:
        print(f"Host architecture: {host_architecture()}")