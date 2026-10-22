import type { BinaryCheckInput, BinaryInfo, Page, Project, ProjectInput, Resolution, ResolutionInput, VersionInfo } from "./types";

const base = (import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000").replace(/\/$/, "");

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
            return item.msg;
          }
          return "Invalid request.";
        })
        .join(" ");
    }
  } catch {
    return `Request failed (${response.status}).`;
  }
  return `Request failed (${response.status}).`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as T;
}

export function fetchVersion(): Promise<VersionInfo> {
  return request<VersionInfo>("/api/version");
}

export function fetchProjects(query: string, offset: number): Promise<Page<Project>> {
  const params = new URLSearchParams({ limit: "20", offset: String(offset) });
  if (query.trim()) {
    params.set("q", query.trim());
  }
  return request<Page<Project>>(`/api/projects?${params.toString()}`);
}

export function createProject(input: ProjectInput): Promise<Project> {
  return request<Project>("/api/projects", { method: "POST", body: JSON.stringify(input) });
}

export function createResolution(projectId: number, input: ResolutionInput): Promise<Resolution> {
  return request<Resolution>(`/api/projects/${projectId}/resolutions`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}
export function checkBinaries(input: BinaryCheckInput): Promise<BinaryInfo[]> {
  return request<BinaryInfo[]>("/api/binary/check", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
