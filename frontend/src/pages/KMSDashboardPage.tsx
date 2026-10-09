import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import {
  listKeyRings,
  createKeyRing,
  listCryptoKeys,
  createCryptoKey,
  encrypt,
  decrypt,
  KeyRing,
  CryptoKey,
} from '../api/kms';
import { Loader2, Plus, RefreshCw, KeyRound, Lock, Unlock } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

export default function KMSDashboardPage() {
  const { currentProject } = useProject();

  const [keyRings, setKeyRings] = useState<KeyRing[]>([]);
  const [selectedRing, setSelectedRing] = useState<string | null>(null);
  const [cryptoKeys, setCryptoKeys] = useState<CryptoKey[]>([]);
  const [loading, setLoading] = useState(true);

  const [showCreateRing, setShowCreateRing] = useState(false);
  const [newRingId, setNewRingId] = useState('');
  const [showCreateKey, setShowCreateKey] = useState(false);
  const [newKeyId, setNewKeyId] = useState('');

  const [plaintext, setPlaintext] = useState('');
  const [ciphertext, setCiphertext] = useState('');
  const [decrypted, setDecrypted] = useState('');
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadRings = useCallback(async () => {
    setLoading(true);
    try {
      const rings = await listKeyRings(currentProject);
      setKeyRings(rings);
      if (!selectedRing && rings.length > 0) {
        setSelectedRing(rings[0].name.split('/').pop() || null);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load key rings');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProject]);

  const loadKeys = useCallback(async () => {
    if (!selectedRing) {
      setCryptoKeys([]);
      return;
    }
    try {
      const keys = await listCryptoKeys(selectedRing, currentProject);
      setCryptoKeys(keys);
      if (keys.length > 0) setSelectedKey(keys[0].name.split('/').pop() || null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load crypto keys');
    }
  }, [selectedRing, currentProject]);

  useEffect(() => {
    loadRings();
  }, [loadRings]);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

  const handleCreateRing = async (e: FormEvent) => {
    e.preventDefault();
    if (!newRingId.trim()) return;
    try {
      await createKeyRing(newRingId.trim(), currentProject);
      toast.success(`Key ring "${newRingId}" created`);
      setShowCreateRing(false);
      setNewRingId('');
      await loadRings();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create key ring');
    }
  };

  const handleCreateKey = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedRing || !newKeyId.trim()) return;
    try {
      await createCryptoKey(selectedRing, newKeyId.trim(), 'ENCRYPT_DECRYPT', currentProject);
      toast.success(`Crypto key "${newKeyId}" created`);
      setShowCreateKey(false);
      setNewKeyId('');
      await loadKeys();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create crypto key');
    }
  };

  const handleEncrypt = async () => {
    if (!selectedRing || !selectedKey || !plaintext) return;
    setBusy(true);
    try {
      const b64 = btoa(plaintext);
      const { ciphertext: ct } = await encrypt(selectedRing, selectedKey, b64, currentProject);
      setCiphertext(ct);
      toast.success('Encrypted');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Encrypt failed');
    } finally {
      setBusy(false);
    }
  };

  const handleDecrypt = async () => {
    if (!selectedRing || !selectedKey || !ciphertext) return;
    setBusy(true);
    try {
      const { plaintext: pt } = await decrypt(selectedRing, selectedKey, ciphertext, currentProject);
      setDecrypted(atob(pt));
      toast.success('Decrypted');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Decrypt failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-blue-600" />
              Cloud KMS
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">{currentProject}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadRings}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            <button
              onClick={() => setShowCreateRing(true)}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Create Key Ring
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Key rings */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="font-medium text-gray-900 mb-3">Key Rings</h2>
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
          ) : keyRings.length === 0 ? (
            <p className="text-sm text-gray-500">No key rings yet.</p>
          ) : (
            <ul className="space-y-1">
              {keyRings.map((ring) => {
                const id = ring.name.split('/').pop() || ring.name;
                return (
                  <li key={ring.name}>
                    <button
                      onClick={() => setSelectedRing(id)}
                      className={`w-full text-left px-2 py-1.5 rounded text-sm ${
                        selectedRing === id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-700'
                      }`}
                    >
                      {id}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Crypto keys */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-medium text-gray-900">Crypto Keys</h2>
            {selectedRing && (
              <button
                onClick={() => setShowCreateKey(true)}
                className="text-sm text-blue-600 hover:underline"
              >
                + New key
              </button>
            )}
          </div>
          {!selectedRing ? (
            <p className="text-sm text-gray-500">Select a key ring.</p>
          ) : cryptoKeys.length === 0 ? (
            <p className="text-sm text-gray-500">No crypto keys in this ring.</p>
          ) : (
            <ul className="space-y-1">
              {cryptoKeys.map((key) => {
                const id = key.name.split('/').pop() || key.name;
                return (
                  <li key={key.name}>
                    <button
                      onClick={() => setSelectedKey(id)}
                      className={`w-full text-left px-2 py-1.5 rounded text-sm ${
                        selectedKey === id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-700'
                      }`}
                    >
                      {id} <span className="text-xs text-gray-400">({key.purpose})</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Encrypt/Decrypt */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="font-medium text-gray-900 mb-3">Encrypt / Decrypt</h2>
          {!selectedKey ? (
            <p className="text-sm text-gray-500">Select a crypto key to test encryption.</p>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Plaintext</label>
                <textarea
                  value={plaintext}
                  onChange={(e) => setPlaintext(e.target.value)}
                  rows={2}
                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                />
              </div>
              <button
                onClick={handleEncrypt}
                disabled={busy}
                className="inline-flex items-center gap-1 text-sm rounded-md bg-blue-600 px-3 py-1.5 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                <Lock className="h-3.5 w-3.5" /> Encrypt
              </button>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Ciphertext (base64)</label>
                <textarea
                  value={ciphertext}
                  onChange={(e) => setCiphertext(e.target.value)}
                  rows={2}
                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm font-mono"
                />
              </div>
              <button
                onClick={handleDecrypt}
                disabled={busy}
                className="inline-flex items-center gap-1 text-sm rounded-md border border-gray-300 px-3 py-1.5 hover:bg-gray-50 disabled:opacity-50"
              >
                <Unlock className="h-3.5 w-3.5" /> Decrypt
              </button>
              {decrypted && (
                <div className="text-sm bg-green-50 border border-green-200 rounded p-2 text-green-800">
                  {decrypted}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <Modal isOpen={showCreateRing} onClose={() => setShowCreateRing(false)} title="Create Key Ring">
        <form onSubmit={handleCreateRing}>
          <input
            type="text"
            value={newRingId}
            onChange={(e) => setNewRingId(e.target.value)}
            placeholder="my-key-ring"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            required
          />
          <ModalFooter>
            <ModalButton variant="secondary" onClick={() => setShowCreateRing(false)}>
              Cancel
            </ModalButton>
            <ModalButton type="submit">Create</ModalButton>
          </ModalFooter>
        </form>
      </Modal>

      <Modal isOpen={showCreateKey} onClose={() => setShowCreateKey(false)} title="Create Crypto Key">
        <form onSubmit={handleCreateKey}>
          <input
            type="text"
            value={newKeyId}
            onChange={(e) => setNewKeyId(e.target.value)}
            placeholder="my-key"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            required
          />
          <ModalFooter>
            <ModalButton variant="secondary" onClick={() => setShowCreateKey(false)}>
              Cancel
            </ModalButton>
            <ModalButton type="submit">Create</ModalButton>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}
