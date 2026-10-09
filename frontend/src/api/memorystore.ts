import { apiClient, getCurrentProject } from './client';

export interface RedisInstance {
  name: string;
  tier: 'BASIC' | 'STANDARD_HA';
  memorySizeGb: number;
  redisVersion: string;
  state: 'CREATING' | 'READY' | 'FAILED' | 'DELETING';
  createTime: string;
  host: string | null;
  port: number;
  hostPort: number | null;
  labels: Record<string, string>;
}

const DEFAULT_LOCATION = 'us-central1';

export async function listInstances(
  project?: string,
  location = DEFAULT_LOCATION
): Promise<RedisInstance[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ instances?: RedisInstance[] }>(
    `/v1/projects/${proj}/locations/${location}/instances`
  );
  return resp.data.instances || [];
}

export async function createInstance(payload: {
  instanceId: string;
  tier?: string;
  memorySizeGb?: number;
  project?: string;
  location?: string;
}): Promise<RedisInstance> {
  const proj = payload.project || getCurrentProject();
  const location = payload.location || DEFAULT_LOCATION;
  const resp = await apiClient.post<RedisInstance>(
    `/v1/projects/${proj}/locations/${location}/instances`,
    {
      instanceId: payload.instanceId,
      tier: payload.tier || 'BASIC',
      memorySizeGb: payload.memorySizeGb || 1,
    }
  );
  return resp.data;
}

export async function deleteInstance(
  instanceId: string,
  project?: string,
  location = DEFAULT_LOCATION
): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.delete(`/v1/projects/${proj}/locations/${location}/instances/${instanceId}`);
}
