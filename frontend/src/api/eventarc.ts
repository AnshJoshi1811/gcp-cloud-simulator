import { apiClient, getCurrentProject } from './client';

export interface Trigger {
  name: string;
  eventFilters: Array<{ attribute: string; value: string }>;
  transport: { pubsub: { topic: string } };
  destination: { cloudFunction: string };
  state: 'ACTIVE' | 'FAILED';
  eventCount: number;
  lastError: string | null;
  createTime: string;
}

const DEFAULT_LOCATION = 'us-central1';

export async function listTriggers(project?: string): Promise<Trigger[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ triggers?: Trigger[] }>(
    `/eventarc/v1/projects/${proj}/locations/${DEFAULT_LOCATION}/triggers`
  );
  return resp.data.triggers || [];
}

export async function createTrigger(
  triggerId: string,
  topic: string,
  destinationFunction: string,
  project?: string
): Promise<Trigger> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<Trigger>(
    `/eventarc/v1/projects/${proj}/locations/${DEFAULT_LOCATION}/triggers`,
    { triggerId, topic, destinationFunction }
  );
  return resp.data;
}

export async function deleteTrigger(triggerId: string, project?: string): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.delete(
    `/eventarc/v1/projects/${proj}/locations/${DEFAULT_LOCATION}/triggers/${triggerId}`
  );
}
