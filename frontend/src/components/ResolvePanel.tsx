import type { FormEvent } from "react";
import { downloadResolution } from "../download";
import type { Project, Resolution } from "../types";

type Props = {
  project: Project | null;
  nodeVersion: string;
  nvmrc: string;
  packageJson: string;
  installed: string;
  resolution: Resolution | null;
  busy: boolean;
  onNodeVersion: (value: string) => void;
  onNvmrc: (value: string) => void;
  onPackageJson: (value: string) => void;
  onInstalled: (value: string) => void;
  onResolve: (event: FormEvent) => void;
};

const SOURCE_LABEL: Record<string, string> = {
  "node-version": ".node-version",
  nvmrc: ".nvmrc",
  engines: "package.json engines.node",
};

function statusLabel(status: string): string {
  if (status === "satisfied") return "Satisfied";
  if (status === "missing") return "Not installed";
  if (status === "invalid") return "Invalid pin";
  return status;
}

export function ResolvePanel({
  project,
  nodeVersion,
  nvmrc,
  packageJson,
  installed,
  resolution,
  busy,
  onNodeVersion,
  onNvmrc,
  onPackageJson,
  onInstalled,
  onResolve,
}: Props) {
  if (project === null) {
    return (
      <section className="panel" aria-label="Resolution">
        <h2>Resolve a pin</h2>
        <p className="status-line">Select a project or create one.</p>
      </section>
    );
  }
  return (
    <section className="panel" aria-label="Resolution">
      <h2>{project.name}</h2>
      <p className="meta">{project.purpose || "No purpose recorded"}</p>
      <form className="stack" onSubmit={onResolve}>
        <label htmlFor="node-version">.node-version</label>
        <textarea
          id="node-version"
          value={nodeVersion}
          onChange={(event) => onNodeVersion(event.target.value)}
          rows={3}
          spellCheck={false}
          placeholder={"22.14.0"}
        />
        <label htmlFor="nvmrc">.nvmrc</label>
        <textarea
          id="nvmrc"
          value={nvmrc}
          onChange={(event) => onNvmrc(event.target.value)}
          rows={3}
          spellCheck={false}
          placeholder={"lts/*"}
        />
        <label htmlFor="package-json">package.json</label>
        <textarea
          id="package-json"
          value={packageJson}
          onChange={(event) => onPackageJson(event.target.value)}
          rows={5}
          spellCheck={false}
          placeholder={'{\n  "engines": { "node": ">=20 <22" }\n}'}
        />
        <label htmlFor="installed">Installed releases</label>
        <textarea
          id="installed"
          value={installed}
          onChange={(event) => onInstalled(event.target.value)}
          rows={5}
          spellCheck={false}
          placeholder={"20.18.1\n22.14.0\n24.11.1"}
        />
        <button type="submit" disabled={busy}>
          {busy ? "Resolving" : "Resolve pin"}
        </button>
      </form>
      {resolution ? (
        <article className={`result result-${resolution.status}`} aria-live="polite">
          <h3>{statusLabel(resolution.status)}</h3>
          <dl>
            <div>
              <dt>Source</dt>
              <dd>{SOURCE_LABEL[resolution.source] ?? resolution.source}</dd>
            </div>
            <div>
              <dt>Requested</dt>
              <dd>{resolution.requested || "none"}</dd>
            </div>
            <div>
              <dt>Matched</dt>
              <dd>{resolution.matched ?? "none"}</dd>
            </div>
            <div>
              <dt>Caller exit code</dt>
              <dd>{resolution.caller_exit_code}</dd>
            </div>
            <div>
              <dt>LTS snapshot</dt>
              <dd>
                {resolution.lts_snapshot}: {resolution.lts_latest_codename} {resolution.lts_latest_major}
              </dd>
            </div>
          </dl>
          <p>{resolution.explanation}</p>
          {resolution.ignored.length > 0 ? (
            <ul>
              {resolution.ignored.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
          {resolution.matches.length > 0 ? (
            <p className="meta">Also matched: {resolution.matches.join(", ")}</p>
          ) : null}
          <button type="button" onClick={() => downloadResolution(resolution)}>
            Export JSON
          </button>
        </article>
      ) : null}
    </section>
  );
}
