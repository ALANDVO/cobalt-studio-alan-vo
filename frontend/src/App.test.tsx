import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import type { Project, Resolution } from "./types";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubApi(handler: (url: string, method: string, init?: RequestInit) => Response | Promise<Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      return Promise.resolve(handler(String(input), method, init));
    }),
  );
}

it("shows the API version and an empty project list", async () => {
  stubApi((url) => {
    if (url.endsWith("/api/version")) return jsonResponse({ version: "9.9.9" });
    return jsonResponse({ items: [], total: 0, limit: 20, offset: 0 });
  });
  render(<App />);
  expect(await screen.findByText("Version 9.9.9")).toBeTruthy();
  expect(screen.getByText("No projects yet. Create one to resolve its Node pin.")).toBeTruthy();
  expect(screen.getByText("Select a project or create one.")).toBeTruthy();
});

it("shows a project load error", async () => {
  stubApi((url) => {
    if (url.endsWith("/api/version")) return jsonResponse({ version: "9.9.9" });
    return jsonResponse({ detail: "Project store unavailable." }, 500);
  });
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Project store unavailable.");
});

it("creates a project and filters the list from the search box", async () => {
  const projects: Project[] = [
    { id: 1, name: "alpha notes", purpose: "notebook UI", created_at: "2026-10-14T00:00:00Z" },
    { id: 2, name: "beta eval", purpose: "score runs", created_at: "2026-10-14T00:00:01Z" },
  ];
  stubApi((url, method, init) => {
    if (url.endsWith("/api/version")) return jsonResponse({ version: "9.9.9" });
    if (method === "POST" && url.endsWith("/api/projects")) {
      const body = JSON.parse(String(init?.body)) as { name: string; purpose: string };
      const created = {
        id: 8,
        name: body.name,
        purpose: body.purpose,
        created_at: "2026-10-14T00:00:02Z",
      };
      projects.unshift(created);
      return jsonResponse(created, 201);
    }
    const query = new URL(url).searchParams.get("q") ?? "";
    const items = projects.filter((project) => project.name.includes(query));
    return jsonResponse({ items, total: items.length, limit: 20, offset: 0 });
  });
  const user = userEvent.setup();
  render(<App />);
  expect(await screen.findByText("alpha notes")).toBeTruthy();
  await user.type(screen.getByLabelText("Project name"), "card site");
  await user.type(screen.getByLabelText("What this toolchain serves"), "model cards");
  await user.click(screen.getByRole("button", { name: "Create project" }));
  expect(await screen.findByRole("button", { name: /card site/ })).toBeTruthy();
  await user.type(screen.getByLabelText("Search projects"), "beta");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => {
    expect(screen.queryByRole("button", { name: /alpha notes/ })).toBeNull();
  });
  expect(screen.getByRole("button", { name: /beta eval/ })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /card site/ })).toBeNull();
});

it("shows a missing install from the API and exports that record", async () => {
  const project: Project = {
    id: 7,
    name: "eval dashboard",
    purpose: "compare checkpoints",
    created_at: "2026-10-14T00:00:00Z",
  };
  const resolution: Resolution = {
    id: 3,
    project_id: 7,
    source: "node-version",
    requested: "22.2.0",
    status: "missing",
    matched: null,
    caller_exit_code: 0,
    explanation: "The release is not installed. Caller exit code stays 0.",
    matches: [],
    ignored: ["Ignored .nvmrc because a higher-precedence pin is set."],
    inputs: { node_version: "22.2.0", nvmrc: "18", package_json: "", installed: ["20.11.1"] },
    binary_info: {},
    lts_snapshot: "2099-01-01",
    lts_latest_codename: "sampleline",
    lts_latest_major: 99,
    created_at: "2026-10-14T00:00:03Z",
  };
  stubApi((url, method) => {
    if (url.endsWith("/api/version")) return jsonResponse({ version: "9.9.9" });
    if (method === "POST" && url.includes("/resolutions")) return jsonResponse(resolution, 201);
    return jsonResponse({ items: [project], total: 1, limit: 20, offset: 0 });
  });
  const createObjectURL = vi.fn(() => "blob:resolution");
  const revokeObjectURL = vi.fn();
  vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
  const downloads: HTMLAnchorElement[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function mockClick(this: HTMLAnchorElement) {
    downloads.push(this);
  });
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: /eval dashboard/ }));
  await user.type(screen.getByLabelText(".node-version"), "22.2.0");
  await user.type(screen.getByLabelText("Installed releases"), "20.11.1");
  await user.click(screen.getByRole("button", { name: "Resolve pin" }));
  expect(await screen.findByText("Not installed")).toBeTruthy();
  expect(screen.getByText("Source").nextElementSibling?.textContent).toBe(".node-version");
  expect(screen.getByText("The release is not installed. Caller exit code stays 0.")).toBeTruthy();
  expect(screen.getByText("Caller exit code").nextElementSibling?.textContent).toBe("0");
  expect(screen.getByText("2099-01-01: sampleline 99")).toBeTruthy();
  expect(screen.getByText("Ignored .nvmrc because a higher-precedence pin is set.")).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Export JSON" }));
  expect(downloads[0]?.download).toBe("resolution-3.json");
  expect(createObjectURL).toHaveBeenCalledOnce();
});
