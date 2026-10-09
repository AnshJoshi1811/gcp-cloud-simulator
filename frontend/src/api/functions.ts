import { apiClient, getCurrentProject } from './client';

export interface CloudFunction {
  name: string;
  entryPoint: string;
  runtime: string;
  state: 'DEPLOYING' | 'ACTIVE' | 'FAILED' | 'DELETING';
  updateTime: string;
  httpsTrigger: { url: string };
  environmentVariables: Record<string, string>;
  invocationCount: number;
  lastError: string | null;
}

const DEFAULT_LOCATION = 'us-central1';

export async function listFunctions(
  project?: string,
  location = DEFAULT_LOCATION
): Promise<CloudFunction[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ functions?: CloudFunction[] }>(
    `/functions/v1/projects/${proj}/locations/${location}/functions`
  );
  return resp.data.functions || [];
}

export async function deployFunction(payload: {
  name: string;
  entryPoint: string;
  sourceCode: string;
  runtime?: string;
  project?: string;
  location?: string;
}): Promise<CloudFunction> {
  const proj = payload.project || getCurrentProject();
  const location = payload.location || DEFAULT_LOCATION;
  const resp = await apiClient.post<CloudFunction>(
    `/functions/v1/projects/${proj}/locations/${location}/functions`,
    {
      name: payload.name,
      entryPoint: payload.entryPoint,
      sourceCode: payload.sourceCode,
      runtime: payload.runtime || 'python312',
    }
  );
  return resp.data;
}

export async function deleteFunction(
  name: string,
  project?: string,
  location = DEFAULT_LOCATION
): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.delete(`/functions/v1/projects/${proj}/locations/${location}/functions/${name}`);
}

export async function invokeFunction(
  name: string,
  body: Record<string, unknown>,
  project?: string,
  location = DEFAULT_LOCATION
): Promise<unknown> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post(`/functions/v1/invoke/${proj}/${location}/${name}`, body);
  return resp.data;
}
