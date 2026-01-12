import React, { useState, useEffect } from 'react';
import { aiAPI } from '../services/api';
import './ConversationHistory.css';

function ConversationHistory() {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const data = await aiAPI.getConversationHistory(50);
      setHistory(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load conversation history');
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    if (window.confirm('Are you sure you want to clear all conversation history?')) {
      try {
        await aiAPI.clearConversationHistory();
        setHistory({ message_count: 0, messages: [], conversation_context: '' });
      } catch (err) {
        setError('Failed to clear history. Please try again.');
      }
    }
  };

  if (loading) {
    return (
      <div className="conversation-history fade-in">
        <div className="loading">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="conversation-history fade-in">
      <div className="history-header">
        <h2 className="section-title">Conversation History</h2>
        <p className="section-subtitle">View your past conversations with Nela</p>
        {history && history.message_count > 0 && (
          <button onClick={clearHistory} className="btn btn-danger">
            Clear All History
          </button>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      {history && history.conversation_context && (
        <div className="card context-card">
          <h3>Conversation Context</h3>
          <p>{history.conversation_context}</p>
        </div>
      )}

      {history && history.messages && history.messages.length > 0 ? (
        <div className="history-messages">
          {history.messages.map((msg, idx) => (
            <div key={idx} className={`history-message message-${msg.role}`}>
              <div className="message-header">
                <span className="message-role">{msg.role === 'user' ? '👤 You' : '🤖 AI'}</span>
                <span className="message-time">
                  {new Date(msg.timestamp).toLocaleString()}
                </span>
              </div>
              <div className="message-body">{msg.content}</div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <strong>Sources:</strong> {msg.sources.join(', ')}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🕐</span>
            <p>No conversation history yet</p>
            <p className="empty-hint">Start chatting with Nela to see your history here</p>
          </div>
        </div>
      )}

      <button onClick={loadHistory} className="btn btn-secondary" style={{ marginTop: '1rem' }}>
        Refresh
      </button>
    </div>
  );
}

export default ConversationHistory;
