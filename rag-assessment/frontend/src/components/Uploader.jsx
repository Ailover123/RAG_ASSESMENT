import React, { useState } from 'react';

export default function Uploader({ onUploadComplete }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (e) => {
    setSelectedFiles(Array.from(e.target.files));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    try {
      // TODO: Call uploadFiles(selectedFiles) from api.js
      if (onUploadComplete) onUploadComplete();
    } catch (err) {
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="uploader-container">
      <h3>Upload Documents</h3>
      <input
        type="file"
        multiple
        accept=".pdf,.docx,.pptx"
        onChange={handleFileChange}
      />
      <button onClick={handleUpload} disabled={uploading || selectedFiles.length === 0}>
        {uploading ? 'Uploading...' : 'Upload'}
      </button>
    </div>
  );
}
