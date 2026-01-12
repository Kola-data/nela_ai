import React, { useState, useEffect, useRef } from 'react';
import { aiAPI } from '../services/api';
import './AIQuery.css';

function AIQuery() {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadHistory = async () => {
    try {
      const history = await aiAPI.getConversationHistory(20);
      if (history.messages && history.messages.length > 0) {
        const formattedMessages = history.messages.map((msg) => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp,
          sources: msg.sources || [],
        }));
        setMessages(formattedMessages);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;

    const userMessage = {
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setPrompt('');
    setLoading(true);
    setError('');

    try {
      const response = await aiAPI.query(prompt);
      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toISOString(),
        sources: response.sources || [],
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to get AI response. Please try again.');
      setMessages((prev) => prev.slice(0, -1)); // Remove user message on error
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    if (window.confirm('Are you sure you want to clear all conversation history?')) {
      try {
        await aiAPI.clearConversationHistory();
        setMessages([]);
      } catch (err) {
        setError('Failed to clear history. Please try again.');
      }
    }
  };

  return (
    <div className="ai-query fade-in">
      <div className="query-header">
        <h2 className="section-title">Ask Nela</h2>
        <p className="section-subtitle">Ask Nela questions about your uploaded documents</p>
        {messages.length > 0 && (
          <button onClick={clearHistory} className="btn btn-secondary" style={{ marginTop: '1rem' }}>
            Clear History
          </button>
        )}
      </div>

      <div className="chat-container">
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">💬</span>
              <p>Start a conversation with Nela by asking a question about your documents</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`message message-${msg.role}`}>
                <div className="message-content">
                  <p>{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="message-sources">
                      <strong>Sources:</strong> {msg.sources.join(', ')}
                    </div>
                  )}
                </div>
                <div className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="message message-assistant">
              <div className="message-content">
                <div className="loading-indicator">
                  <span className="spinner"></span>
                  <span>Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="query-form">
          <textarea
            className="input-field query-input"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask a question about your documents..."
            rows="3"
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !prompt.trim()}>
            {loading ? (
              <>
                <span className="spinner"></span> Processing...
              </>
            ) : (
              <>
                <span>📤</span> Send
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AIQuery;
