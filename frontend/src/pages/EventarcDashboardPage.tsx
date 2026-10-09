import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import { listTriggers, createTrigger, deleteTrigger, Trigger } from '../api/eventarc';
import { Loader2, Plus, RefreshCw, Shuffle, Trash2 } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

export default function EventarcDashboardPage() {
  const { currentProject } = useProject();

  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  const [triggerId, setTriggerId] = useState('');
  const [topic, setTopic] = useState('');
  const [destinationFunction, setDestinationFunction] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTriggers(await listTriggers(currentProject));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load triggers');
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [load]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!triggerId.trim() || !topic.trim() || !destinationFunction.trim()) return;
    setCreating(true);
    try {
      await createTrigger(triggerId.trim(), topic.trim(), destinationFunction.trim(), currentProject);
      toast.success(`Trigger "${triggerId}" created`);
      setShowCreate(false);
      setTriggerId('');
      setTopic('');
      setDestinationFunction('');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create trigger');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (trigger: Trigger) => {
    const id = trigger.name.split('/').pop()!;
    if (!confirm(`Delete trigger "${id}"?`)) return;
    try {
      await deleteTrigger(id, currentProject);
      toast.success('Trigger deleted');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete trigger');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Shuffle className="h-5 w-5 text-blue-600" />
              Event Routing
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
              Create Trigger
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
          ) : triggers.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              No triggers yet. Route a Pub/Sub topic's messages to a Cloud Function.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left">
                  <th className="px-4 py-3 font-medium text-gray-600">Trigger</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Topic</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Destination</th>
                  <th className="px-4 py-3 font-medium text-gray-600">State</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Events</th>
                  <th className="px-4 py-3 font-medium text-gray-600 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {triggers.map((trigger) => {
                  const id = trigger.name.split('/').pop();
                  return (
                    <tr key={trigger.name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{id}</td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs">
                        {trigger.transport.pubsub.topic}
                      </td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs">
                        {trigger.destination.cloudFunction}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-xs ${
                            trigger.state === 'ACTIVE'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {trigger.state}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{trigger.eventCount}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDelete(trigger)}
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

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Event Trigger">
        <form onSubmit={handleCreate}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Trigger ID</label>
              <input
                value={triggerId}
                onChange={(e) => setTriggerId(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Source Pub/Sub topic name
              </label>
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="my-topic"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Destination Cloud Function name
              </label>
              <input
                value={destinationFunction}
                onChange={(e) => setDestinationFunction(e.target.value)}
                placeholder="my-function"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
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
