import type { FormEvent } from "react";
import type { Project } from "../types";

type Props = {
  projects: Project[] | null;
  total: number;
  query: string;
  selectedId: number | null;
  name: string;
  purpose: string;
  busy: boolean;
  onQueryChange: (value: string) => void;
  onSearch: (event: FormEvent) => void;
  onNameChange: (value: string) => void;
  onPurposeChange: (value: string) => void;
  onCreate: (event: FormEvent) => void;
  onSelect: (project: Project) => void;
  onLoadMore: () => void;
};

export function ProjectList({
  projects,
  total,
  query,
  selectedId,
  name,
  purpose,
  busy,
  onQueryChange,
  onSearch,
  onNameChange,
  onPurposeChange,
  onCreate,
  onSelect,
  onLoadMore,
}: Props) {
  return (
    <section className="panel" aria-label="Projects">
      <form className="stack" onSubmit={onCreate}>
        <h2>New project</h2>
        <label htmlFor="project-name">Project name</label>
        <input
          id="project-name"
          value={name}
          maxLength={80}
          onChange={(event) => onNameChange(event.target.value)}
          required
        />
        <label htmlFor="project-purpose">What this toolchain serves</label>
        <input
          id="project-purpose"
          value={purpose}
          maxLength={240}
          onChange={(event) => onPurposeChange(event.target.value)}
          placeholder="Evaluation dashboard"
        />
        <button type="submit" disabled={busy}>
          {busy ? "Saving" : "Create project"}
        </button>
      </form>
      <form className="search" onSubmit={onSearch}>
        <label htmlFor="project-search">Search projects</label>
        <div className="search-row">
          <input
            id="project-search"
            value={query}
            maxLength={80}
            onChange={(event) => onQueryChange(event.target.value)}
          />
          <button type="submit">Search</button>
        </div>
      </form>
      {projects === null ? <p className="status-line">Loading projects</p> : null}
      {projects !== null && projects.length === 0 ? (
        <p className="status-line">No projects yet. Create one to resolve its Node pin.</p>
      ) : null}
      {projects !== null && projects.length > 0 ? (
        <ul className="project-list">
          {projects.map((project) => (
            <li key={project.id}>
              <button
                type="button"
                className="project-button"
                aria-pressed={project.id === selectedId}
                onClick={() => onSelect(project)}
              >
                <span className="project-name">{project.name}</span>
                <span className="project-purpose">{project.purpose || "No purpose recorded"}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {projects !== null && projects.length < total ? (
        <button type="button" onClick={onLoadMore}>
          Load more
        </button>
      ) : null}
      {projects !== null ? (
        <p className="meta">
          Showing {projects.length} of {total}
        </p>
      ) : null}
    </section>
  );
}
