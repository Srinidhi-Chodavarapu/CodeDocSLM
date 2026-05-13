// Type definitions for slm_docgen API

export interface GenerateDocRequest {
  code: string;
  language: string;
  style?: string;
}

export interface GenerateDocResponse {
  documentation: string;
  language: string;
  style: string;
  latency_ms: number;
}

export interface ProjectStatsResponse {
  files_processed: number;
  units_documented: number;
  total_latency_ms: number;
  languages: string[];
}

export interface GenerateProjectResponse {
  readme: string;
  modified_files: { [filePath: string]: string };
  stats: ProjectStatsResponse;
}

export interface GenerateFileResponse {
  modified_source: string;
  units_documented: number;
  language: string;
  latency_ms: number;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  adapter_dir: string;
}

export interface InfoResponse {
  title: string;
  version: string;
  supported_languages: string[];
  model_info: {
    base_model: string;
    adapter_dir: string;
    loaded: boolean;
  };
  config: {
    max_files: number;
    max_zip_mb: number;
    load_in_4bit: boolean;
  };
}

export enum ServerStatus {
  Stopped = 'stopped',
  Starting = 'starting',
  LoadingModel = 'loading-model',
  Ready = 'ready',
  Generating = 'generating',
  Error = 'error'
}

export interface ServerConfig {
  port: number;
  pythonPath: string;
  adapterPath: string;
  enable4bit: boolean;
  maxFiles: number;
}
