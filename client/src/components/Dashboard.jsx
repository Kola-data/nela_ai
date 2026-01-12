import React, { useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import Navbar from './Navbar';
import Footer from './Footer';
import DocumentUpload from './DocumentUpload';
import AIQuery from './AIQuery';
import FileList from './FileList';
import ConversationHistory from './ConversationHistory';
import './Dashboard.css';

function Dashboard({ setIsAuthenticated }) {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('query');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      const userData = await authAPI.getCurrentUser();
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
    } catch (err) {
      console.error('Failed to load user:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <Navbar user={user} onLogout={handleLogout} />
      <div className="dashboard-container">
        <div className="dashboard-sidebar">
          <nav className="sidebar-nav">
            <button
              className={`nav-item ${activeTab === 'query' ? 'active' : ''}`}
              onClick={() => setActiveTab('query')}
            >
              <span>💬</span> AI Query
            </button>
            <button
              className={`nav-item ${activeTab === 'upload' ? 'active' : ''}`}
              onClick={() => setActiveTab('upload')}
            >
              <span>📄</span> Upload Documents
            </button>
            <button
              className={`nav-item ${activeTab === 'files' ? 'active' : ''}`}
              onClick={() => setActiveTab('files')}
            >
              <span>📁</span> My Files
            </button>
            <button
              className={`nav-item ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              <span>🕐</span> History
            </button>
          </nav>
        </div>

        <div className="dashboard-content">
          {activeTab === 'query' && <AIQuery />}
          {activeTab === 'upload' && <DocumentUpload />}
          {activeTab === 'files' && <FileList />}
          {activeTab === 'history' && <ConversationHistory />}
        </div>
      </div>
      <Footer />
    </div>
  );
}

export default Dashboard;
