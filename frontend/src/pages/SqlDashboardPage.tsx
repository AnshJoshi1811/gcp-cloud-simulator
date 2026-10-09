import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import {
  listInstances,
  createInstance,
  deleteInstance,
  stopInstance,
  startInstance,
  listDatabases,
  createDatabase,
  listUsers,
  createUser,
  SqlInstance,
  SqlDatabase,
  SqlUser,
} from '../api/sql';
import { Loader2, Plus, RefreshCw, Database, Trash2, Square, Play } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

export default function SqlDashboardPage() {
  const { currentProject } = useProject();

  const [instances, setInstances] = useState<SqlInstance[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [databases, setDatabases] = useState<SqlDatabase[]>([]);
  const [users, setUsers] = useState<SqlUser[]>([]);
  const [loading, setLoading] = useState(true);

  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const [engine, setEngine] = useState<'POSTGRES_15' | 'MYSQL_8_0'>('POSTGRES_15');

  const [newDbName, setNewDbName] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [lastPassword, setLastPassword] = useState<string | null>(null);

  const loadInstances = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listInstances(currentProject);
      setInstances(data);
      if (!selected && data.length > 0) setSelected(data[0].name);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load instances');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProject]);

  const loadDetails = useCallback(async () => {
    if (!selected) {
      setDatabases([]);
      setUsers([]);
      return;
    }
    try {
      const [dbs, usrs] = await Promise.all([
        listDatabases(selected, currentProject),
        listUsers(selected, currentProject),
      ]);
      setDatabases(dbs);
      setUsers(usrs);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load instance details');
    }
  }, [selected, currentProject]);

  useEffect(() => {
    loadInstances();
  }, [loadInstances]);

  useEffect(() => {
    loadDetails();
  }, [loadDetails]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await createInstance({ name: name.trim(), databaseVersion: engine, project: currentProject });
      toast.success(`Instance "${name}" created`);
      setShowCreate(false);
      setName('');
      await loadInstances();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create instance');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (instance: SqlInstance) => {
    if (!confirm(`Delete instance "${instance.name}"? This removes its container.`)) return;
    try {
      await deleteInstance(instance.name, currentProject);
      toast.success('Instance deleted');
      setSelected(null);
      await loadInstances();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete instance');
    }
  };

  const handleToggle = async (instance: SqlInstance) => {
    try {
      if (instance.state === 'RUNNABLE') {
        await stopInstance(instance.name, currentProject);
      } else {
        await startInstance(instance.name, currentProject);
      }
      await loadInstances();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update instance');
    }
  };

  const handleCreateDb = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !newDbName.trim()) return;
    try {
      await createDatabase(selected, newDbName.trim(), currentProject);
      setNewDbName('');
      toast.success('Database created');
      await loadDetails();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create database');
    }
  };

  const handleCreateUser = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !newUserName.trim()) return;
    try {
      const user = await createUser(selected, newUserName.trim(), currentProject);
      setLastPassword(user.password || null);
      setNewUserName('');
      toast.success('User created');
      await loadDetails();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create user');
    }
  };

  const stateColor: Record<string, string> = {
    RUNNABLE: 'bg-green-100 text-green-700',
    STOPPED: 'bg-gray-100 text-gray-700',
    PENDING_CREATE: 'bg-yellow-100 text-yellow-700',
    FAILED: 'bg-red-100 text-red-700',
  };

  const selectedInstance = instances.find((i) => i.name === selected);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-600" />
              Cloud SQL
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">{currentProject}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadInstances}
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

      <div className="px-6 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="font-medium text-gray-900 mb-3">Instances</h2>
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
          ) : instances.length === 0 ? (
            <p className="text-sm text-gray-500">No Cloud SQL instances yet.</p>
          ) : (
            <ul className="space-y-1">
              {instances.map((inst) => (
                <li key={inst.name} className="flex items-center justify-between">
                  <button
                    onClick={() => setSelected(inst.name)}
                    className={`flex-1 text-left px-2 py-1.5 rounded text-sm ${
                      selected === inst.name ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    {inst.name}{' '}
                    <span className={`ml-1 px-1.5 py-0.5 rounded text-xs ${stateColor[inst.state]}`}>
                      {inst.state}
                    </span>
                  </button>
                  <button
                    onClick={() => handleToggle(inst)}
                    className="p-1 text-gray-500 hover:text-blue-600"
                    title={inst.state === 'RUNNABLE' ? 'Stop' : 'Start'}
                  >
                    {inst.state === 'RUNNABLE' ? <Square className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </button>
                  <button
                    onClick={() => handleDelete(inst)}
                    className="p-1 text-gray-500 hover:text-red-600"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 p-4">
          {!selectedInstance ? (
            <p className="text-sm text-gray-500">Select an instance to view details.</p>
          ) : (
            <div className="space-y-4">
              <div className="text-sm text-gray-700 space-y-1">
                <p>
                  <span className="text-gray-500">Engine:</span> {selectedInstance.databaseVersion}
                </p>
                <p>
                  <span className="text-gray-500">Connection name:</span>{' '}
                  <span className="font-mono text-xs">{selectedInstance.connectionName}</span>
                </p>
                {selectedInstance.hostPort && (
                  <p>
                    <span className="text-gray-500">Connect from host:</span>{' '}
                    <span className="font-mono text-xs">
                      localhost:{selectedInstance.hostPort}
                    </span>
                  </p>
                )}
              </div>

              <div>
                <h3 className="text-sm font-medium text-gray-900 mb-2">Databases</h3>
                <form onSubmit={handleCreateDb} className="flex gap-2 mb-2">
                  <input
                    value={newDbName}
                    onChange={(e) => setNewDbName(e.target.value)}
                    placeholder="database name"
                    className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm"
                  />
                  <button type="submit" className="text-sm text-blue-600 hover:underline">
                    Add
                  </button>
                </form>
                <ul className="text-sm text-gray-700 space-y-1">
                  {databases.map((db) => (
                    <li key={db.name}>{db.name}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h3 className="text-sm font-medium text-gray-900 mb-2">Users</h3>
                <form onSubmit={handleCreateUser} className="flex gap-2 mb-2">
                  <input
                    value={newUserName}
                    onChange={(e) => setNewUserName(e.target.value)}
                    placeholder="user name"
                    className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm"
                  />
                  <button type="submit" className="text-sm text-blue-600 hover:underline">
                    Add
                  </button>
                </form>
                <ul className="text-sm text-gray-700 space-y-1">
                  {users.map((u) => (
                    <li key={u.name}>{u.name}</li>
                  ))}
                </ul>
                {lastPassword && (
                  <p className="mt-2 text-xs bg-yellow-50 border border-yellow-200 rounded p-2 text-yellow-800">
                    Generated password (shown once): <span className="font-mono">{lastPassword}</span>
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Cloud SQL Instance">
        <form onSubmit={handleCreate}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Instance ID</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="my-sql-instance"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Database engine</label>
              <select
                value={engine}
                onChange={(e) => setEngine(e.target.value as 'POSTGRES_15' | 'MYSQL_8_0')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="POSTGRES_15">PostgreSQL 15</option>
                <option value="MYSQL_8_0">MySQL 8.0</option>
              </select>
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
