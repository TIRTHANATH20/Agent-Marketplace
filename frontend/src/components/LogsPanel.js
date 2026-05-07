import React, { useState } from 'react';
import axios from 'axios';

function LogsPanel({ logs, authToken, apiBase, onLoadLogs }) {
  const [filterType, setFilterType] = useState('all');
  const [clearing, setClearing] = useState(false);

  const handleClearLogs = async () => {
    if (window.confirm('Are you sure you want to clear all logs? This cannot be undone.')) {
      setClearing(true);
      try {
        await axios.post(
          `${apiBase}/logs/clear`,
          {},
          {
            headers: {
              Authorization: `Bearer ${authToken}`,
              'Content-Type': 'application/json'
            }
          }
        );
        onLoadLogs();
      } catch (err) {
        alert('Error clearing logs: ' + (err.response?.data?.detail || 'Unknown error'));
      } finally {
        setClearing(false);
      }
    }
  };

  const filteredLogs = logs
    ? logs.filter((log) => {
        if (filterType === 'all') return true;
        if (filterType === 'query') return log.type === 'QUERY' || log.type === 'AGENT_QUERY';
        if (filterType === 'demo') return log.type === 'DEMO_USAGE' || log.type === 'DEMO_LIMIT_EXCEEDED';
        if (filterType === 'auth') return log.type === 'LOGIN' || log.type === 'LOGOUT';
        if (filterType === 'comm') return log.type === 'AGENT_COMMUNICATION';
        return true;
      })
    : [];

  const getLogColor = (logType) => {
    if (!logType) return '#64748b';
    if (logType.includes('ERROR') || logType.includes('LIMIT')) return '#f97316';
    if (logType.includes('AUTH') || logType.includes('LOGIN')) return '#06b6d4';
    if (logType.includes('DEMO')) return '#eab308';
    if (logType.includes('QUERY')) return '#8b5cf6';
    if (logType.includes('COMMUNICATION')) return '#10b981';
    return '#64748b';
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: '#94a3b8' }}>
            Filter:
          </label>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{
              padding: '0.5rem 0.75rem',
              backgroundColor: '#0f172a',
              color: '#e2e8f0',
              border: '1px solid #475569',
              borderRadius: '0.375rem',
              fontSize: '0.875rem'
            }}
          >
            <option value="all">All Logs</option>
            <option value="query">Queries</option>
            <option value="demo">Demo Usage</option>
            <option value="auth">Authentication</option>
            <option value="comm">Agent Communication</option>
          </select>
        </div>

        <button
          onClick={handleClearLogs}
          disabled={clearing || logs.length === 0}
          className="btn btn-danger"
          style={{
            marginTop: 'auto',
            opacity: clearing || logs.length === 0 ? 0.5 : 1
          }}
        >
          {clearing ? 'Clearing...' : 'Clear All Logs'}
        </button>

        <div style={{ marginLeft: 'auto', color: '#64748b', fontSize: '0.875rem' }}>
          Showing {filteredLogs.length} of {logs ? logs.length : 0} logs
        </div>
      </div>

      {filteredLogs && filteredLogs.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '600px', overflow: 'auto' }}>
          {filteredLogs.map((log, idx) => (
            <div
              key={idx}
              style={{
                padding: '0.75rem',
                backgroundColor: '#0f172a',
                borderLeft: `4px solid ${getLogColor(log.type)}`,
                borderRadius: '0.375rem',
                fontSize: '0.875rem'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span
                  style={{
                    color: getLogColor(log.type),
                    fontWeight: 'bold',
                    fontFamily: 'monospace'
                  }}
                >
                  [{log.type}]
                </span>
                <span style={{ color: '#64748b', fontSize: '0.75rem' }}>
                  {new Date(log.timestamp).toLocaleString()}
                </span>
              </div>

              {log.user && (
                <p style={{ margin: '0.25rem 0', color: '#cbd5e1' }}>
                  <strong style={{ color: '#94a3b8' }}>User:</strong> {log.user}
                </p>
              )}

              {log.agent_name && (
                <p style={{ margin: '0.25rem 0', color: '#cbd5e1' }}>
                  <strong style={{ color: '#94a3b8' }}>Agent:</strong> {log.agent_name}
                </p>
              )}

              {log.message && (
                <p style={{ margin: '0.25rem 0', color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
                  <strong style={{ color: '#94a3b8' }}>Message:</strong> {log.message}
                </p>
              )}

              {log.details && (
                <p style={{ margin: '0.25rem 0', color: '#64748b', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                  {JSON.stringify(log.details)}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
          <p>No logs to display.</p>
          <p style={{ fontSize: '0.875rem' }}>Try filtering different log types or perform actions to generate logs.</p>
        </div>
      )}
    </div>
  );
}

export default LogsPanel;
