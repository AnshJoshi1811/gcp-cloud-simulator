import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import {
  listDocuments,
  createDocument,
  deleteDocument,
  fieldsToPlain,
  FirestoreDocument,
} from '../api/firestore';
import { Loader2, Plus, RefreshCw, FolderTree, Trash2 } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

export default function FirestoreDashboardPage() {
  const { currentProject } = useProject();

  const [collectionId, setCollectionId] = useState('users');
  const [documents, setDocuments] = useState<FirestoreDocument[]>([]);
  const [loading, setLoading] = useState(true);

  const [showCreate, setShowCreate] = useState(false);
  const [docId, setDocId] = useState('');
  const [jsonBody, setJsonBody] = useState('{\n  "name": "Alice",\n  "age": 30\n}');
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setDocuments(await listDocuments(collectionId, currentProject));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [collectionId, currentProject]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(jsonBody);
    } catch {
      toast.error('Invalid JSON');
      return;
    }
    setCreating(true);
    try {
      await createDocument(collectionId, parsed, docId.trim() || undefined, currentProject);
      toast.success('Document created');
      setShowCreate(false);
      setDocId('');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create document');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (doc: FirestoreDocument) => {
    const id = doc.name.split('/').pop()!;
    if (!confirm(`Delete document "${id}"?`)) return;
    try {
      await deleteDocument(collectionId, id, currentProject);
      toast.success('Document deleted');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete document');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <FolderTree className="h-5 w-5 text-blue-600" />
              Firestore
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">{currentProject}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={load}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Add Document
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6">
        <div className="mb-4 flex items-center gap-2">
          <label className="text-sm text-gray-600">Collection:</label>
          <input
            value={collectionId}
            onChange={(e) => setCollectionId(e.target.value)}
            onBlur={load}
            className="rounded-md border border-gray-300 px-2 py-1 text-sm font-mono"
          />
        </div>

        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              No documents in "{collectionId}" yet.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left">
                  <th className="px-4 py-3 font-medium text-gray-600">Document ID</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Fields</th>
                  <th className="px-4 py-3 font-medium text-gray-600 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {documents.map((doc) => {
                  const id = doc.name.split('/').pop();
                  return (
                    <tr key={doc.name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-900">{id}</td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs max-w-md truncate">
                        {JSON.stringify(fieldsToPlain(doc.fields))}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDelete(doc)}
                          className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-red-600"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Add Document" size="lg">
        <form onSubmit={handleCreate}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Document ID (optional, auto-generated if blank)
              </label>
              <input
                type="text"
                value={docId}
                onChange={(e) => setDocId(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fields (JSON)</label>
              <textarea
                value={jsonBody}
                onChange={(e) => setJsonBody(e.target.value)}
                rows={6}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
              />
            </div>
          </div>
          <ModalFooter>
            <ModalButton variant="secondary" onClick={() => setShowCreate(false)}>
              Cancel
            </ModalButton>
            <ModalButton type="submit" disabled={creating}>
              {creating && <Loader2 className="h-4 w-4 animate-spin" />}
              Create
            </ModalButton>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}
