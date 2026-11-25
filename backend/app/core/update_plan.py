"""Plan a manager update that checks out a tagged Node version.

An update plan names a tag to check out and does not stop on a detached
FETCH_HEAD.  Already-installed Node releases are left in place.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UpdatePlan:
    """An update plan that names a tag to check out."""

    tag: str
    """The git tag to check out (e.g. "v20.11.1")."""

    resolve_to_dir: str = field(repr=False, default="/tmp/cobalt-studio-work")
    """Directory where the tag checkout will be attempted."""

    leave_installed: bool = field(repr=False, default=True)
    """If True, already-installed Node releases are preserved."""

    fetch_head_behavior: str = field(repr=False, default="detach-ok")
    """How to handle a detached FETCH_HEAD: "detach-ok" means do not stop."""


def make_update_plan(tag: str, *, leave_installed: bool = True) -> UpdatePlan:
    """Construct an update plan for checking out *tag*.

    The returned plan names the tag and is configured so that a detached
    FETCH_HEAD will not cause the operation to stop; installed releases are
    left untouched.
    """
    if not tag.startswith("v"):
        tag = f"v{tag}"
    return UpdatePlan(
        tag=tag,
        leave_installed=leave_installed,
        fetch_head_behavior="detach-ok",
    )


def plan_description(plan: UpdatePlan) -> str:
    """Human-readable description of what the plan does."""
    parts: list = [
        f"checkout tag {plan.tag}",
    ]
    if plan.leave_installed:
        parts.append("leave installed releases in place")
    parts.append("continue if FETCH_HEAD is detached")
    return " ".join(parts)
