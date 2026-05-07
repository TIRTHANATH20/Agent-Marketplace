import React, { useState, useEffect } from 'react';
import axios from 'axios';

function MCPToolsGrid({ authToken, apiBase }) {
  const [mcpServers, setMcpServers] = useState([]);
  const [purchasedServers, setPurchasedServers] = useState({});
  const [agentNames, setAgentNames] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [purchasing, setPurchasing] = useState({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Load MCP servers
      const serversRes = await axios.get(`${apiBase}/mcp-servers`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setMcpServers(serversRes.data);

      // Load purchased MCP servers
      const purchasesRes = await axios.get(`${apiBase}/users/me/mcp-purchases`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      const purchased = {};
      purchasesRes.data.purchased_mcp_servers.forEach(server_id => {
        purchased[server_id] = true;
      });
      setPurchasedServers(purchased);

      // Load all agents to show which use each tool
      const agentsRes = await axios.get(`${apiBase}/agents`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      const agents = {};
      agentsRes.data.forEach(agent => {
        agents[agent.id] = agent;
      });
      setAgentNames(agents);

      setError('');
    } catch (err) {
      setError('Error loading data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async (serverId) => {
    if (purchasedServers[serverId]) {
      // Already purchased, show message
      alert('This MCP tool is already installed!');
      return;
    }

    setPurchasing(prev => ({ ...prev, [serverId]: true }));
    try {
      const response = await axios.post(
        `${apiBase}/mcp-servers/${serverId}/purchase`,
        {},
        { headers: { Authorization: `Bearer ${authToken}` } }
      );

      // Update purchased list
      setPurchasedServers(prev => ({ ...prev, [serverId]: true }));
      
      alert(`✓ ${response.data.server_name} installed successfully!\n\nUsed by agents: ${response.data.agents_using_this.join(', ')}`);
    } catch (err) {
      alert('Error installing MCP tool: ' + (err.response?.data?.detail || err.message));
      console.error(err);
    } finally {
      setPurchasing(prev => ({ ...prev, [serverId]: false }));
    }
  };

  const getAgentsUsingServer = (serverId) => {
    return Object.values(agentNames)
      .filter(agent => agent.mcp_server_ids && agent.mcp_server_ids.includes(serverId))
      .map(agent => agent.name);
  };

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading MCP Tools...</div>;
  }

  return (
    <div style={{ padding: '2rem' }}>
      <h2 style={{ marginBottom: '1.5rem', color: '#333' }}>🔧 Available MCP Servers & Tools</h2>
      
      {error && (
        <div style={{
          padding: '1rem',
          backgroundColor: '#fee',
          color: '#c33',
          borderRadius: '0.5rem',
          marginBottom: '1rem'
        }}>
          {error}
        </div>
      )}

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
        gap: '1.5rem'
      }}>
        {mcpServers.map(server => {
          const isInstalled = purchasedServers[server.id];
          const agentsUsing = getAgentsUsingServer(server.id);
          const isInstalling = purchasing[server.id];

          return (
            <div
              key={server.id}
              style={{
                border: isInstalled ? '2px solid #4caf50' : '1px solid #ddd',
                borderRadius: '0.5rem',
                padding: '1.5rem',
                backgroundColor: isInstalled ? '#f1f8f4' : '#f9f9f9',
                boxShadow: isInstalled ? '0 2px 8px rgba(76,175,80,0.2)' : '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'transform 0.2s, box-shadow 0.2s',
                cursor: 'pointer'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = isInstalled 
                  ? '0 4px 12px rgba(76,175,80,0.3)' 
                  : '0 4px 12px rgba(0,0,0,0.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = isInstalled 
                  ? '0 2px 8px rgba(76,175,80,0.2)' 
                  : '0 2px 8px rgba(0,0,0,0.1)';
              }}
            >
              {/* Header */}
              <div style={{ marginBottom: '0.75rem' }}>
                <h3 style={{ margin: '0 0 0.25rem 0', color: '#333' }}>{server.name}</h3>
                <div style={{
                  display: 'inline-block',
                  padding: '0.25rem 0.75rem',
                  backgroundColor: '#e3f2fd',
                  color: '#1976d2',
                  borderRadius: '1rem',
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  marginRight: '0.5rem'
                }}>
                  {server.category}
                </div>
                <div style={{
                  display: 'inline-block',
                  padding: '0.25rem 0.75rem',
                  backgroundColor: isInstalled ? '#c8e6c9' : '#c8e6c9',
                  color: isInstalled ? '#2e7d32' : '#2e7d32',
                  borderRadius: '1rem',
                  fontSize: '0.75rem',
                  fontWeight: 'bold'
                }}>
                  {isInstalled ? '✓ Installed' : server.status}
                </div>
              </div>

              {/* Description */}
              <p style={{
                margin: '0.75rem 0',
                color: '#666',
                fontSize: '0.95rem',
                lineHeight: '1.4'
              }}>
                {server.description}
              </p>

              {/* Tools List */}
              <div style={{ marginTop: '1rem', marginBottom: '1rem' }}>
                <p style={{
                  margin: '0 0 0.5rem 0',
                  color: '#333',
                  fontWeight: 'bold',
                  fontSize: '0.9rem'
                }}>
                  📋 Available Tools:
                </p>
                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '0.5rem'
                }}>
                  {server.tools.map((tool, idx) => (
                    <span
                      key={idx}
                      style={{
                        padding: '0.25rem 0.6rem',
                        backgroundColor: '#f0f0f0',
                        border: '1px solid #ddd',
                        borderRadius: '0.25rem',
                        fontSize: '0.8rem',
                        color: '#555'
                      }}
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              </div>

              {/* Agents Using This Tool */}
              {agentsUsing.length > 0 && (
                <div style={{ marginTop: '1rem', marginBottom: '1rem', paddingTop: '1rem', borderTop: '1px solid #eee' }}>
                  <p style={{
                    margin: '0 0 0.5rem 0',
                    color: '#333',
                    fontWeight: 'bold',
                    fontSize: '0.9rem'
                  }}>
                    👥 Used by Agents:
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {agentsUsing.map((agentName, idx) => (
                      <span
                        key={idx}
                        style={{
                          padding: '0.25rem 0.6rem',
                          backgroundColor: '#ffe0b2',
                          border: '1px solid #ffb74d',
                          borderRadius: '0.25rem',
                          fontSize: '0.75rem',
                          color: '#e65100'
                        }}
                      >
                        {agentName}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Footer */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderTop: '1px solid #eee',
                paddingTop: '0.75rem',
                marginTop: '0.75rem'
              }}>
                <div style={{
                  color: '#2e7d32',
                  fontWeight: 'bold',
                  fontSize: '0.95rem'
                }}>
                  {server.price === 0 ? 'Free' : `$${server.price}`}
                </div>
                <button
                  onClick={() => handleInstall(server.id)}
                  disabled={isInstalling}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: isInstalled ? '#4caf50' : '#2196f3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.25rem',
                    cursor: isInstalling ? 'wait' : 'pointer',
                    fontSize: '0.9rem',
                    fontWeight: 'bold',
                    opacity: isInstalling ? 0.7 : 1,
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    if (!isInstalling && !isInstalled) {
                      e.target.style.backgroundColor = '#1976d2';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isInstalling && !isInstalled) {
                      e.target.style.backgroundColor = '#2196f3';
                    }
                  }}
                >
                  {isInstalling ? 'Installing...' : isInstalled ? '✓ Installed' : 'Install'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {mcpServers.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          color: '#999'
        }}>
          No MCP servers available
        </div>
      )}
    </div>
  );
}

export default MCPToolsGrid;
