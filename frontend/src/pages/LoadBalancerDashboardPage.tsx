import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import {
  listBackendServices,
  listForwardingRules,
  createHealthCheck,
  createBackendService,
  addBackend,
  createUrlMap,
  createTargetProxy,
  createForwardingRule,
  simulateRequest,
  BackendService,
  ForwardingRule,
  SimulateResult,
} from '../api/loadbalancer';
import { Loader2, Plus, RefreshCw, Workflow, Play } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

export default function LoadBalancerDashboardPage() {
  const { currentProject } = useProject();

  const [backendServices, setBackendServices] = useState<BackendService[]>([]);
  const [forwardingRules, setForwardingRules] = useState<ForwardingRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [results, setResults] = useState<Record<string, SimulateResult>>({});

  const [svcName, setSvcName] = useState('web-backend');
  const [instanceName, setInstanceName] = useState('');
  const [zone, setZone] = useState('us-central1-a');
  const [port, setPort] = useState(80);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [services, rules] = await Promise.all([
        listBackendServices(currentProject),
        listForwardingRules(currentProject),
      ]);
      setBackendServices(services);
      setForwardingRules(rules);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load load balancer resources');
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!svcName.trim() || !instanceName.trim()) return;
    setCreating(true);
    try {
      const hcName = `${svcName}-hc`;
      const umName = `${svcName}-urlmap`;
      const proxyName = `${svcName}-proxy`;
      const ruleName = `${svcName}-rule`;

      await createHealthCheck(hcName, port, currentProject);
      await createBackendService(svcName, [hcName], currentProject);
      await addBackend(svcName, instanceName.trim(), zone, port, currentProject);
      await createUrlMap(umName, svcName, currentProject);
      await createTargetProxy(proxyName, umName, currentProject);
      await createForwardingRule(ruleName, proxyName, String(port), currentProject);

      toast.success(`Load balancer "${svcName}" created`);
      setShowCreate(false);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create load balancer');
    } finally {
      setCreating(false);
    }
  };

  const handleSimulate = async (rule: ForwardingRule) => {
    try {
      const result = await simulateRequest(rule.name, currentProject);
      setResults((prev) => ({ ...prev, [rule.name]: result }));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Simulation failed');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Workflow className="h-5 w-5 text-blue-600" />
              Cloud Load Balancing
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
              Create Load Balancer
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="font-medium text-gray-900 mb-3">Backend Services</h2>
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
          ) : backendServices.length === 0 ? (
            <p className="text-sm text-gray-500">None yet.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {backendServices.map((svc) => (
                <li key={svc.name} className="border border-gray-100 rounded p-2">
                  <p className="font-medium text-gray-900">{svc.name}</p>
                  <p className="text-gray-500 text-xs">
                    {svc.backends.length} backend(s): {svc.backends.map((b) => b.instanceName).join(', ') || '-'}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="font-medium text-gray-900 mb-3">Forwarding Rules</h2>
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
          ) : forwardingRules.length === 0 ? (
            <p className="text-sm text-gray-500">None yet.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {forwardingRules.map((rule) => {
                const result = results[rule.name];
                return (
                  <li key={rule.name} className="border border-gray-100 rounded p-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{rule.name}</p>
                        <p className="text-gray-500 text-xs font-mono">
                          {rule.IPAddress}:{rule.portRange}
                        </p>
                      </div>
                      <button
                        onClick={() => handleSimulate(rule)}
                        className="inline-flex items-center gap-1 text-xs rounded bg-gray-100 px-2 py-1 hover:bg-gray-200"
                      >
                        <Play className="h-3 w-3" /> Simulate
                      </button>
                    </div>
                    {result && (
                      <p
                        className={`mt-1 text-xs ${result.healthy ? 'text-green-700' : 'text-red-700'}`}
                      >
                        routed to {result.routedTo} —{' '}
                        {result.healthy ? `OK (${result.statusCode})` : result.error}
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Load Balancer" size="lg">
        <form onSubmit={handleCreate}>
          <p className="text-xs text-gray-500 mb-3">
            Creates a health check, backend service, URL map, target proxy, and forwarding rule in
            one step, wired to an existing Compute Engine instance.
          </p>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Backend service name</label>
              <input
                value={svcName}
                onChange={(e) => setSvcName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Target instance name (existing VM)
              </label>
              <input
                value={instanceName}
                onChange={(e) => setInstanceName(e.target.value)}
                placeholder="my-vm-instance"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Zone</label>
                <input
                  value={zone}
                  onChange={(e) => setZone(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                <input
                  type="number"
                  value={port}
                  onChange={(e) => setPort(Number(e.target.value))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
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
