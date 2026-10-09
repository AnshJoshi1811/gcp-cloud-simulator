import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import {
  listFunctions,
  deployFunction,
  deleteFunction,
  invokeFunction,
  CloudFunction,
} from '../api/functions';
import { Loader2, Plus, RefreshCw, Zap, Trash2, Play } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

const DEFAULT_SOURCE = `def handler(request):
    data = request.get_json() or {}
    name = data.get('name', 'world')
    return {'message': f'Hello, {name}!'}, 200
`;

export default function FunctionsDashboardPage() {
  const { currentProject } = useProject();

  const [functions, setFunctions] = useState<CloudFunction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [deploying, setDeploying] = useState(false);

  const [name, setName] = useState('');
  const [entryPoint, setEntryPoint] = useState('handler');
  const [sourceCode, setSourceCode] = useState(DEFAULT_SOURCE);

  const [testBody, setTestBody] = useState('{"name": "Ansh"}');
  const [testResults, setTestResults] = useState<Record<string, string>>({});
  const [invoking, setInvoking] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setFunctions(await listFunctions(currentProject));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load functions');
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDeploy = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !entryPoint.trim()) return;
    setDeploying(true);
    try {
      const fn = await deployFunction({
        name: name.trim(),
        entryPoint: entryPoint.trim(),
        sourceCode,
        project: currentProject,
      });
      if (fn.state === 'FAILED') {
        toast.error(`Deployed with errors: ${fn.lastError}`);
      } else {
        toast.success(`Function "${name}" deployed`);
      }
      setShowCreate(false);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to deploy function');
    } finally {
      setDeploying(false);
    }
  };

  const handleDelete = async (fn: CloudFunction) => {
    const id = fn.name.split('/').pop()!;
    if (!confirm(`Delete function "${id}"?`)) return;
    try {
      await deleteFunction(id, currentProject);
      toast.success('Function deleted');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete function');
    }
  };

  const handleInvoke = async (fn: CloudFunction) => {
    const id = fn.name.split('/').pop()!;
    setInvoking(id);
    try {
      let body: Record<string, unknown> = {};
      try {
        body = JSON.parse(testBody);
      } catch {
        toast.error('Invalid JSON test body');
        return;
      }
      const result = await invokeFunction(id, body, currentProject);
      setTestResults((prev) => ({ ...prev, [id]: JSON.stringify(result) }));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Invocation failed');
    } finally {
      setInvoking(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Zap className="h-5 w-5 text-blue-600" />
              Cloud Functions
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
              Deploy Function
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 space-y-4">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Test payload (JSON):</label>
          <input
            value={testBody}
            onChange={(e) => setTestBody(e.target.value)}
            className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm font-mono"
          />
        </div>

        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : functions.length === 0 ? (
            <div className="text-center py-16 text-gray-500">No functions deployed yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left">
                  <th className="px-4 py-3 font-medium text-gray-600">Name</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Runtime</th>
                  <th className="px-4 py-3 font-medium text-gray-600">State</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Invocations</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Last result</th>
                  <th className="px-4 py-3 font-medium text-gray-600 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {functions.map((fn) => {
                  const id = fn.name.split('/').pop()!;
                  return (
                    <tr key={fn.name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{id}</td>
                      <td className="px-4 py-3 text-gray-600">{fn.runtime}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-xs ${
                            fn.state === 'ACTIVE'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {fn.state}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{fn.invocationCount}</td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs max-w-xs truncate">
                        {testResults[id] || '-'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleInvoke(fn)}
                            disabled={invoking === id}
                            className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-blue-600"
                            title="Invoke"
                          >
                            {invoking === id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </button>
                          <button
                            onClick={() => handleDelete(fn)}
                            className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-red-600"
                            title="Delete"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Deploy Cloud Function" size="lg">
        <form onSubmit={handleDeploy}>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Function name</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="hello-fn"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Entry point</label>
                <input
                  value={entryPoint}
                  onChange={(e) => setEntryPoint(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Source (Python — function takes a Flask-like `request`)
              </label>
              <textarea
                value={sourceCode}
                onChange={(e) => setSourceCode(e.target.value)}
                rows={10}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
              />
            </div>
          </div>
          <ModalFooter>
            <ModalButton variant="secondary" onClick={() => setShowCreate(false)}>
              Cancel
            </ModalButton>
            <ModalButton type="submit" disabled={deploying}>
              {deploying && <Loader2 className="h-4 w-4 animate-spin" />}
              Deploy
            </ModalButton>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}
