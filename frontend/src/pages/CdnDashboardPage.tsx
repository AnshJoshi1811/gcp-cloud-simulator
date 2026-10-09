import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import {
  listBackendBuckets,
  createBackendBucket,
  deleteBackendBucket,
  invalidateCache,
  cdnContentUrl,
  BackendBucket,
} from '../api/cdn';
import { Loader2, Plus, RefreshCw, Rss, Trash2, RotateCcw } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

export default function CdnDashboardPage() {
  const { currentProject } = useProject();

  const [backendBuckets, setBackendBuckets] = useState<BackendBucket[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  const [name, setName] = useState('');
  const [bucketName, setBucketName] = useState('');
  const [ttl, setTtl] = useState(3600);
  const [testPath, setTestPath] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setBackendBuckets(await listBackendBuckets(currentProject));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load backend buckets');
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !bucketName.trim()) return;
    setCreating(true);
    try {
      await createBackendBucket(name.trim(), bucketName.trim(), ttl, currentProject);
      toast.success(`Backend bucket "${name}" created`);
      setShowCreate(false);
      setName('');
      setBucketName('');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create backend bucket');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (bb: BackendBucket) => {
    if (!confirm(`Delete backend bucket "${bb.name}"?`)) return;
    try {
      await deleteBackendBucket(bb.name, currentProject);
      toast.success('Backend bucket deleted');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete backend bucket');
    }
  };

  const handleInvalidate = async (bb: BackendBucket) => {
    try {
      const count = await invalidateCache(bb.name, undefined, currentProject);
      toast.success(`Invalidated ${count} cached object(s)`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to invalidate cache');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Rss className="h-5 w-5 text-blue-600" />
              Cloud CDN
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
              Create Backend Bucket
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
          ) : backendBuckets.length === 0 ? (
            <p className="text-sm text-gray-500">
              No backend buckets yet. Create one pointing at an existing Cloud Storage bucket to
              enable CDN caching for its objects.
            </p>
          ) : (
            <ul className="space-y-3">
              {backendBuckets.map((bb) => (
                <li key={bb.name} className="border border-gray-100 rounded p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{bb.name}</p>
                      <p className="text-xs text-gray-500">
                        bucket: {bb.bucketName} — TTL {bb.cdnPolicy.defaultTtl}s
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleInvalidate(bb)}
                        className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-blue-600"
                        title="Invalidate cache"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(bb)}
                        className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-red-600"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <input
                      value={testPath[bb.name] || ''}
                      onChange={(e) => setTestPath((prev) => ({ ...prev, [bb.name]: e.target.value }))}
                      placeholder="object-path.ext"
                      className="rounded-md border border-gray-300 px-2 py-1 text-xs font-mono w-48"
                    />
                    {testPath[bb.name] && (
                      <a
                        href={cdnContentUrl(bb.name, testPath[bb.name])}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Open via CDN
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Backend Bucket">
        <form onSubmit={handleCreate}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Backend bucket name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cloud Storage bucket name
              </label>
              <input
                value={bucketName}
                onChange={(e) => setBucketName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cache TTL (seconds)</label>
              <input
                type="number"
                value={ttl}
                onChange={(e) => setTtl(Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
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
