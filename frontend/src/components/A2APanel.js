import React, { useState } from 'react';
import axios from 'axios';

function A2APanel({
  agents,
  commHistory,
  authToken,
  apiBase,
  onLoadHistory
}) {
  const [fromAgent, setFromAgent] = useState('');
  const [toAgent, setToAgent] = useState('');
  const [payload, setPayload] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleSend = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (!fromAgent || !toAgent || !payload.trim()) {
      setError('Please select agents and enter a payload');
      return;
    }

    if (fromAgent === toAgent) {
      setError('Cannot send message to the same agent');
      return;
    }

    setLoading(true);

    try {
      await axios.post(
        `${apiBase}/agents/communicate`,
        {
          from_agent_id: fromAgent,
          to_agent_id: toAgent,
          payload: payload.trim()
        },
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        }
      );

      setSuccessMsg('Message sent successfully!');
      setFromAgent('');
      setToAgent('');
      setPayload('');
      onLoadHistory();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error sending message');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h3 style={{ marginBottom: '1.5rem' }}>Agent-to-Agent Communication</h3>

      <form onSubmit={handleSend} style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>
              From Agent:
            </label>
            <select
              value={fromAgent}
              onChange={(e) => setFromAgent(e.target.value)}
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#0f172a',
                color: '#e2e8f0',
                border: '1px solid #475569',
                borderRadius: '0.375rem',
                fontSize: '0.875rem'
              }}
            >
              <option value="">Select agent...</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>
              To Agent:
            </label>
            <select
              value={toAgent}
              onChange={(e) => setToAgent(e.target.value)}
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#0f172a',
                color: '#e2e8f0',
                border: '1px solid #475569',
                borderRadius: '0.375rem',
                fontSize: '0.875rem'
              }}
            >
              <option value="">Select agent...</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: '#e2e8f0' }}>
            Payload (JSON or text):
          </label>
          <textarea
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            disabled={loading}
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: '#0f172a',
              color: '#e2e8f0',
              border: '1px solid #475569',
              borderRadius: '0.375rem',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              minHeight: '120px',
              resize: 'vertical'
            }}
            placeholder={`Example:\n{\n  "query": "What is the total revenue?",\n  "context": "last quarter"\n}`}
          />
        </div>

        <button
          type="submit"
          disabled={loading || !fromAgent || !toAgent || !payload.trim()}
          className="btn btn-primary"
          style={{
            opacity: loading || !fromAgent || !toAgent || !payload.trim() ? 0.5 : 1
          }}
        >
          {loading ? 'Sending...' : 'Send Message'}
        </button>
      </form>

      {error && (
        <div style={{ padding: '1rem', backgroundColor: '#7c2d12', borderRadius: '0.5rem', borderLeft: '4px solid #f97316', marginBottom: '1rem', color: '#fed7aa' }}>
          {error}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: '1rem', backgroundColor: '#064e3b', borderRadius: '0.5rem', borderLeft: '4px solid #86efac', marginBottom: '1rem', color: '#a7f3d0' }}>
          {successMsg}
        </div>
      )}

      {commHistory && commHistory.length > 0 && (
        <div>
          <h4 style={{ marginBottom: '1rem', color: '#cbd5e1' }}>Communication History</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: '400px', overflow: 'auto' }}>
            {commHistory.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  padding: '1rem',
                  backgroundColor: '#0f172a',
                  borderLeft: '4px solid #f97316',
                  borderRadius: '0.375rem'
                }}
              >
                <p style={{ margin: '0 0 0.5rem 0', color: '#f97316', fontSize: '0.875rem' }}>
                  {msg.from_agent_name} → {msg.to_agent_name}
                </p>
                <p style={{ margin: '0.5rem 0', color: '#cbd5e1', fontFamily: 'monospace', fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                  {msg.payload}
                </p>
                <p style={{ margin: '0.5rem 0 0 0', color: '#64748b', fontSize: '0.75rem' }}>
                  {new Date(msg.timestamp).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {(!commHistory || commHistory.length === 0) && (
        <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
          <p>No agent communication history yet.</p>
          <p style={{ fontSize: '0.875rem' }}>Send a message above to get started.</p>
        </div>
      )}
    </div>
  );
}

export default A2APanel;
