import { apiClient, getCurrentProject } from './client';

export interface LogEntry {
  logName: string;
  resource: { type: string; labels: Record<string, string> };
  timestamp: string;
  severity: string;
  insertId: string;
  labels: Record<string, string>;
  textPayload?: string;
  jsonPayload?: Record<string, unknown>;
}

export interface LogSink {
  name: string;
  destination: string;
  filter: string;
  createTime: string;
}

export async function listEntries(
  filter = '',
  project?: string,
  pageSize = 100
): Promise<LogEntry[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<{ entries?: LogEntry[] }>('/v2/entries:list', {
    resourceNames: [`projects/${proj}`],
    filter,
    pageSize,
  });
  return resp.data.entries || [];
}

export async function writeEntry(
  logId: string,
  severity: string,
  textPayload: string,
  project?: string
): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.post('/v2/entries:write', {
    logName: `projects/${proj}/logs/${logId}`,
    entries: [{ textPayload, severity }],
  });
}

export async function listSinks(project?: string): Promise<LogSink[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ sinks?: LogSink[] }>(`/v2/projects/${proj}/sinks`);
  return resp.data.sinks || [];
}

export async function createSink(
  name: string,
  destination: string,
  filter = '',
  project?: string
): Promise<LogSink> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<LogSink>(`/v2/projects/${proj}/sinks`, {
    name,
    destination,
    filter,
  });
  return resp.data;
}

export async function deleteSink(sinkId: string, project?: string): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.delete(`/v2/projects/${proj}/sinks/${sinkId}`);
}
