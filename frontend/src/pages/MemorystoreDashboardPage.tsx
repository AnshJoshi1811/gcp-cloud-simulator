import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import { listInstances, createInstance, deleteInstance, RedisInstance } from '../api/memorystore';
import { Loader2, Plus, RefreshCw, Gauge, Trash2 } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

export default function MemorystoreDashboardPage() {
  const { currentProject } = useProject();

  const [instances, setInstances] = useState<RedisInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [instanceId, setInstanceId] = useState('');
  const [tier, setTier] = useState<'BASIC' | 'STANDARD_HA'>('BASIC');
  const [memoryGb, setMemoryGb] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setInstances(await listInstances(currentProject));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load instances');
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!instanceId.trim()) return;
    setCreating(true);
    try {
      await createInstance({ instanceId: instanceId.trim(), tier, memorySizeGb: memoryGb, project: currentProject });
      toast.success(`Instance "${instanceId}" created`);
      setShowCreate(false);
      setInstanceId('');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create instance');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (instance: RedisInstance) => {
    const id = instance.name.split('/').pop();
    if (!confirm(`Delete Redis instance "${id}"?`)) return;
    try {
      await deleteInstance(id!, currentProject);
      toast.success('Instance deleted');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete instance');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Gauge className="h-5 w-5 text-blue-600" />
              Memorystore
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
              Create Instance
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6">
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : instances.length === 0 ? (
            <div className="text-center py-16 text-gray-500">No Redis instances yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left">
                  <th className="px-4 py-3 font-medium text-gray-600">Name</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Tier</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Memory (GB)</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Host:Port</th>
                  <th className="px-4 py-3 font-medium text-gray-600">State</th>
                  <th className="px-4 py-3 font-medium text-gray-600 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {instances.map((inst) => {
                  const id = inst.name.split('/').pop();
                  return (
                    <tr key={inst.name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{id}</td>
                      <td className="px-4 py-3 text-gray-600">{inst.tier}</td>
                      <td className="px-4 py-3 text-gray-600">{inst.memorySizeGb}</td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs">
                        {inst.hostPort ? `localhost:${inst.hostPort}` : `${inst.host}:${inst.port}`}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{inst.state}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDelete(inst)}
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

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Redis Instance">
        <form onSubmit={handleCreate}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Instance ID</label>
              <input
                type="text"
                value={instanceId}
                onChange={(e) => setInstanceId(e.target.value)}
                placeholder="my-cache"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tier</label>
              <select
                value={tier}
                onChange={(e) => setTier(e.target.value as 'BASIC' | 'STANDARD_HA')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="BASIC">Basic</option>
                <option value="STANDARD_HA">Standard HA</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Memory (GB)</label>
              <input
                type="number"
                min={1}
                value={memoryGb}
                onChange={(e) => setMemoryGb(Number(e.target.value))}
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
