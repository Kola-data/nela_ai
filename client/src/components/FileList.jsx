import React, { useState, useEffect, useRef } from 'react';
import { documentAPI } from '../services/api';
import './FileList.css';

function FileList() {
  const [files, setFiles] = useState([]);
  const [storageInfo, setStorageInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(null);
  const [fileStatuses, setFileStatuses] = useState({});
  const pollingIntervalsRef = useRef({});

  useEffect(() => {
    loadFiles();
    return () => {
      // Cleanup polling intervals on unmount
      Object.values(pollingIntervalsRef.current).forEach(interval => clearInterval(interval));
    };
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
      
      // Start polling for files that are pending or processing
      startStatusPolling(filesData.files || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const startStatusPolling = (filesList) => {
    // Clear existing intervals
    Object.values(pollingIntervalsRef.current).forEach(interval => clearInterval(interval));
    pollingIntervalsRef.current = {};

    filesList.forEach((file) => {
      const fileObj = typeof file === 'string' ? { id: null, filename: file } : file;
      
      // Only poll for files with IDs that are pending or processing
      if (fileObj.id && (fileObj.status === 'pending' || fileObj.status === 'processing')) {
        pollFileStatus(fileObj.id);
      } else if (fileObj.id) {
        // Set initial status for completed/failed files
        setFileStatuses(prev => ({
          ...prev,
          [fileObj.id]: {
            status: fileObj.status,
            progress: fileObj.status === 'completed' ? 100 : 0,
          }
        }));
      }
    });
  };

  const pollFileStatus = (fileId) => {
    // Clear existing interval for this file if any
    if (pollingIntervalsRef.current[fileId]) {
      clearInterval(pollingIntervalsRef.current[fileId]);
    }

    let attempts = 0;
    const maxAttempts = 60; // Poll for up to 2 minutes (60 * 2 seconds)

    const poll = async () => {
      attempts++;
      try {
        const status = await documentAPI.getStatus(fileId);
        
        // Calculate progress based on status
        let progress = 0;
        if (status.status === 'pending') {
          progress = 10;
        } else if (status.status === 'processing') {
          // Simulate progress: start at 20%, gradually increase
          progress = Math.min(90, 20 + (attempts * 2));
        } else if (status.status === 'completed') {
          progress = 100;
        }

        setFileStatuses(prev => ({
          ...prev,
          [fileId]: {
            status: status.status,
            progress: progress,
            error_message: status.error_message,
          }
        }));

        // Stop polling if completed, failed, or max attempts reached
        if (status.status === 'completed' || status.status === 'failed' || attempts >= maxAttempts) {
          if (pollingIntervalsRef.current[fileId]) {
            clearInterval(pollingIntervalsRef.current[fileId]);
            delete pollingIntervalsRef.current[fileId];
          }
          
          // Reload files to get updated list
          if (status.status === 'completed' || status.status === 'failed') {
            setTimeout(() => loadFiles(), 1000);
          }
        }
      } catch (err) {
        console.error(`Failed to poll status for file ${fileId}:`, err);
        // Stop polling on error
        if (pollingIntervalsRef.current[fileId]) {
          clearInterval(pollingIntervalsRef.current[fileId]);
          delete pollingIntervalsRef.current[fileId];
        }
      }
    };

    // Poll immediately, then every 2 seconds
    poll();
    pollingIntervalsRef.current[fileId] = setInterval(poll, 2000);
  };

  const handleDelete = async (fileId, filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      setDeleting(fileId);
      setError('');
      await documentAPI.delete(fileId);
      // Reload files after successful deletion
      await loadFiles();
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
          {files.map((file) => {
            const fileObj = typeof file === 'string' ? { id: null, filename: file } : file;
            const fileStatus = fileObj.id ? fileStatuses[fileObj.id] : null;
            const currentStatus = fileStatus?.status || fileObj.status;
            const currentProgress = fileStatus?.progress ?? (currentStatus === 'completed' ? 100 : currentStatus === 'processing' ? 50 : currentStatus === 'pending' ? 10 : 0);
            const isProcessing = currentStatus === 'pending' || currentStatus === 'processing';
            
            return (
              <div key={fileObj.id || fileObj.filename} className="file-card card">
                <div className="file-icon">📄</div>
                <div className="file-info">
                  <h4 className="file-name">{fileObj.filename}</h4>
                  {currentStatus && (
                    <span className={`status-badge status-${currentStatus?.toLowerCase()}`}>
                      {currentStatus}
                    </span>
                  )}
                  
                  {/* Progress bar for processing files */}
                  {isProcessing && fileObj.id && (
                    <div className="file-progress-container">
                      <div className="file-progress-bar-container">
                        <div 
                          className="file-progress-bar" 
                          style={{ width: `${currentProgress}%` }}
                        ></div>
                      </div>
                      <div className="file-progress-text">
                        <span className="file-progress-percentage">{currentProgress}%</span>
                        {currentStatus === 'processing' && (
                          <span className="file-progress-status">Processing...</span>
                        )}
                        {currentStatus === 'pending' && (
                          <span className="file-progress-status">Waiting to process...</span>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {fileStatus?.error_message && (
                    <div className="file-error-message">
                      {fileStatus.error_message}
                    </div>
                  )}
                </div>
                {fileObj.id ? (
                  <button
                    onClick={() => handleDelete(fileObj.id, fileObj.filename)}
                    className="btn btn-danger btn-sm"
                    disabled={deleting === fileObj.id}
                  >
                    {deleting === fileObj.id ? (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="spinner"></span>
                        <span>Deleting...</span>
                      </span>
                    ) : (
                      'Delete'
                    )}
                  </button>
                ) : (
                  <button
                    className="btn btn-danger btn-sm"
                    disabled
                    title="File ID not available"
                  >
                    Delete
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      <button onClick={loadFiles} className="btn btn-secondary" style={{ marginTop: '1rem' }}>
        Refresh
      </button>
    </div>
  );
}

export default FileList;
