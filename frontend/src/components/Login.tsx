import React, { useState } from 'react';
import { authAPI } from '../services/api';
import { LoginData } from '../types';

interface LoginProps {
  onLogin: (token: string) => void;
  onSwitchToRegister: () => void;
}

const Login: React.FC<LoginProps> = ({ onLogin, onSwitchToRegister }) => {
  const [formData, setFormData] = useState<LoginData>({
    username: '',
    password: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await authAPI.login(formData);
      const { access_token } = response.data;
      setError('');
      onLogin(access_token);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDismissError = () => {
    setError('');
  };

  return (
    <div className="auth-form">
      <h2>Welcome Back</h2>
      
      {error && (
        <div className="error-message" style={{ position: 'relative', paddingRight: '40px' }}>
          {error}
          <button
            type="button"
            onClick={handleDismissError}
            style={{
              position: 'absolute',
              right: '8px',
              top: '8px',
              background: 'none',
              border: 'none',
              fontSize: '18px',
              cursor: 'pointer',
              color: '#9b2c2c',
              padding: '0',
              lineHeight: '1',
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Close"
          >
            ×
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            required
            autoFocus
          />
        </div>

        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
          />
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={isLoading}>
            {isLoading ? 'Signing In...' : 'Sign In'}
          </button>
        </div>
      </form>

      <div className="auth-switch">
        Don't have an account?{' '}
        <button type="button" onClick={onSwitchToRegister}>
          Sign up here
        </button>
      </div>
    </div>
  );
};

export default Login; 