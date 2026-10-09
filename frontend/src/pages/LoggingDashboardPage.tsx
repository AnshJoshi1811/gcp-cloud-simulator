import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import { listEntries, writeEntry, LogEntry } from '../api/logging';
import { Loader2, RefreshCw, ScrollText, Send } from 'lucide-react';

export default function LoggingDashboardPage() {
  const { currentProject } = useProject();

  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  const [logId, setLogId] = useState('app');
  const [severity, setSeverity] = useState('INFO');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setEntries(await listEntries(filter, currentProject));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load log entries');
    } finally {
      setLoading(false);
    }
  }, [filter, currentProject]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSend = async (e: FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    setSending(true);
    try {
      await writeEntry(logId || 'app', severity, message.trim(), currentProject);
      setMessage('');
      toast.success('Entry written');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to write entry');
    } finally {
      setSending(false);
    }
  };

  const severityColor: Record<string, string> = {
    DEFAULT: 'bg-gray-100 text-gray-700',
    DEBUG: 'bg-gray-100 text-gray-700',
    INFO: 'bg-blue-100 text-blue-700',
    NOTICE: 'bg-blue-100 text-blue-700',
    WARNING: 'bg-yellow-100 text-yellow-700',
    ERROR: 'bg-red-100 text-red-700',
    CRITICAL: 'bg-red-200 text-red-800',
    ALERT: 'bg-red-200 text-red-800',
    EMERGENCY: 'bg-red-300 text-red-900',
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <ScrollText className="h-5 w-5 text-blue-600" />
              Cloud Logging
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">{currentProject}</p>
          </div>
          <button
            onClick={load}
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      <div className="px-6 py-6 space-y-4">
        <form onSubmit={handleSend} className="bg-white rounded-lg border border-gray-200 p-4 flex gap-2 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Log name</label>
            <input
              value={logId}
              onChange={(e) => setLogId(e.target.value)}
              className="rounded-md border border-gray-300 px-2 py-1 text-sm w-32"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="rounded-md border border-gray-300 px-2 py-1 text-sm"
            >
              {['DEBUG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'CRITICAL'].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-gray-600 mb-1">Message</label>
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Write a test log entry..."
              className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={sending}
            className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Send className="h-3.5 w-3.5" /> Write
          </button>
        </form>

        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Filter:</label>
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            onBlur={load}
            placeholder='e.g. severity>=ERROR'
            className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm font-mono"
          />
        </div>

        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : entries.length === 0 ? (
            <div className="text-center py-16 text-gray-500">No log entries yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left">
                  <th className="px-4 py-3 font-medium text-gray-600">Timestamp</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Severity</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Log</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entries.map((entry) => (
                  <tr key={entry.insertId} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {new Date(entry.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${severityColor[entry.severity] || ''}`}>
                        {entry.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs font-mono">
                      {entry.logName.split('/').pop()}
                    </td>
                    <td className="px-4 py-3 text-gray-700 max-w-md truncate">
                      {entry.textPayload || JSON.stringify(entry.jsonPayload)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
