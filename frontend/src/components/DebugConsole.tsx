import { useState } from 'react';
import { Terminal, Play, Trash2, Copy, CheckCircle } from 'lucide-react';
import { api } from '../api';

interface LogEntry {
  timestamp: string;
  type: 'request' | 'response' | 'error' | 'info';
  message: string;
  data?: unknown;
}

export default function DebugConsole() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [command, setCommand] = useState('');
  const [copied, setCopied] = useState(false);

  const addLog = (type: LogEntry['type'], message: string, data?: unknown) => {
    setLogs((prev) => [
      ...prev,
      {
        timestamp: new Date().toISOString(),
        type,
        message,
        data,
      },
    ]);
  };

  const executeCommand = async () => {
    if (!command.trim()) return;

    addLog('info', `Executing: ${command}`);

    try {
      if (command === 'health' || command === 'healthz') {
        const result = await api.checkHealth();
        addLog('response', 'Health check successful', result);
      } else if (command.startsWith('job ')) {
        const jobId = command.split(' ')[1];
        addLog('request', `Fetching job: ${jobId}`);
        const result = await api.getJob(jobId);
        addLog('response', `Job data retrieved`, result);
      } else if (command === 'clear') {
        setLogs([]);
        addLog('info', 'Console cleared');
      } else if (command === 'help') {
        addLog(
          'info',
          'Available commands:\n' +
            '  health - Check API health\n' +
            '  job <job_id> - Get job details\n' +
            '  clear - Clear console\n' +
            '  help - Show this message'
        );
      } else {
        addLog('error', `Unknown command: ${command}`);
      }
    } catch (error) {
      addLog('error', error instanceof Error ? error.message : 'Command failed');
    }

    setCommand('');
  };

  const copyLogs = () => {
    const logText = logs
      .map(
        (log) =>
          `[${log.timestamp}] ${log.type.toUpperCase()}: ${log.message}${
            log.data ? '\n' + JSON.stringify(log.data, null, 2) : ''
          }`
      )
      .join('\n\n');

    navigator.clipboard.writeText(logText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLogClass = (type: string) => {
    switch (type) {
      case 'error':
        return 'log-error';
      case 'request':
        return 'log-request';
      case 'response':
        return 'log-response';
      default:
        return 'log-info';
    }
  };

  return (
    <div className="debug-console">
      <div className="section-header">
        <h2>Debug Console</h2>
        <p>Execute commands and view API interactions</p>
      </div>

      <div className="console-controls">
        <div className="command-input">
          <Terminal size={18} />
          <input
            type="text"
            placeholder="Enter command (type 'help' for commands)"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && executeCommand()}
            className="input"
          />
          <button className="button-primary" onClick={executeCommand}>
            <Play size={16} />
            Run
          </button>
        </div>

        <div className="console-actions">
          <button className="button-secondary" onClick={copyLogs} disabled={logs.length === 0}>
            {copied ? <CheckCircle size={16} /> : <Copy size={16} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
          <button
            className="button-secondary"
            onClick={() => setLogs([])}
            disabled={logs.length === 0}
          >
            <Trash2 size={16} />
            Clear
          </button>
        </div>
      </div>

      <div className="console-output">
        {logs.length === 0 ? (
          <div className="console-empty">
            <Terminal size={48} />
            <p>No logs yet. Run a command to get started.</p>
            <p className="hint">Try: health, job &lt;job_id&gt;, or help</p>
          </div>
        ) : (
          <div className="console-logs">
            {logs.map((log, index) => (
              <div key={index} className={`console-log ${getLogClass(log.type)}`}>
                <div className="log-header">
                  <span className="log-type">[{log.type.toUpperCase()}]</span>
                  <span className="log-time">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="log-message">{log.message}</div>
                {log.data && (
                  <pre className="log-data">
                    {JSON.stringify(log.data, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
