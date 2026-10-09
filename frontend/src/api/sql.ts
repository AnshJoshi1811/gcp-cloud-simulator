import { apiClient, getCurrentProject } from './client';

export interface SqlInstance {
  name: string;
  project: string;
  region: string;
  databaseVersion: 'POSTGRES_15' | 'MYSQL_8_0';
  settings: { tier: string };
  state: 'PENDING_CREATE' | 'RUNNABLE' | 'STOPPED' | 'FAILED' | 'DELETED';
  createTime: string;
  connectionName: string;
  ipAddresses: Array<{ type: string; ipAddress: string }>;
  hostPort: number | null;
  enginePort: number;
  selfLink: string;
}

export interface SqlDatabase {
  name: string;
  project: string;
  instance: string;
  charset: string;
}

export interface SqlUser {
  name: string;
  project: string;
  instance: string;
  password?: string;
}

export async function listInstances(project?: string): Promise<SqlInstance[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ items?: SqlInstance[] }>(`/sql/v1beta4/projects/${proj}/instances`);
  return resp.data.items || [];
}

export async function createInstance(payload: {
  name: string;
  region?: string;
  databaseVersion?: string;
  tier?: string;
  project?: string;
}): Promise<SqlInstance> {
  const proj = payload.project || getCurrentProject();
  const resp = await apiClient.post<SqlInstance>(`/sql/v1beta4/projects/${proj}/instances`, {
    name: payload.name,
    region: payload.region || 'us-central1',
    databaseVersion: payload.databaseVersion || 'POSTGRES_15',
    settings: { tier: payload.tier || 'db-f1-micro' },
  });
  return resp.data;
}

export async function deleteInstance(instanceName: string, project?: string): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.delete(`/sql/v1beta4/projects/${proj}/instances/${instanceName}`);
}

export async function stopInstance(instanceName: string, project?: string): Promise<SqlInstance> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<SqlInstance>(
    `/sql/v1beta4/projects/${proj}/instances/${instanceName}:stop`
  );
  return resp.data;
}

export async function startInstance(instanceName: string, project?: string): Promise<SqlInstance> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<SqlInstance>(
    `/sql/v1beta4/projects/${proj}/instances/${instanceName}:start`
  );
  return resp.data;
}

export async function listDatabases(instanceName: string, project?: string): Promise<SqlDatabase[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ items?: SqlDatabase[] }>(
    `/sql/v1beta4/projects/${proj}/instances/${instanceName}/databases`
  );
  return resp.data.items || [];
}

export async function createDatabase(
  instanceName: string,
  name: string,
  project?: string
): Promise<SqlDatabase> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<SqlDatabase>(
    `/sql/v1beta4/projects/${proj}/instances/${instanceName}/databases`,
    { name }
  );
  return resp.data;
}

export async function listUsers(instanceName: string, project?: string): Promise<SqlUser[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ items?: SqlUser[] }>(
    `/sql/v1beta4/projects/${proj}/instances/${instanceName}/users`
  );
  return resp.data.items || [];
}

export async function createUser(
  instanceName: string,
  name: string,
  project?: string
): Promise<SqlUser> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<SqlUser>(
    `/sql/v1beta4/projects/${proj}/instances/${instanceName}/users`,
    { name }
  );
  return resp.data;
}
