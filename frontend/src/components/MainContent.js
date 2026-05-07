import React, { useState, useEffect } from 'react';
import AgentGrid from './AgentGrid';
import AgentModal from './AgentModal';

function MainContent({
  currentUser,
  onLogout,
  theme,
  onToggleTheme,
  agents,
  purchasedMap,
  accessStatus,
  logs,
  commHistory,
  authToken,
  apiBase,
  onLoadAgents,
  onLoadLogs,
  onLoadHistory
}) {
  const [directAgentId, setDirectAgentId] = useState(null);
  const ownedCount = Object.values(accessStatus || {}).filter((s) => s && s.is_purchased).length;

  // Check URL for direct agent access (without exposing tokens in URL)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const agentId = params.get('agent');
    if (agentId) {
      setDirectAgentId(agentId);
      // Clean up URL to remove any exposed tokens/keys
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-title-group">
          <h1>Agent Marketplace</h1>
        </div>
        <div className="user-info">
          <button className="theme-btn" onClick={onToggleTheme} type="button">
            {theme === 'light' ? 'Light' : 'Dark'} Mode
          </button>
          <span>Logged in as: <strong>{currentUser}</strong></span>
          <button className="logout-btn" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="main-content">
        <section className="hero-panel">
          <h2 className="hero-title">Choose an agent and run tasks fast.</h2>
          <p className="hero-subtitle">
            All agents now follow strict LLM response rules with role-specific behavior.
          </p>
          <div className="hero-stats">
            <div className="hero-stat">
              <span className="hero-stat-label">Available Agents</span>
              <span className="hero-stat-value">{agents.length}</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat-label">Owned</span>
              <span className="hero-stat-value">{ownedCount}</span>
            </div>
          </div>
        </section>

        <div className="tab-content active">
          <AgentGrid
            agents={agents}
            purchasedMap={purchasedMap}
            accessStatus={accessStatus}
            theme={theme}
            authToken={authToken}
            apiBase={apiBase}
            onLoadAgents={onLoadAgents}
          />
        </div>

      </main>

      {directAgentId && agents.length > 0 && (
        <AgentModal
          agent={agents.find(a => a.id === directAgentId)}
          purchased={purchasedMap && purchasedMap[directAgentId]}
          accessStatus={accessStatus[directAgentId] || {}}
          theme={theme}
          authToken={authToken}
          apiBase={apiBase}
          onClose={() => {
            setDirectAgentId(null);
            window.history.pushState({}, '', window.location.pathname);
          }}
          onLoadAgents={onLoadAgents}
        />
      )}
    </div>
  );
}

export default MainContent;
