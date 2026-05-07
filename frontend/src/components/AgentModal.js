import React, { useState } from 'react';
import axios from 'axios';

function AgentModal({
  agent,
  purchased,
  accessStatus,
  mode,
  theme,
  authToken,
  apiBase,
  onClose,
  onLoadAgents
}) {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState('');
  const [responseMode, setResponseMode] = useState('Concise');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPurchasePrompt, setShowPurchasePrompt] = useState(false);
  const [purchaseLoading, setPurchaseLoading] = useState(false);
  const [purchaseSuccess, setPurchaseSuccess] = useState(null);
  const [showAccessDetails, setShowAccessDetails] = useState(false);
  const [accessDetails, setAccessDetails] = useState(null);
  const [loadingAccessDetails, setLoadingAccessDetails] = useState(false);
  const [includeReasoning, setIncludeReasoning] = useState(false);

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      alert('Copied to clipboard');
    } catch {
      alert('Copy failed. Please copy manually.');
    }
  };

  const openAgentUrl = (url) => {
    if (!url) return;
    const marketplaceTheme = theme === 'dark' ? 'dark' : 'light';
    localStorage.setItem('app-theme', marketplaceTheme);
    localStorage.setItem('theme', marketplaceTheme);
    const target = new URL(url, window.location.origin);
    target.searchParams.set('theme', marketplaceTheme);
    target.searchParams.set('v', Date.now().toString());
    window.open(target.toString(), '_blank', 'noopener,noreferrer');
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setError('');
    setResponse('');
    setResponseMode(includeReasoning ? 'Detailed' : 'Concise');
    setShowPurchasePrompt(false);
    setLoading(true);

    try {
      const res = await axios.post(
        `${apiBase}/agents/${agent.id}/ask`,
        { question: question.trim(), include_reasoning: includeReasoning },
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        }
      );

      setResponse(res.data.response || 'No response.');
      setResponseMode(res.data.include_reasoning ? 'Detailed' : 'Concise');
      setQuestion('');
    } catch (err) {
      if (err.response?.status === 402) {
        setShowPurchasePrompt(true);
        setError('Demo limit reached! Please purchase to continue.');
      } else {
        setError(err.response?.data?.detail || 'Error asking agent');
      }
    } finally {
      // Always refresh status so demo attempts stay accurate in UI.
      onLoadAgents();
      setLoading(false);
    }
  };

  const handlePurchase = async () => {
    setPurchaseLoading(true);
    setError('');
    try {
      const res = await axios.post(
        `${apiBase}/agents/${agent.id}/purchase`,
        {},
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        }
      );

      setPurchaseSuccess({
        message: res.data.message,
        url: res.data.url,
        purchasedApiUrl: res.data.purchased_api_url,
        purchaseAccessToken: res.data.purchase_access_token,
        purchasedAt: res.data.purchased_at
      });
      setAccessDetails({
        url: res.data.url,
        purchasedApiUrl: res.data.purchased_api_url,
        purchaseAccessToken: res.data.purchase_access_token,
        instructions: 'Use purchase token as bearer token.',
        example_queries: []
      });
      setShowAccessDetails(true);
      setShowPurchasePrompt(false);
      onLoadAgents();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error purchasing agent');
    } finally {
      setPurchaseLoading(false);
    }
  };

  const handleShowAccessDetails = async () => {
    setLoadingAccessDetails(true);
    setError('');
    try {
      const res = await axios.get(
        `${apiBase}/agents/${agent.id}/access-details`,
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        }
      );
      setAccessDetails({
        url: res.data.url,
        purchasedApiUrl: res.data.purchased_api_url,
        purchaseAccessToken: res.data.purchase_access_token,
        instructions: res.data.instructions,
        example_queries: res.data.example_queries || []
      });
      setShowAccessDetails(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error fetching access details');
    } finally {
      setLoadingAccessDetails(false);
    }
  };

  const demoUsesLeft = accessStatus.demo_uses_left || 0;
  const isPurchased = accessStatus.is_purchased || Boolean(purchaseSuccess) || Boolean(accessDetails);
  const isDetailsMode = mode === 'details';
  const agentCardPayload = {
    ...agent,
    access_status: accessStatus || {},
    purchased: Boolean(purchased || isPurchased)
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-top-row">
          <div>
            <h2 className="modal-agent-title">{agent.name}</h2>
            <p className="modal-agent-subtitle">
              {isDetailsMode ? (
                <span className="muted-text">Agent Card</span>
              ) : (
                isPurchased ? (
                  <span className="owned-text">✓ Owned</span>
                ) : (
                  <span className="demo-text">Demo: {demoUsesLeft} {demoUsesLeft !== 1 ? 'tries' : 'try'} left</span>
                )
              )}
            </p>
          </div>
          <div className="modal-actions-top">
            {!isDetailsMode && isPurchased && !purchaseSuccess && !showAccessDetails && (
              <button
                className="btn btn-success"
                onClick={handleShowAccessDetails}
                disabled={loadingAccessDetails}
              >
                {loadingAccessDetails ? 'Loading...' : 'Access Details'}
              </button>
            )}
            {!isDetailsMode && !isPurchased && !purchaseSuccess && (
              <button
                className="btn btn-primary"
                onClick={handlePurchase}
                disabled={purchaseLoading}
              >
                {purchaseLoading ? '...' : 'Buy Now'}
              </button>
            )}
            <button onClick={onClose} className="close-btn" type="button">
              ✕
            </button>
          </div>
        </div>

        <p className="modal-description">{agent.description}</p>

        <div className="modal-panel">
          <h4 className="modal-panel-title">Purpose</h4>
          <p className="modal-panel-content">{agent.purpose}</p>
        </div>

        <div className="modal-panel">
          <h4 className="modal-panel-title">Capabilities</h4>
          <div className="capabilities">
            {agent.capabilities.map((cap, idx) => (
              <span key={idx} className="capability-badge">
                {cap}
              </span>
            ))}
          </div>
        </div>

        <div className="modal-panel">
          <h4 className="modal-panel-title">Status</h4>
          <div className="modal-status-row">
            <div>
              <span className="muted-text">Operational: </span>
              <span className="owned-text">{agent.status}</span>
            </div>
            <div>
              {isPurchased ? (
                <span className="owned-text">✓ Owned</span>
              ) : (
                <span className="demo-text">Demo: {demoUsesLeft} {demoUsesLeft !== 1 ? 'tries' : 'try'} left</span>
              )}
            </div>
          </div>
        </div>

        {!isDetailsMode && isPurchased && !showAccessDetails && !purchaseSuccess && (
          <div className="state-card state-success">
            Use <strong>Access Details</strong> for URL and token.
          </div>
        )}

        {isDetailsMode && (
          <div className="modal-panel">
            <h4 className="modal-panel-title">Agent Card</h4>
            <pre className="raw-json-block">
{JSON.stringify(agentCardPayload, null, 2)}
            </pre>
          </div>
        )}

        {!isDetailsMode && showAccessDetails && accessDetails ? (
          <div className="state-card state-success">
            <h4>Access Details</h4>
            <div className="code-block">
              <p className="code-label">Agent URL:</p>
              <p>{accessDetails.url}</p>
              <p className="code-label" style={{ marginTop: '0.5rem' }}>Purchase Access Token:</p>
              <p style={{ wordBreak: 'break-all' }}>{accessDetails.purchaseAccessToken || 'Not available'}</p>
            </div>
            <p className="muted-text">
              {accessDetails.instructions || 'Use purchase token as bearer token.'}
            </p>
            
            <button className="btn btn-primary" onClick={() => openAgentUrl(accessDetails.url)} type="button">
              Open Agent URL
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => copyToClipboard(accessDetails.purchaseAccessToken || '')}
              type="button"
              disabled={!accessDetails.purchaseAccessToken}
            >
              Copy Purchase Token
            </button>
          </div>
        ) : !isDetailsMode && showPurchasePrompt ? (
          <div className="state-card state-warn">
            <h4>Demo Limit Reached</h4>
            <p>
              Demo tries exhausted. Purchase for unlimited access.
            </p>
            <button
              className="btn btn-primary"
              onClick={handlePurchase}
              disabled={purchaseLoading}
            >
              {purchaseLoading ? 'Processing...' : 'Purchase Now'}
            </button>
          </div>
        ) : !isDetailsMode && purchaseSuccess ? (
          <div className="state-card state-success">
            <h4>✓ Purchase Successful!</h4>
            <p>
              <strong>Agent:</strong> {agent.name}
            </p>
            <p>
              <strong>Purchased:</strong> {new Date(purchaseSuccess.purchasedAt).toLocaleString()}
            </p>
            <div className="code-block">
              <p className="code-label">Agent URL:</p>
              <p>{purchaseSuccess.url}</p>
              <p className="code-label" style={{ marginTop: '0.5rem' }}>Purchase Access Token:</p>
              <p style={{ wordBreak: 'break-all' }}>{purchaseSuccess.purchaseAccessToken || 'Not available'}</p>
            </div>
            <button className="btn btn-primary" onClick={() => openAgentUrl(purchaseSuccess.url)} type="button">
              Open Agent URL
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => copyToClipboard(purchaseSuccess.purchaseAccessToken || '')}
              type="button"
              disabled={!purchaseSuccess.purchaseAccessToken}
            >
              Copy Purchase Token
            </button>
            <p className="purchase-note">
              Use purchase token as bearer token.
            </p>
          </div>
        ) : null}

        {!isDetailsMode && !isPurchased && !purchaseSuccess && !showAccessDetails && (
          <form onSubmit={handleAsk} className="ask-form">
            <div className="form-group">
              <label className="form-label">
                Question
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={loading || (!isPurchased && demoUsesLeft === 0)}
                className="form-textarea"
                placeholder="Type your question here..."
              />
              <label className="reasoning-toggle-row" htmlFor="reasoning-toggle-modal">
                <input
                  id="reasoning-toggle-modal"
                  type="checkbox"
                  checked={includeReasoning}
                  onChange={(e) => setIncludeReasoning(e.target.checked)}
                />
                Show reasoning/details
              </label>
            </div>
            <button
              type="submit"
              disabled={loading || !question.trim() || (!isPurchased && demoUsesLeft === 0)}
              className="btn btn-primary"
            >
              {loading ? 'Asking...' : 'Ask Agent'}
            </button>
          </form>
        )}

        {error && (
          <div className="state-card state-warn">
            {error}
          </div>
        )}

        {response && (
          <div className="state-card state-response">
            <h4>Response</h4>
            <p className="code-meta"><strong>Mode:</strong> {responseMode}</p>
            <p className="response-text">{response}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default AgentModal;
