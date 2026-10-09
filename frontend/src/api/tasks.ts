import { apiClient, getCurrentProject } from './client';

export interface Queue {
  name: string;
  state: 'RUNNING' | 'PAUSED' | 'DISABLED';
  rateLimits: {
    maxDispatchesPerSecond: number;
    maxConcurrentDispatches: number;
  };
}

export interface Task {
  name: string;
  httpRequest: {
    url: string;
    httpMethod?: string;
    headers?: Record<string, string>;
    body?: string;
  };
  scheduleTime: string;
  createTime: string;
  dispatchCount: number;
  responseCount: number;
  state: 'SCHEDULED' | 'DISPATCHED' | 'SUCCEEDED' | 'FAILED';
  lastAttemptResult?: string | null;
}

const DEFAULT_LOCATION = 'us-central1';

export async function listQueues(project?: string, location = DEFAULT_LOCATION): Promise<Queue[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ queues?: Queue[] }>(
    `/v2/projects/${proj}/locations/${location}/queues`
  );
  return resp.data.queues || [];
}

export async function createQueue(
  queueId: string,
  project?: string,
  location = DEFAULT_LOCATION
): Promise<Queue> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<Queue>(
    `/v2/projects/${proj}/locations/${location}/queues`,
    { queueId }
  );
  return resp.data;
}

export async function deleteQueue(queueName: string): Promise<void> {
  await apiClient.delete(`/v2/${queueName}`);
}

export async function pauseQueue(queueName: string): Promise<Queue> {
  const resp = await apiClient.post<Queue>(`/v2/${queueName}:pause`);
  return resp.data;
}

export async function resumeQueue(queueName: string): Promise<Queue> {
  const resp = await apiClient.post<Queue>(`/v2/${queueName}:resume`);
  return resp.data;
}

export async function listTasks(queueName: string): Promise<Task[]> {
  const resp = await apiClient.get<{ tasks?: Task[] }>(`/v2/${queueName}/tasks`);
  return resp.data.tasks || [];
}

export async function createTask(
  queueName: string,
  url: string,
  httpMethod = 'POST'
): Promise<Task> {
  const resp = await apiClient.post<Task>(`/v2/${queueName}/tasks`, {
    task: { httpRequest: { url, httpMethod } },
  });
  return resp.data;
}

export async function deleteTask(taskName: string): Promise<void> {
  await apiClient.delete(`/v2/${taskName}`);
}

export async function runTaskNow(taskName: string): Promise<Task> {
  const resp = await apiClient.post<Task>(`/v2/${taskName}:run`);
  return resp.data;
}
