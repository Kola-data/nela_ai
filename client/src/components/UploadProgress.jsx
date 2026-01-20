import React from 'react';
import './UploadProgress.css';

function UploadProgress({ uploads }) {
  if (!uploads || uploads.length === 0) return null;

  return (
    <div className="upload-progress-container">
      {uploads.map((upload) => (
        <div key={upload.id} className="upload-progress-item">
          <div className="upload-progress-header">
            <span className="upload-filename">{upload.filename}</span>
            <span className="upload-percentage">{upload.progress}%</span>
          </div>
          <div className="progress-bar-container">
            <div 
              className="progress-bar" 
              style={{ width: `${upload.progress}%` }}
            ></div>
          </div>
          <div className="upload-progress-info">
            {upload.status === 'uploading' && (
              <>
                <span className="upload-speed">{upload.speed}</span>
                <span className="upload-eta">{upload.eta}</span>
              </>
            )}
            {upload.status === 'processing' && (
              <span className="upload-status-text">Processing document...</span>
            )}
            {upload.status === 'completed' && (
              <span className="upload-status-text success">✓ Completed</span>
            )}
            {upload.status === 'failed' && (
              <span className="upload-status-text error">✗ Failed</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default UploadProgress;
