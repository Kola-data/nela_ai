import React, { useState, useEffect } from 'react';
import { documentAPI } from '../services/api';
import './FileList.css';

function FileList() {
  const [files, setFiles] = useState([]);
  const [storageInfo, setStorageInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      setLoading(true);
      const [filesData, storageData] = await Promise.all([
        documentAPI.listFiles(),
        documentAPI.getStorageInfo(),
      ]);
      setFiles(filesData.files || []);
      setStorageInfo(storageData);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      setDeleting(filename);
      // Note: We need document ID to delete, but API returns only filenames
      // This is a limitation - we'd need to modify the API or store document IDs
      setError('Delete functionality requires document ID. Please check the API.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete file');
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return (
      <div className="file-list fade-in">
        <div className="loading">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="file-list fade-in">
      <h2 className="section-title">My Files</h2>
      <p className="section-subtitle">Manage your uploaded documents</p>

      {storageInfo && (
        <div className="storage-summary card">
          <h3>Storage Information</h3>
          <div className="storage-stats">
            <div className="stat-item">
              <span className="stat-label">Total Files:</span>
              <span className="stat-value">{storageInfo.file_count || 0}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Total Size:</span>
              <span className="stat-value">
                {storageInfo.total_size_mb ? `${storageInfo.total_size_mb.toFixed(2)} MB` : '0 MB'}
              </span>
            </div>
          </div>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {files.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">📁</span>
            <p>No files uploaded yet</p>
            <p className="empty-hint">Upload documents to get started</p>
          </div>
        </div>
      ) : (
        <div className="files-grid">
          {files.map((filename, idx) => (
            <div key={idx} className="file-card card">
              <div className="file-icon">📄</div>
              <div className="file-info">
                <h4 className="file-name">{filename}</h4>
              </div>
              <button
                onClick={() => handleDelete(filename)}
                className="btn btn-danger btn-sm"
                disabled={deleting === filename}
              >
                {deleting === filename ? <span className="spinner"></span> : 'Delete'}
              </button>
            </div>
          ))}
        </div>
      )}

      <button onClick={loadFiles} className="btn btn-secondary" style={{ marginTop: '1rem' }}>
        Refresh
      </button>
    </div>
  );
}

export default FileList;
