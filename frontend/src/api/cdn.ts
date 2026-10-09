import { apiClient, getCurrentProject } from './client';

export interface BackendBucket {
  name: string;
  selfLink: string;
  bucketName: string;
  cdnPolicy: { cacheMode: string; defaultTtl: number };
  enableCdn: boolean;
  creationTimestamp: string;
}

export async function listBackendBuckets(project?: string): Promise<BackendBucket[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ items?: BackendBucket[] }>(
    `/compute/v1/projects/${proj}/global/backendBuckets`
  );
  return resp.data.items || [];
}

export async function createBackendBucket(
  name: string,
  bucketName: string,
  defaultTtl = 3600,
  project?: string
): Promise<BackendBucket> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<BackendBucket>(
    `/compute/v1/projects/${proj}/global/backendBuckets`,
    { name, bucketName, cdnPolicy: { defaultTtl } }
  );
  return resp.data;
}

export async function deleteBackendBucket(name: string, project?: string): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.delete(`/compute/v1/projects/${proj}/global/backendBuckets/${name}`);
}

export async function invalidateCache(
  name: string,
  path: string | undefined,
  project?: string
): Promise<number> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<{ invalidatedCount: number }>(
    `/compute/v1/projects/${proj}/global/backendBuckets/${name}/invalidateCache`,
    path ? { path } : {}
  );
  return resp.data.invalidatedCount;
}

export function cdnContentUrl(backendBucketName: string, objectPath: string): string {
  const base = apiClient.defaults.baseURL || '';
  return `${base}/cdn/v1/content/${backendBucketName}/${objectPath}`;
}
