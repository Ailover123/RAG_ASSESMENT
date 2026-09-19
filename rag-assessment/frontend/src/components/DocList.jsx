import React from 'react';

export default function DocList({ documents = [] }) {
  return (
    <div className="doclist-container">
      <h3>Indexed Documents</h3>
      {documents.length === 0 ? (
        <p>No documents indexed yet.</p>
      ) : (
        <ul>
          {documents.map((doc, index) => (
            <li key={index}>
              {/* TODO: Display document filename, chunk count, and metadata */}
              {doc.name || `Document ${index + 1}`}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
