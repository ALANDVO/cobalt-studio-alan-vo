export type Project = {
  id: number;
  name: string;
  purpose: string;
  created_at: string;
};

export type ProjectInput = {
  name: string;
  purpose: string;
};

export type ResolutionInputs = {
  node_version: string;
  nvmrc: string;
  package_json: string;
  installed: string[];
};

export type Resolution = {
  id: number;
  project_id: number;
  source: string;
  requested: string;
  status: string;
  matched: string | null;
  caller_exit_code: number;
  explanation: string;
  matches: string[];
  ignored: string[];
  inputs: ResolutionInputs;
  lts_snapshot: string;
  lts_latest_codename: string;
  lts_latest_major: number;
  created_at: string;
};

export type ResolutionInput = {
  node_version: string;
  nvmrc: string;
  package_json: string;
  installed: string[];
};

export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type VersionInfo = {
  version: string;
};
