import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import {
  listQueues,
  createQueue,
  pauseQueue,
  resumeQueue,
  listTasks,
  createTask,
  Queue,
  Task,
} from '../api/tasks';
import { Loader2, Plus, RefreshCw, ListChecks, Pause, Play } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

export default function TasksDashboardPage() {
  const { currentProject } = useProject();

  const [queues, setQueues] = useState<Queue[]>([]);
  const [selectedQueue, setSelectedQueue] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const [showCreateQueue, setShowCreateQueue] = useState(false);
  const [newQueueId, setNewQueueId] = useState('');
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [taskUrl, setTaskUrl] = useState('');

  const loadQueues = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listQueues(currentProject);
      setQueues(data);
      if (!selectedQueue && data.length > 0) {
        setSelectedQueue(data[0].name.split('/').pop() || null);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load queues');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProject]);

  const loadTasks = useCallback(async () => {
    if (!selectedQueue) {
      setTasks([]);
      return;
    }
    const queue = queues.find((q) => q.name.endsWith(`/${selectedQueue}`));
    if (!queue) return;
    try {
      setTasks(await listTasks(queue.name));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load tasks');
    }
  }, [selectedQueue, queues]);

  useEffect(() => {
    loadQueues();
  }, [loadQueues]);

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 2000);
    return () => clearInterval(interval);
  }, [loadTasks]);

  const handleCreateQueue = async (e: FormEvent) => {
    e.preventDefault();
    if (!newQueueId.trim()) return;
    try {
      await createQueue(newQueueId.trim(), currentProject);
      toast.success(`Queue "${newQueueId}" created`);
      setShowCreateQueue(false);
      setNewQueueId('');
      await loadQueues();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create queue');
    }
  };

  const handleTogglePause = async (queue: Queue) => {
    try {
      if (queue.state === 'RUNNING') {
        await pauseQueue(queue.name);
      } else {
        await resumeQueue(queue.name);
      }
      await loadQueues();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update queue');
    }
  };

  const handleCreateTask = async (e: FormEvent) => {
    e.preventDefault();
    const queue = queues.find((q) => q.name.endsWith(`/${selectedQueue}`));
    if (!queue || !taskUrl.trim()) return;
    try {
      await createTask(queue.name, taskUrl.trim());
      toast.success('Task scheduled');
      setShowCreateTask(false);
      setTaskUrl('');
      await loadTasks();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create task');
    }
  };

  const stateColor: Record<string, string> = {
    SCHEDULED: 'bg-gray-100 text-gray-700',
    DISPATCHED: 'bg-yellow-100 text-yellow-700',
    SUCCEEDED: 'bg-green-100 text-green-700',
    FAILED: 'bg-red-100 text-red-700',
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <ListChecks className="h-5 w-5 text-blue-600" />
              Cloud Tasks
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">{currentProject}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadQueues}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            <button
              onClick={() => setShowCreateQueue(true)}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Create Queue
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="font-medium text-gray-900 mb-3">Queues</h2>
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
          ) : queues.length === 0 ? (
            <p className="text-sm text-gray-500">No queues yet.</p>
          ) : (
            <ul className="space-y-1">
              {queues.map((queue) => {
                const id = queue.name.split('/').pop() || queue.name;
                return (
                  <li key={queue.name} className="flex items-center justify-between">
                    <button
                      onClick={() => setSelectedQueue(id)}
                      className={`flex-1 text-left px-2 py-1.5 rounded text-sm ${
                        selectedQueue === id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-700'
                      }`}
                    >
                      {id} <span className="text-xs text-gray-400">({queue.state})</span>
                    </button>
                    <button
                      onClick={() => handleTogglePause(queue)}
                      className="p-1 text-gray-500 hover:text-blue-600"
                      title={queue.state === 'RUNNING' ? 'Pause' : 'Resume'}
                    >
                      {queue.state === 'RUNNING' ? (
                        <Pause className="h-4 w-4" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-medium text-gray-900">Tasks</h2>
            {selectedQueue && (
              <button
                onClick={() => setShowCreateTask(true)}
                className="text-sm text-blue-600 hover:underline"
              >
                + New task
              </button>
            )}
          </div>
          {!selectedQueue ? (
            <p className="text-sm text-gray-500">Select a queue.</p>
          ) : tasks.length === 0 ? (
            <p className="text-sm text-gray-500">No tasks in this queue.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <th className="py-2 pr-2">URL</th>
                  <th className="py-2 pr-2">State</th>
                  <th className="py-2 pr-2">Dispatches</th>
                  <th className="py-2">Last Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tasks.map((task) => (
                  <tr key={task.name}>
                    <td className="py-2 pr-2 max-w-xs truncate">{task.httpRequest.url}</td>
                    <td className="py-2 pr-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${stateColor[task.state]}`}>
                        {task.state}
                      </span>
                    </td>
                    <td className="py-2 pr-2">{task.dispatchCount}</td>
                    <td className="py-2 text-gray-500">{task.lastAttemptResult || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <Modal isOpen={showCreateQueue} onClose={() => setShowCreateQueue(false)} title="Create Queue">
        <form onSubmit={handleCreateQueue}>
          <input
            type="text"
            value={newQueueId}
            onChange={(e) => setNewQueueId(e.target.value)}
            placeholder="my-queue"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            required
          />
          <ModalFooter>
            <ModalButton variant="secondary" onClick={() => setShowCreateQueue(false)}>
              Cancel
            </ModalButton>
            <ModalButton type="submit">Create</ModalButton>
          </ModalFooter>
        </form>
      </Modal>

      <Modal isOpen={showCreateTask} onClose={() => setShowCreateTask(false)} title="Create Task">
        <form onSubmit={handleCreateTask}>
          <label className="block text-sm font-medium text-gray-700 mb-1">Target URL</label>
          <input
            type="text"
            value={taskUrl}
            onChange={(e) => setTaskUrl(e.target.value)}
            placeholder="http://localhost:8080/health"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            required
          />
          <ModalFooter>
            <ModalButton variant="secondary" onClick={() => setShowCreateTask(false)}>
              Cancel
            </ModalButton>
            <ModalButton type="submit">Schedule</ModalButton>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}
