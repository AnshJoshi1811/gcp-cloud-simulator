import { apiClient, getCurrentProject } from './client';

export interface BackendService {
  name: string;
  selfLink: string;
  protocol: string;
  portName: string;
  healthChecks: string[];
  backends: Array<{ instanceName: string; zone: string; port: number }>;
  creationTimestamp: string;
}

export interface ForwardingRule {
  name: string;
  selfLink: string;
  IPAddress: string;
  portRange: string;
  target: string;
  creationTimestamp: string;
}

export interface SimulateResult {
  routedTo: string;
  healthy: boolean;
  statusCode?: number;
  error?: string;
}

export async function listBackendServices(project?: string): Promise<BackendService[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ items?: BackendService[] }>(
    `/compute/v1/projects/${proj}/global/backendServices`
  );
  return resp.data.items || [];
}

export async function createHealthCheck(name: string, port: number, project?: string): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.post(`/compute/v1/projects/${proj}/global/healthChecks`, { name, port });
}

export async function createBackendService(
  name: string,
  healthChecks: string[],
  project?: string
): Promise<BackendService> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<BackendService>(
    `/compute/v1/projects/${proj}/global/backendServices`,
    { name, healthChecks }
  );
  return resp.data;
}

export async function addBackend(
  backendServiceName: string,
  instanceName: string,
  zone: string,
  port: number,
  project?: string
): Promise<BackendService> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<BackendService>(
    `/compute/v1/projects/${proj}/global/backendServices/${backendServiceName}/addBackend`,
    { instanceName, zone, port }
  );
  return resp.data;
}

export async function createUrlMap(name: string, defaultService: string, project?: string): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.post(`/compute/v1/projects/${proj}/global/urlMaps`, { name, defaultService });
}

export async function createTargetProxy(name: string, urlMap: string, project?: string): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.post(`/compute/v1/projects/${proj}/global/targetHttpProxies`, { name, urlMap });
}

export async function listForwardingRules(project?: string): Promise<ForwardingRule[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ items?: ForwardingRule[] }>(
    `/compute/v1/projects/${proj}/global/forwardingRules`
  );
  return resp.data.items || [];
}

export async function createForwardingRule(
  name: string,
  target: string,
  portRange: string,
  project?: string
): Promise<ForwardingRule> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<ForwardingRule>(
    `/compute/v1/projects/${proj}/global/forwardingRules`,
    { name, target, portRange }
  );
  return resp.data;
}

export async function simulateRequest(ruleName: string, project?: string): Promise<SimulateResult> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<SimulateResult>(
    `/compute/v1/projects/${proj}/global/forwardingRules/${ruleName}:simulate`
  );
  return resp.data;
}
