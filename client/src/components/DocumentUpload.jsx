import React, { useState } from 'react';
import { documentAPI } from '../services/api';
import './DocumentUpload.css';

function DocumentUpload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [uploadStatus, setUploadStatus] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith('.txt') || selectedFile.name.endsWith('.pdf') || selectedFile.name.endsWith('.md')) {
        setFile(selectedFile);
        setMessage({ type: '', text: '' });
      } else {
        setMessage({ type: 'error', text: 'Only .txt, .pdf, and .md files are supported' });
        setFile(null);
      }
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      if (droppedFile.name.endsWith('.txt') || droppedFile.name.endsWith('.pdf') || droppedFile.name.endsWith('.md')) {
        setFile(droppedFile);
        setMessage({ type: '', text: '' });
      } else {
        setMessage({ type: 'error', text: 'Only .txt, .pdf, and .md files are supported' });
        setFile(null);
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleUpload = async () => {
    if (!file) {
      setMessage({ type: 'error', text: 'Please select a file first' });
      return;
    }

    setUploading(true);
    setMessage({ type: '', text: '' });

    try {
      const result = await documentAPI.upload(file);
      setMessage({ type: 'success', text: 'File uploaded successfully! Processing in background...' });
      setUploadStatus(result);
      setFile(null);
      
      // Poll for status updates
      if (result.task_id) {
        pollStatus(result.task_id);
      }
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Upload failed. Please try again.',
      });
    } finally {
      setUploading(false);
    }
  };

  const pollStatus = async (docId) => {
    const maxAttempts = 30;
    let attempts = 0;

    const interval = setInterval(async () => {
      attempts++;
      try {
        const status = await documentAPI.getStatus(docId);
        setUploadStatus(status);

        if (status.status === 'completed' || status.status === 'failed' || attempts >= maxAttempts) {
          clearInterval(interval);
          if (status.status === 'completed') {
            setMessage({ type: 'success', text: 'Document processed and indexed successfully!' });
          } else if (status.status === 'failed') {
            setMessage({ type: 'error', text: `Processing failed: ${status.error_message || 'Unknown error'}` });
          }
        }
      } catch (err) {
        clearInterval(interval);
      }
    }, 2000);
  };

  return (
    <div className="document-upload fade-in">
      <h2 className="section-title">Upload Document</h2>
      <p className="section-subtitle">Upload documents for Nela to analyze. Supported formats: .txt, .pdf, .md</p>

      <div className="card">
        {message.text && (
          <div className={message.type === 'error' ? 'error-message' : 'success-message'}>
            {message.text}
          </div>
        )}

        <div
          className={`file-upload-area ${file ? 'has-file' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <input
            type="file"
            id="file-input"
            accept=".txt,.pdf,.md"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <label htmlFor="file-input" className="file-upload-label">
            {file ? (
              <>
                <span className="file-icon">📄</span>
                <span className="file-name">{file.name}</span>
                <span className="file-size">({(file.size / 1024).toFixed(2)} KB)</span>
              </>
            ) : (
              <>
                <span className="file-icon">📤</span>
                <span>Click to select or drag and drop</span>
                <span className="file-hint">Supports .txt, .pdf, .md files</span>
              </>
            )}
          </label>
        </div>

        {file && (
          <button
            onClick={handleUpload}
            className="btn btn-primary"
            disabled={uploading}
            style={{ marginTop: '1rem', width: '100%' }}
          >
            {uploading ? (
              <>
                <span className="spinner"></span> Uploading...
              </>
            ) : (
              'Upload Document'
            )}
          </button>
        )}

        {uploadStatus && (
          <div className="upload-status" style={{ marginTop: '1.5rem' }}>
            <h3>Upload Status</h3>
            <div className="status-info">
              <p>
                <strong>File:</strong> {uploadStatus.filename}
              </p>
              <p>
                <strong>Status:</strong>{' '}
                <span className={`status-badge status-${uploadStatus.status?.toLowerCase()}`}>
                  {uploadStatus.status}
                </span>
              </p>
              {uploadStatus.error_message && (
                <p className="error-text">
                  <strong>Error:</strong> {uploadStatus.error_message}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default DocumentUpload;
