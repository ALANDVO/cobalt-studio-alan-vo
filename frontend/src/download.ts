import type { Resolution } from "./types";

export function downloadResolution(resolution: Resolution): void {
  const blob = new Blob([JSON.stringify(resolution, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `resolution-${resolution.id}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
