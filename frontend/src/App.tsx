import { useEffect, useState, type FormEvent } from "react";
import { createProject, createResolution, fetchProjects, fetchVersion } from "./api";
import { ProjectList } from "./components/ProjectList";
import { ResolvePanel } from "./components/ResolvePanel";
import type { Project, Resolution } from "./types";

export function App() {
  const [version, setVersion] = useState("");
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [selected, setSelected] = useState<Project | null>(null);
  const [nodeVersion, setNodeVersion] = useState("");
  const [nvmrc, setNvmrc] = useState("");
  const [packageJson, setPackageJson] = useState("");
  const [installed, setInstalled] = useState("");
  const [basePath, setBasePath] = useState("/home/node/.nvm/versions/node");
  const [resolution, setResolution] = useState<Resolution | null>(null);
  const [saving, setSaving] = useState(false);
  const [resolving, setResolving] = useState(false);

  async function loadProjects(nextQuery: string, offset: number, append: boolean) {
    const page = await fetchProjects(nextQuery, offset);
    setTotal(page.total);
    setProjects((current) => (append && current ? [...current, ...page.items] : page.items));
    setActiveQuery(nextQuery);
  }

  useEffect(() => {
    let cancelled = false;
    fetchVersion()
      .then((info) => {
        if (!cancelled) setVersion(info.version);
      })
      .catch(() => {
        if (!cancelled) setVersion("");
      });
    loadProjects("", 0, false).catch((err: unknown) => {
      if (cancelled) return;
      setProjects([]);
      setError(err instanceof Error ? err.message : "Could not load projects.");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await createProject({ name: name.trim(), purpose: purpose.trim() });
      setName("");
      setPurpose("");
      setSelected(created);
      setResolution(null);
      await loadProjects(activeQuery, 0, false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not create the project.");
    } finally {
      setSaving(false);
    }
  }

  function onSearch(event: FormEvent) {
    event.preventDefault();
    setError(null);
    loadProjects(query, 0, false).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Could not search projects.");
    });
  }

  function onLoadMore() {
    const offset = projects?.length ?? 0;
    loadProjects(activeQuery, offset, true).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Could not load more projects.");
    });
  }

  async function onResolve(event: FormEvent) {
    event.preventDefault();
    if (selected === null) return;
    setResolving(true);
    setError(null);
    try {
      const created = await createResolution(selected.id, {
        node_version: nodeVersion,
        nvmrc,
        package_json: packageJson,
        installed: installed
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter((line) => line.length > 0),
      });
      setResolution(created);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not resolve the pin.");
    } finally {
      setResolving(false);
    }
  }

  return (
    <div className="page">
      <header className="masthead">
        <div>
          <p className="eyebrow">Node pin resolver</p>
          <h1>Cobalt Studio</h1>
        </div>
        <p className="version">{version ? `Version ${version}` : "Version unavailable"}</p>
      </header>
      <p className="lede">
        Paste the Node pins from a machine-learning project and the releases already installed. Cobalt Studio
        picks one pin and the highest installed release that satisfies it.
      </p>
      {error ? (
        <p className="banner" role="alert">
          {error}
        </p>
      ) : null}
      <main className="layout">
        <ProjectList
          projects={projects}
          total={total}
          query={query}
          selectedId={selected?.id ?? null}
          name={name}
          purpose={purpose}
          busy={saving}
          onQueryChange={setQuery}
          onSearch={onSearch}
          onNameChange={setName}
          onPurposeChange={setPurpose}
          onCreate={(event) => {
            void onCreate(event);
          }}
          onSelect={(project) => {
            setSelected(project);
            setResolution(null);
          }}
          onLoadMore={onLoadMore}
        />
        <ResolvePanel
          project={selected}
          nodeVersion={nodeVersion}
          nvmrc={nvmrc}
          packageJson={packageJson}
          installed={installed}
          resolution={resolution}
          busy={resolving}
          onNodeVersion={setNodeVersion}
          onNvmrc={setNvmrc}
          onPackageJson={setPackageJson}
          onInstalled={setInstalled}
          onBasePath={setBasePath}
          basePath={basePath}
          onResolve={(event) => {
            void onResolve(event);
          }}
        />
      </main>
    </div>
  );
}
