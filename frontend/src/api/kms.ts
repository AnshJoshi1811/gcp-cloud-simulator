import { apiClient, getCurrentProject } from './client';

export interface KeyRing {
  name: string;
  createTime: string;
}

export interface CryptoKeyVersion {
  name: string;
  state: 'PENDING_GENERATION' | 'ENABLED' | 'DISABLED' | 'DESTROYED' | 'DESTROY_SCHEDULED';
  protectionLevel: string;
  algorithm: string;
  createTime: string;
  destroyTime?: string;
}

export interface CryptoKey {
  name: string;
  purpose: string;
  createTime: string;
  labels: Record<string, string>;
  primary?: CryptoKeyVersion;
  rotationPeriod?: string;
}

const DEFAULT_LOCATION = 'us-central1';

export async function listKeyRings(project?: string, location = DEFAULT_LOCATION): Promise<KeyRing[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ keyRings?: KeyRing[] }>(
    `/v1/projects/${proj}/locations/${location}/keyRings`
  );
  return resp.data.keyRings || [];
}

export async function createKeyRing(
  keyRingId: string,
  project?: string,
  location = DEFAULT_LOCATION
): Promise<KeyRing> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<KeyRing>(
    `/v1/projects/${proj}/locations/${location}/keyRings?keyRingId=${keyRingId}`
  );
  return resp.data;
}

export async function listCryptoKeys(
  keyRingId: string,
  project?: string,
  location = DEFAULT_LOCATION
): Promise<CryptoKey[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ cryptoKeys?: CryptoKey[] }>(
    `/v1/projects/${proj}/locations/${location}/keyRings/${keyRingId}/cryptoKeys`
  );
  return resp.data.cryptoKeys || [];
}

export async function createCryptoKey(
  keyRingId: string,
  cryptoKeyId: string,
  purpose = 'ENCRYPT_DECRYPT',
  project?: string,
  location = DEFAULT_LOCATION
): Promise<CryptoKey> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<CryptoKey>(
    `/v1/projects/${proj}/locations/${location}/keyRings/${keyRingId}/cryptoKeys?cryptoKeyId=${cryptoKeyId}`,
    { purpose }
  );
  return resp.data;
}

export async function encrypt(
  keyRingId: string,
  cryptoKeyId: string,
  plaintextBase64: string,
  project?: string,
  location = DEFAULT_LOCATION
): Promise<{ ciphertext: string }> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<{ ciphertext: string }>(
    `/v1/projects/${proj}/locations/${location}/keyRings/${keyRingId}/cryptoKeys/${cryptoKeyId}:encrypt`,
    { plaintext: plaintextBase64 }
  );
  return resp.data;
}

export async function decrypt(
  keyRingId: string,
  cryptoKeyId: string,
  ciphertextBase64: string,
  project?: string,
  location = DEFAULT_LOCATION
): Promise<{ plaintext: string }> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.post<{ plaintext: string }>(
    `/v1/projects/${proj}/locations/${location}/keyRings/${keyRingId}/cryptoKeys/${cryptoKeyId}:decrypt`,
    { ciphertext: ciphertextBase64 }
  );
  return resp.data;
}
