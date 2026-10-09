import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import { listGateways, createApiConfig, createGateway, testRoute, Gateway } from '../api/apigateway';
import { Loader2, Plus, RefreshCw, Router, Play } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

export default function ApiGatewayDashboardPage() {
  const { currentProject } = useProject();

  const [gateways, setGateways] = useState<Gateway[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  const [gatewayName, setGatewayName] = useState('my-gateway');
  const [routePath, setRoutePath] = useState('/hello');
  const [backendFunction, setBackendFunction] = useState('');

  const [testPath, setTestPath] = useState<Record<string, string>>({});
  const [testResults, setTestResults] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setGateways(await listGateways(currentProject));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load gateways');
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!gatewayName.trim() || !routePath.trim() || !backendFunction.trim()) return;
    setCreating(true);
    try {
      const apiId = `${gatewayName}-api`;
      const configId = `${gatewayName}-cfg`;
      await createApiConfig(
        apiId,
        configId,
        [{ path: routePath.trim(), method: 'GET', backendFunction: backendFunction.trim(), backendUrl: null }],
        currentProject
      );
      await createGateway(gatewayName.trim(), configId, currentProject);
      toast.success(`Gateway "${gatewayName}" created`);
      setShowCreate(false);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create gateway');
    } finally {
      setCreating(false);
    }
  };

  const handleTest = async (gw: Gateway) => {
    const id = gw.name.split('/').pop()!;
    const path = testPath[id] || '/hello';
    try {
      const result = await testRoute(id, path, 'GET', currentProject);
      setTestResults((prev) => ({ ...prev, [id]: JSON.stringify(result) }));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Request failed');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Router className="h-5 w-5 text-blue-600" />
              API Gateway
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
              Create Gateway
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
          ) : gateways.length === 0 ? (
            <p className="text-sm text-gray-500">
              No gateways yet. Deploy a Cloud Function first, then create a gateway that routes to
              it.
            </p>
          ) : (
            <ul className="space-y-3">
              {gateways.map((gw) => {
                const id = gw.name.split('/').pop()!;
                return (
                  <li key={gw.name} className="border border-gray-100 rounded p-3">
                    <p className="font-medium text-gray-900">{id}</p>
                    <p className="text-xs text-gray-500 font-mono">{gw.defaultHostname}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <input
                        value={testPath[id] || '/hello'}
                        onChange={(e) => setTestPath((prev) => ({ ...prev, [id]: e.target.value }))}
                        className="rounded-md border border-gray-300 px-2 py-1 text-xs font-mono w-40"
                      />
                      <button
                        onClick={() => handleTest(gw)}
                        className="inline-flex items-center gap-1 text-xs rounded bg-gray-100 px-2 py-1 hover:bg-gray-200"
                      >
                        <Play className="h-3 w-3" /> Test
                      </button>
                    </div>
                    {testResults[id] && (
                      <p className="mt-1 text-xs font-mono text-gray-700">{testResults[id]}</p>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create API Gateway">
        <form onSubmit={handleCreate}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Gateway name</label>
              <input
                value={gatewayName}
                onChange={(e) => setGatewayName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Route path</label>
              <input
                value={routePath}
                onChange={(e) => setRoutePath(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Backend Cloud Function name
              </label>
              <input
                value={backendFunction}
                onChange={(e) => setBackendFunction(e.target.value)}
                placeholder="hello-fn"
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
