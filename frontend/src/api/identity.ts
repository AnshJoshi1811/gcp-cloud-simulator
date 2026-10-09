import { apiClient, getCurrentProject } from './client';

export interface IdentityUser {
  localId: string;
  email: string;
  displayName: string;
  disabled: boolean;
  createdAt: string;
}

export async function listUsers(project?: string): Promise<IdentityUser[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ users?: IdentityUser[] }>(
    `/identitytoolkit/v1/projects/${proj}/accounts`
  );
  return resp.data.users || [];
}

export async function signUp(
  email: string,
  password: string,
  displayName: string,
  project?: string
): Promise<{ localId: string; email: string; idToken: string }> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post(`/identitytoolkit/v1/projects/${proj}/accounts:signUp`, {
    email,
    password,
    displayName,
  });
  return resp.data;
}

export async function disableUser(localId: string, project?: string): Promise<IdentityUser> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<IdentityUser>(
    `/identitytoolkit/v1/projects/${proj}/accounts/${localId}:disable`
  );
  return resp.data;
}

export async function enableUser(localId: string, project?: string): Promise<IdentityUser> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<IdentityUser>(
    `/identitytoolkit/v1/projects/${proj}/accounts/${localId}:enable`
  );
  return resp.data;
}

export async function deleteUser(localId: string, project?: string): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.delete(`/identitytoolkit/v1/projects/${proj}/accounts/${localId}`);
}
