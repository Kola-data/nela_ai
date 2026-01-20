import React, { useState, useRef } from 'react';
import { documentAPI } from '../services/api';
import { useUploads } from '../contexts/UploadContext';
import './DocumentUpload.css';

function DocumentUpload() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState({ type: '', text: '' });
  const { addUpload, updateUpload, removeUpload } = useUploads();
  const uploadStartTimeRef = useRef(null);
  const lastLoadedRef = useRef(0);
  const lastTimeRef = useRef(null);

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

    setMessage({ type: '', text: '' });
    
    // Create upload tracking object
    const uploadId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const upload = {
      id: uploadId,
      filename: file.name,
      progress: 0,
      status: 'uploading',
      speed: 'Calculating...',
      eta: 'Calculating...',
    };
    
    addUpload(upload);
    uploadStartTimeRef.current = Date.now();
    lastLoadedRef.current = 0;
    lastTimeRef.current = Date.now();
    setFile(null); // Clear file input to allow new uploads

    try {
      const result = await documentAPI.upload(file, (progressEvent) => {
        const { loaded, total, percent } = progressEvent;
        const now = Date.now();
        const timeElapsed = (now - lastTimeRef.current) / 1000; // seconds
        const bytesLoaded = loaded - lastLoadedRef.current;
        
        if (timeElapsed > 0 && bytesLoaded > 0) {
          const speed = bytesLoaded / timeElapsed; // bytes per second
          const remainingBytes = total - loaded;
          const etaSeconds = remainingBytes / speed;
          
          const formatSpeed = (bytes) => {
            if (bytes < 1024) return `${bytes.toFixed(0)} B/s`;
            if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB/s`;
            return `${(bytes / (1024 * 1024)).toFixed(1)} MB/s`;
          };
          
          const formatTime = (seconds) => {
            if (seconds < 60) return `${Math.ceil(seconds)}s`;
            const mins = Math.floor(seconds / 60);
            const secs = Math.ceil(seconds % 60);
            return `${mins}m ${secs}s`;
          };
          
          updateUpload(uploadId, {
            progress: percent,
            speed: formatSpeed(speed),
            eta: formatTime(etaSeconds),
          });
        } else {
          updateUpload(uploadId, {
            progress: percent,
          });
        }
        
        lastLoadedRef.current = loaded;
        lastTimeRef.current = now;
      });
      
      // Upload complete, now processing
      updateUpload(uploadId, {
        progress: 100,
        status: 'processing',
        speed: '',
        eta: '',
      });
      
      setMessage({ type: 'success', text: 'File uploaded successfully! Processing in background...' });
      
      // Poll for status updates
      if (result.task_id) {
        pollStatus(result.task_id, uploadId);
      } else {
        // If no task_id, mark as completed after a delay
        setTimeout(() => {
          updateUpload(uploadId, { status: 'completed' });
          setTimeout(() => removeUpload(uploadId), 3000);
        }, 1000);
      }
    } catch (err) {
      updateUpload(uploadId, {
        status: 'failed',
        progress: 0,
      });
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Upload failed. Please try again.',
      });
      // Remove failed upload after 5 seconds
      setTimeout(() => removeUpload(uploadId), 5000);
    }
  };

  const pollStatus = async (docId, uploadId) => {
    const maxAttempts = 60; // Increased for longer processing
    let attempts = 0;

    const interval = setInterval(async () => {
      attempts++;
      try {
        const status = await documentAPI.getStatus(docId);
        
        // Update progress based on status
        if (status.status === 'processing') {
          // Simulate progress during processing (0-90%)
          const processingProgress = Math.min(90, 50 + (attempts * 2));
          updateUpload(uploadId, {
            progress: processingProgress,
            status: 'processing',
          });
        }

        if (status.status === 'completed' || status.status === 'failed' || attempts >= maxAttempts) {
          clearInterval(interval);
          if (status.status === 'completed') {
            updateUpload(uploadId, {
              progress: 100,
              status: 'completed',
            });
            setMessage({ type: 'success', text: 'Document processed and indexed successfully!' });
            // Remove completed upload after 3 seconds
            setTimeout(() => removeUpload(uploadId), 3000);
          } else if (status.status === 'failed') {
            updateUpload(uploadId, {
              status: 'failed',
            });
            setMessage({ type: 'error', text: `Processing failed: ${status.error_message || 'Unknown error'}` });
            // Remove failed upload after 5 seconds
            setTimeout(() => removeUpload(uploadId), 5000);
          }
        }
      } catch (err) {
        clearInterval(interval);
        updateUpload(uploadId, {
          status: 'failed',
        });
        setTimeout(() => removeUpload(uploadId), 5000);
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
            style={{ marginTop: '1rem', width: '100%' }}
          >
            Upload Document
          </button>
        )}

        <p className="upload-note" style={{ marginTop: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          💡 You can continue using the app while files are uploading. Check the progress indicator in the top-right corner.
        </p>
      </div>
    </div>
  );
}

export default DocumentUpload;
