import { apiClient, getCurrentProject } from './client';

export interface GatewayRoute {
  path: string;
  method: string;
  backendFunction: string | null;
  backendUrl: string | null;
}

export interface ApiConfig {
  name: string;
  routes: GatewayRoute[];
  createTime: string;
}

export interface Gateway {
  name: string;
  apiConfig: string;
  state: string;
  defaultHostname: string;
  createTime: string;
}

const DEFAULT_LOCATION = 'us-central1';

export async function listGateways(project?: string): Promise<Gateway[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ gateways?: Gateway[] }>(
    `/apigateway/v1/projects/${proj}/locations/${DEFAULT_LOCATION}/gateways`
  );
  return resp.data.gateways || [];
}

export async function createApiConfig(
  apiId: string,
  configId: string,
  routes: GatewayRoute[],
  project?: string
): Promise<ApiConfig> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<ApiConfig>(
    `/apigateway/v1/projects/${proj}/apis/${apiId}/configs`,
    { configId, routes }
  );
  return resp.data;
}

export async function createGateway(
  gatewayId: string,
  apiConfig: string,
  project?: string
): Promise<Gateway> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<Gateway>(
    `/apigateway/v1/projects/${proj}/locations/${DEFAULT_LOCATION}/gateways`,
    { gatewayId, apiConfig }
  );
  return resp.data;
}

export async function deleteGateway(gatewayId: string, project?: string): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.delete(
    `/apigateway/v1/projects/${proj}/locations/${DEFAULT_LOCATION}/gateways/${gatewayId}`
  );
}

export async function testRoute(
  gatewayId: string,
  path: string,
  method = 'GET',
  project?: string
): Promise<unknown> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.request({
    url: `/apigateway/v1/invoke/${proj}/${gatewayId}${path}`,
    method,
  });
  return resp.data;
}
