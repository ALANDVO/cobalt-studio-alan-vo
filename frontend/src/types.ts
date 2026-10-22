export type BinaryInfo = {
  version: string;
  path: string;
  architecture: string;
  format: string;
  interpreter: string | null;
  compatible: boolean;
  reason: string | null;
};

export type BinaryCheckInput = {
  installed: string[];
  base_path: string;
};

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
  binary_info: Record<string, BinaryInfo>;
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
