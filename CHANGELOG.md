# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0

First checkpoint of Cobalt Studio.

- Resolve a Node pin from `.node-version`, then `.nvmrc`, then `package.json` `engines.node`.
- Select the highest installed release that satisfies an exact version, partial version, comparator range, `lts/*`, or `lts/<codename>`.
- Store a missing install with caller exit code 0, and store an unreadable pin as invalid without falling through.
- Persist projects, resolutions, and an audit row in SQLite, with search and pagination.
- Add a local web UI to create a project, search, resolve, and export the API record.
- Score the resolver against the hand-labeled cases in `backend/app/data/pin_cases.json`.
