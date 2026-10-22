# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

binary-compat-check

## Roadmap

### resolve-project-pin — Resolve a project Node pin against installed releases

Status: done

Acceptance:
- Creating a project and submitting .node-version, .nvmrc, and package.json stores a resolution that names the winning source.
- A partial version or range selects the highest installed release that satisfies it.
- A well-formed pin whose release is not installed is stored with status missing and caller exit code 0.
- An unreadable pin is stored as invalid and does not fall through to a lower-precedence file.
- The project list can be searched and a resolution can be read back through the API.
- The UI loads projects, creates one, searches, shows the resolution from the API, and exports that record.

Implementation: `backend/app/core/semver.py`, `backend/app/core/resolver.py`, `backend/app/api/routes.py`, `backend/app/main.py`, `frontend/src/App.tsx`, `frontend/src/api.ts`

Tests: `backend/tests/test_resolver.py`, `backend/tests/test_api.py`, `backend/tests/test_evaluate.py`, `frontend/src/App.test.tsx`

### binary-compat-check — Report when a Node binary exists but cannot start

Status: done

Acceptance:
- A catalog entry can record the host architecture and the binary's ELF or Mach-O interpreter.
- A file that exists but does not match the host is reported as incompatible instead of as a missing path.

Implementation: `backend/app/core/binary.py`, `backend/app/core/resolver.py`, `backend/app/models/schemas.py`, `backend/app/api/routes.py`, `backend/app/services/store.py`, `frontend/src/types.ts`, `frontend/src/api.ts`, `frontend/src/components/ResolvePanel.tsx`, `frontend/src/styles.css`

Tests: `backend/tests/test_binary.py`, `backend/tests/test_api.py`, `backend/tests/test_resolver.py`, `frontend/src/App.test.tsx`

### shell-activation — Emit shell activation that stays successful when a pin is missing

Status: planned

Acceptance:
- A bash or zsh snippet applies a satisfied resolution and returns exit 0 when the pin is only missing.
- A fish snippet is generated from the same resolution.
- A non-interactive environment file exposes the selected Node bin directory without sourcing an interactive profile.

### manager-update-plan — Plan a manager update that checks out a tag

Status: planned

Acceptance:
- An update plan names a tag to check out and does not stop on a detached FETCH_HEAD.
- The plan leaves already installed Node releases in place.

### oidc-access — Require OIDC login for project data

Status: planned

Acceptance:
- Unauthenticated calls to project and resolution routes are rejected.
- A viewer cannot create projects or resolutions, and an operator can.
- Login uses authorization-code PKCE against an operator-configured OIDC provider, with a documented Keycloak realm for SAML brokering.

### advisory-explanation — Optional grounded explanation of a stored resolution

Status: planned

Acceptance:
- An explanation is requested only when the operator turns it on and LLM_API_KEY is set on the server.
- The prompt is built from the stored resolution, and a provider failure is returned as an error without inventing a match.

