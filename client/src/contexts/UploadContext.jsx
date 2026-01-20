import React, { createContext, useContext, useState, useCallback } from 'react';

const UploadContext = createContext();

export const useUploads = () => {
  const context = useContext(UploadContext);
  if (!context) {
    throw new Error('useUploads must be used within UploadProvider');
  }
  return context;
};

export const UploadProvider = ({ children }) => {
  const [uploads, setUploads] = useState([]);

  const addUpload = useCallback((upload) => {
    setUploads((prev) => [...prev, upload]);
  }, []);

  const updateUpload = useCallback((id, updates) => {
    setUploads((prev) =>
      prev.map((upload) => (upload.id === id ? { ...upload, ...updates } : upload))
    );
  }, []);

  const removeUpload = useCallback((id) => {
    setUploads((prev) => prev.filter((upload) => upload.id !== id));
  }, []);

  return (
    <UploadContext.Provider value={{ uploads, addUpload, updateUpload, removeUpload }}>
      {children}
    </UploadContext.Provider>
  );
};
