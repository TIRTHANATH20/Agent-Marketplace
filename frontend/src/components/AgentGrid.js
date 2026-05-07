import React, { useMemo, useState } from 'react';
import AgentModal from './AgentModal';

function AgentGrid({
  agents,
  purchasedMap,
  accessStatus,
  theme,
  authToken,
  apiBase,
  onLoadAgents
}) {
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('details');
  const [searchText, setSearchText] = useState('');
  const [visibilityFilter, setVisibilityFilter] = useState('all');

  const formatCapability = (capability) =>
    capability
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');

  const getDomainLabel = (agentId) => {
    const domainMap = {
      'agent-001': 'Analytics',
      'agent-002': 'Database',
      'agent-003': 'Reporting',
      'agent-004': 'Customer',
      'agent-005': 'Sales',
      'agent-006': 'Pricing'
    };
    return domainMap[agentId] || 'General';
  };

  const getBuyerFitLabel = (agentId) => {
    const fitMap = {
      'agent-001': 'Best for KPI and trend visibility',
      'agent-002': 'Best for exact data and counts',
      'agent-003': 'Best for structured stakeholder reports',
      'agent-004': 'Best for customer segmentation and LTV',
      'agent-005': 'Best for sales and revenue performance',
      'agent-006': 'Best for pricing and discount decisions'
    };
    return fitMap[agentId] || 'Best for general assistant tasks';
  };

  const visibleAgents = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    return agents.filter((agent) => {
      const status = accessStatus[agent.id] || {};
      const isPurchased = status.is_purchased;
      const matchesFilter =
        visibilityFilter === 'all' ||
        (visibilityFilter === 'owned' && isPurchased) ||
        (visibilityFilter === 'demo' && !isPurchased);

      if (!matchesFilter) return false;
      if (!q) return true;

      const haystack = [
        agent.name,
        agent.description,
        agent.purpose,
        ...(agent.capabilities || [])
      ].join(' ').toLowerCase();

      return haystack.includes(q);
    });
  }, [agents, accessStatus, searchText, visibilityFilter]);

  const openAgentModal = (agent, mode = 'details') => {
    setSelectedAgent(agent);
    setModalMode(mode);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setTimeout(() => setSelectedAgent(null), 300);
  };

  return (
    <>
      <section className="market-header-row">
        <h3 className="market-title">Available Agents</h3>
        <span className="market-count">{agents.length} total</span>
      </section>

      <section className="market-controls">
        <input
          type="text"
          className="market-search"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Search by role, purpose, or capability..."
        />
        <div className="market-filters">
          <button
            type="button"
            className={`chip-btn ${visibilityFilter === 'all' ? 'active' : ''}`}
            onClick={() => setVisibilityFilter('all')}
          >
            All
          </button>
          <button
            type="button"
            className={`chip-btn ${visibilityFilter === 'demo' ? 'active' : ''}`}
            onClick={() => setVisibilityFilter('demo')}
          >
            Demo
          </button>
          <button
            type="button"
            className={`chip-btn ${visibilityFilter === 'owned' ? 'active' : ''}`}
            onClick={() => setVisibilityFilter('owned')}
          >
            Owned
          </button>
        </div>
      </section>

      {agents.length === 0 ? (
        <div className="empty-state">
          <h4>Agent cards are not loaded yet</h4>
          <p>Click reload to fetch agents from the backend.</p>
          <button type="button" className="btn btn-primary" onClick={onLoadAgents}>
            Reload Agents
          </button>
        </div>
      ) : (
      <div className="agent-grid">
        {visibleAgents.map((agent) => {
          const status = accessStatus[agent.id] || {};
          const isPurchased = status.is_purchased;
          const demoUsesLeft = status.demo_uses_left || 0;

          return (
            <div
              key={agent.id}
              className="agent-card"
              onClick={() => openAgentModal(agent, 'details')}
            >
              <div className="agent-card-top">
                <div className="agent-icon">AI</div>
                <div className="agent-card-tags">
                  <span className="domain-pill">{getDomainLabel(agent.id)}</span>
                  <span className="agent-id-pill">{agent.id}</span>
                </div>
              </div>
              <h3 className="agent-name">{agent.name}</h3>
              <p className="agent-description">{agent.description}</p>
              <div className="agent-purpose">
                <strong>Purpose:</strong> {agent.purpose}
              </div>

              <div className="buyer-fit-row">
                <span className="buyer-fit-badge">{getBuyerFitLabel(agent.id)}</span>
              </div>

              <div className="requirements-panel">
                <p className="requirements-title">Includes</p>
                <ul className="requirements-list">
                  {agent.capabilities.slice(0, 3).map((cap, idx) => (
                    <li key={idx}>{formatCapability(cap)}</li>
                  ))}
                </ul>
              </div>

              <div className="capabilities">
                {agent.capabilities.map((cap, idx) => (
                  <span key={idx} className="capability-badge">
                    {formatCapability(cap)}
                  </span>
                ))}
              </div>
              <div className="agent-status">
                {agent.status}
              </div>
              <div className="demo-badge">
                {isPurchased ? (
                  <span className="owned-text">✓ Owned</span>
                ) : (
                  <span>Demo: {demoUsesLeft} {demoUsesLeft !== 1 ? 'tries' : 'try'} left</span>
                )}
              </div>
              <div className="agent-actions-row">
                <button
                  className="btn btn-ghost"
                  onClick={(e) => {
                    e.stopPropagation();
                    openAgentModal(agent, 'details');
                  }}
                >
                  More Details
                </button>
                {isPurchased ? (
                  <button 
                    className="btn btn-success" 
                    onClick={(e) => {
                      e.stopPropagation();
                      openAgentModal(agent, 'purchase');
                    }}
                    title="Click to view access details and credentials"
                  >
                    Access
                  </button>
                ) : (
                  <button 
                    className="btn btn-primary" 
                    onClick={(e) => {
                      e.stopPropagation();
                      openAgentModal(agent, 'purchase');
                    }}
                  >
                    Buy
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
      )}

      {agents.length > 0 && visibleAgents.length === 0 && (
        <div className="empty-state">
          <h4>No agents match your filters</h4>
          <p>Try changing the search text or switching filter chips.</p>
        </div>
      )}

      {showModal && selectedAgent && (
        <AgentModal
          agent={selectedAgent}
          purchased={purchasedMap && purchasedMap[selectedAgent.id]}
          accessStatus={accessStatus[selectedAgent.id] || {}}
          mode={modalMode}
          theme={theme}
          authToken={authToken}
          apiBase={apiBase}
          onClose={handleCloseModal}
          onLoadAgents={onLoadAgents}
        />
      )}
    </>
  );
}

export default AgentGrid;
