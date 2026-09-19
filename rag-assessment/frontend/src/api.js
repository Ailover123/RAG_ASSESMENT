const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Upload one or more document files to the backend.
 * @param {FileList|File[]} files
 * @returns {Promise<any>}
 */
export async function uploadFiles(files) {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed with status: ${response.status}`);
  }

  return response.json();
}

/**
 * Query the RAG backend with a question.
 * @param {string} query
 * @param {number} topK
 * @param {boolean} stream
 * @returns {Promise<any>}
 */
export async function queryRAG(query, topK = 4, stream = false) {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query, top_k: topK, stream }),
  });

  if (!response.ok) {
    throw new Error(`Query failed with status: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch the list of indexed documents.
 * @returns {Promise<any>}
 */
export async function getDocuments() {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Fetching documents failed with status: ${response.status}`);
  }

  return response.json();
}
