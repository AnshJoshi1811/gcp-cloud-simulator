import { apiClient, getCurrentProject } from './client';

export type FirestoreValue =
  | { stringValue: string }
  | { integerValue: string }
  | { doubleValue: number }
  | { booleanValue: boolean }
  | { nullValue: null }
  | { mapValue: { fields: Record<string, FirestoreValue> } }
  | { arrayValue: { values: FirestoreValue[] } };

export interface FirestoreDocument {
  name: string;
  fields: Record<string, FirestoreValue>;
  createTime: string;
  updateTime: string;
}

const DEFAULT_DATABASE = '(default)';

export function plainToFields(obj: Record<string, unknown>): Record<string, FirestoreValue> {
  const fields: Record<string, FirestoreValue> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (typeof value === 'string') fields[key] = { stringValue: value };
    else if (typeof value === 'number') fields[key] = { integerValue: String(value) };
    else if (typeof value === 'boolean') fields[key] = { booleanValue: value };
    else fields[key] = { stringValue: String(value) };
  }
  return fields;
}

export function fieldsToPlain(fields: Record<string, FirestoreValue>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(fields || {})) {
    if ('stringValue' in value) result[key] = value.stringValue;
    else if ('integerValue' in value) result[key] = value.integerValue;
    else if ('doubleValue' in value) result[key] = value.doubleValue;
    else if ('booleanValue' in value) result[key] = value.booleanValue;
    else result[key] = null;
  }
  return result;
}

export async function listDocuments(
  collectionId: string,
  project?: string,
  database = DEFAULT_DATABASE
): Promise<FirestoreDocument[]> {
  const proj = project || getCurrentProject();
  const resp = await apiClient.get<{ documents?: FirestoreDocument[] }>(
    `/v1/projects/${proj}/databases/${database}/documents/${collectionId}`
  );
  return resp.data.documents || [];
}

export async function createDocument(
  collectionId: string,
  data: Record<string, unknown>,
  documentId?: string,
  project?: string,
  database = DEFAULT_DATABASE
): Promise<FirestoreDocument> {
  const proj = project || getCurrentProject();
  const qs = documentId ? `?documentId=${documentId}` : '';
  const resp = await apiClient.post<FirestoreDocument>(
    `/v1/projects/${proj}/databases/${database}/documents/${collectionId}${qs}`,
    { fields: plainToFields(data) }
  );
  return resp.data;
}

export async function deleteDocument(
  collectionId: string,
  documentId: string,
  project?: string,
  database = DEFAULT_DATABASE
): Promise<void> {
  const proj = project || getCurrentProject();
  await apiClient.delete(
    `/v1/projects/${proj}/databases/${database}/documents/${collectionId}/${documentId}`
  );
}
