import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import AuthModal from './components/AuthModal';
import MainContent from './components/MainContent';

const API_BASE = process.env.REACT_APP_API_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : '');

function App() {
  const [authToken, setAuthToken] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem('app-theme') || 'light');
  const [agents, setAgents] = useState([]);
  const [purchasedMap, setPurchasedMap] = useState({});
  const [accessStatus, setAccessStatus] = useState({});
  const [logs, setLogs] = useState([]);
  const [commHistory, setCommHistory] = useState([]);

  useEffect(() => {
    if (authToken) {
      loadAgents();
      loadCommunicationHistory();
      loadLogs();
    }
  }, [authToken]);

  useEffect(() => {
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('app-theme', theme);
  }, [theme]);

  const loadAgents = async () => {
    try {
      const res = await axios.get(`${API_BASE}/agents`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      setAgents(res.data);

      const purchasesRes = await axios.get(`${API_BASE}/users/me/purchases`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      setPurchasedMap(purchasesRes.data.purchases || {});

      const accessRes = await axios.get(`${API_BASE}/agents/my-access-status`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      setAccessStatus(accessRes.data || {});
    } catch (error) {
      console.error('Failed to load agents:', error);
    }
  };

  const loadCommunicationHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE}/agents/communication/history?limit=20`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      setCommHistory(res.data);
    } catch (error) {
      console.error('Failed to load communication history:', error);
    }
  };

  const loadLogs = async () => {
    try {
      const res = await axios.get(`${API_BASE}/logs?limit=100`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      setLogs(res.data);
    } catch (error) {
      console.error('Failed to load logs:', error);
    }
  };

  const handleLogin = (token, user) => {
    setAuthToken(token);
    setCurrentUser(user);
  };

  const handleLogout = async () => {
    try {
      if (authToken) {
        await axios.post(`${API_BASE}/auth/logout`, {}, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
      }
    } catch (error) {
      console.error('Logout API failed:', error);
    } finally {
      setAuthToken(null);
      setCurrentUser(null);
    }
  };

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  if (!authToken) {
    return <AuthModal onLogin={handleLogin} apiBase={API_BASE} />;
  }

  return (
    <MainContent
      currentUser={currentUser}
      onLogout={handleLogout}
      theme={theme}
      onToggleTheme={handleToggleTheme}
      agents={agents}
      purchasedMap={purchasedMap}
      accessStatus={accessStatus}
      logs={logs}
      commHistory={commHistory}
      authToken={authToken}
      apiBase={API_BASE}
      onLoadAgents={loadAgents}
      onLoadLogs={loadLogs}
      onLoadHistory={loadCommunicationHistory}
    />
  );
}

export default App;
