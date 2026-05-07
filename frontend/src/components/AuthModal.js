import React, { useState } from 'react';
import axios from 'axios';

function AuthModal({ onLogin, apiBase }) {
  const [loginTab, setLoginTab] = useState(true);
  const [loginUsername, setLoginUsername] = useState('admin');
  const [loginPassword, setLoginPassword] = useState('admin123');
  const [registerUsername, setRegisterUsername] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const applyDemoAccount = (username, password) => {
    setLoginTab(true);
    setError('');
    setLoginUsername(username);
    setLoginPassword(password);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    try {
      const res = await axios.post(`${apiBase}/auth/login`, {
        username: loginUsername,
        password: loginPassword
      });
      onLogin(res.data.access_token, res.data.user);
    } catch (err) {
      setError('Login failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    try {
      const res = await axios.post(`${apiBase}/auth/register`, {
        username: registerUsername,
        password: registerPassword
      });
      onLogin(res.data.access_token, res.data.user);
    } catch (err) {
      setError('Registration failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-modal">
      <div className="auth-container">
        <section className="auth-form-side">
          <h1 className="auth-title">Agent Marketplace</h1>
          <h3 className="auth-form-heading">Sign In</h3>
          <p className="auth-form-subheading">
            {loginTab ? 'Enter credentials.' : 'Create account.'}
          </p>
          <div className="auth-tabs">
            <button
              className={`auth-tab ${loginTab ? 'active' : ''}`}
              onClick={() => {
                setError('');
                setLoginTab(true);
              }}
              disabled={isSubmitting}
            >
              Login
            </button>
            <button
              className={`auth-tab ${!loginTab ? 'active' : ''}`}
              onClick={() => {
                setError('');
                setLoginTab(false);
              }}
              disabled={isSubmitting}
            >
              Register
            </button>
          </div>

          {error && <div className="auth-error">{error}</div>}

          {loginTab ? (
            <form className="auth-form active" onSubmit={handleLogin}>
              <label className="auth-label" htmlFor="login-username">Username</label>
              <input
                id="login-username"
                type="text"
                placeholder="Enter username"
                value={loginUsername}
                onChange={(e) => setLoginUsername(e.target.value)}
                disabled={isSubmitting}
                required
              />
              <label className="auth-label" htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                placeholder="Enter password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                disabled={isSubmitting}
                required
              />
              <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Signing In...' : 'Login'}
              </button>
              <p className="auth-helper">Quick demo login.</p>
              <div className="auth-demo-actions auth-demo-inline">
                <button type="button" className="auth-demo-btn" onClick={() => applyDemoAccount('admin', 'admin123')} disabled={isSubmitting}>
                  admin
                </button>
                <button type="button" className="auth-demo-btn" onClick={() => applyDemoAccount('user1', 'user123')} disabled={isSubmitting}>
                  user1
                </button>
              </div>
            </form>
          ) : (
            <form className="auth-form active" onSubmit={handleRegister}>
              <label className="auth-label" htmlFor="register-username">Username</label>
              <input
                id="register-username"
                type="text"
                placeholder="Choose username"
                value={registerUsername}
                onChange={(e) => setRegisterUsername(e.target.value)}
                disabled={isSubmitting}
                required
              />
              <label className="auth-label" htmlFor="register-password">Password</label>
              <input
                id="register-password"
                type="password"
                placeholder="Choose password"
                value={registerPassword}
                onChange={(e) => setRegisterPassword(e.target.value)}
                disabled={isSubmitting}
                required
              />
              <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Creating Account...' : 'Create Account'}
              </button>
            </form>
          )}

        </section>
      </div>
    </div>
  );
}

export default AuthModal;
