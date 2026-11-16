"""Shell activation snippets for Node pin resolutions.

Provides bash, zsh, and fish snippet generation for resolved Node versions.
Also provides a non-interactive environment file for CI/CD contexts.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class ShellActivation:
    """Hold a resolved pin and generate shell snippets for it."""

    source: str
    """Which pin file produced the resolution: "node-version", "nvmrc", or "package.json engines.node"."""

    selected_version: str
    """The Node.js version string that was selected (e.g. "20.11.1")."""

    bin_dir: str
    """Path to the directory containing the node binary for the selected version."""

    def bash_snippet(self) -> str:
        """Return a bash snippet that sets NODE_VERSION and PATH.

        The snippet is safe to source; it returns exit 0 even when the
        resolved version is "missing" (caller should check status separately).
        """
        lines = [
            "# Cobalt Studio: resolved Node version",
            'export NODE_VERSION=' + self.selected_version,
            'export NODE_BIN_DIR=' + self.bin_dir,
            # Prepend the binary directory to PATH only if it exists
            'if [ -d "$NODE_BIN_DIR" ]; then',
            '    export PATH="$NODE_BIN_DIR:$PATH"',
            'fi',
            "# End Cobalt Studio resolution",
        ]
        return "\n".join(lines)

    def zsh_snippet(self) -> str:
        """Return a zsh snippet that sets NODE_VERSION and PATH."""
        lines = [
            "# Cobalt Studio: resolved Node version",
            'export NODE_VERSION=' + self.selected_version,
            'export NODE_BIN_DIR=' + self.bin_dir,
            'if [ -d "$NODE_BIN_DIR" ]; then',
            '    export PATH="$NODE_BIN_DIR:$PATH"',
            'fi',
            "# End Cobalt Studio resolution",
        ]
        return "\n".join(lines)

    def fish_snippet(self) -> str:
        """Return a fish snippet that sets NODE_VERSION and PATH."""
        lines = [
            "# Cobalt Studio: resolved Node version",
            'set -g NODE_VERSION ' + self.selected_version,
            'set -g NODE_BIN_DIR ' + self.bin_dir,
            'if test -d $NODE_BIN_DIR',
            '    set -U PATH $NODE_BIN_DIR $PATH',
            'end',
            "# End Cobalt Studio resolution",
        ]
        return "\n".join(lines)

    def env_file(self, path: str) -> None:
        """Write a non-interactive environment file at *path*.

        The file contains only the bare variables needed by CI/CD pipelines;
        it does NOT source any interactive profile (e.g. ~/.bashrc or
        ~/.zshrc) so that non-interactive shells (cron, CI runners) work
        without side-effects.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            "NODE_VERSION=" + self.selected_version + "\n"
            "NODE_BIN_DIR=" + self.bin_dir + "\n"
        )


def activation_from_resolution(
    resolution: "Resolution",
) -> ShellActivation:
    """Convert a resolver :class:`Resolution` into a :class:`ShellActivation`.

    The :class:`Resolution` carries the source, selected version, and binary
    information; this function extracts those fields and builds the paths
    required for shell snippets.
    """
    from app.core.resolver import Resolution as _Resolution

    if not isinstance(resolution, _Resolution):
        raise TypeError("expected a resolver Resolution")

    # Use `matched` if available; otherwise fall back to the requested version
    selected = resolution.matched or resolution.requested or "unknown"
    bin_dir = resolution.binary_info.get("path", "") or ""

    return ShellActivation(
        source=resolution.source,
        selected_version=selected,
        bin_dir=bin_dir,
    )
