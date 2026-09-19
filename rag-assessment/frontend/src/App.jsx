import { Fragment, cloneElement, isValidElement, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import mermaid from 'mermaid';
import './App.css';

const API_BASE = "";

mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
  theme: 'base',
  themeVariables: {
    primaryColor: '#e8f5f3',
    primaryTextColor: '#255966',
    primaryBorderColor: '#75b9b0',
    lineColor: '#6d9293',
    secondaryColor: '#f7fbfa',
    tertiaryColor: '#ffffff',
  },
});

// Matches numeric/source brackets [1], [1, 2], [Source: ...], and unicode brackets 【...】
const CITATION_REGEX = /(\[\s*\d+(?:\s*[,\-–]\s*\d+)*\s*\]|\[\s*(?:Source|Retrieved from|Doc|Page|Slide|Ref)[^\]]+\]|\[\s*[^\]]+\.(?:pdf|docx|pptx|txt)[^\]]*\]|【[^】]+】|〔[^〕]+〕)/gi;

function renderWithCitations(node) {
  if (typeof node === 'string') {
    const parts = node.split(CITATION_REGEX);
    if (parts.length === 1) return node;
    return parts.map((part, index) => {
      if (!part) return null;
      if (
        (/^\[.+\]$/.test(part) || /^【.+】$/.test(part) || /^〔.+〕$/.test(part)) &&
        (/^\s*\[\s*\d+(?:\s*[,\-–]\s*\d+)*\s*\]\s*$/.test(part) ||
          /^\s*\[\s*(?:Source|Retrieved from|Doc|Page|Slide|Ref)/i.test(part) ||
          /^\s*\[\s*[^\]]+\.(?:pdf|docx|pptx|txt)/i.test(part) ||
          /^[【〔]/.test(part))
      ) {
        return (
          <span key={index} className="inline-citation" title="Source reference">
            {part}
          </span>
        );
      }
      return part;
    });
  }

  if (Array.isArray(node)) {
    return node.map((child, index) => (
      <Fragment key={index}>{renderWithCitations(child)}</Fragment>
    ));
  }

  if (isValidElement(node)) {
    if (node.type === 'code' || node.type === 'pre') {
      return node;
    }
    if (node.props && node.props.children) {
      return cloneElement(node, {
        children: renderWithCitations(node.props.children),
      });
    }
  }

  return node;
}

function MermaidDiagram({ source, isStreaming }) {
  const diagramRef = useRef(null);
  const diagramId = useRef(`rag-diagram-${Math.random().toString(36).slice(2)}`);

  useEffect(() => {
    if (isStreaming || !diagramRef.current || !source.trim()) return undefined;

    let isCurrent = true;
    mermaid
      .render(diagramId.current, source)
      .then(({ svg }) => {
        if (isCurrent && diagramRef.current) diagramRef.current.innerHTML = svg;
      })
      .catch(() => {
        if (isCurrent && diagramRef.current) {
          diagramRef.current.textContent = source;
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [source, isStreaming]);

  if (isStreaming) {
    return (
      <pre className="diagram-fallback">
        <code>{source}</code>
      </pre>
    );
  }

  return <div className="mermaid-diagram" ref={diagramRef} aria-label="Generated flowchart" />;
}

// Normalize common inline table output before Markdown parses it.
function formatMarkdown(rawText) {
  if (!rawText) return '';
  let formatted = rawText;

  // Some model responses use "| |" or "||" as row breaks while streaming.
  // Only apply this when a Markdown separator row is present, so normal prose
  // containing pipe characters is left untouched.
  const hasTableSeparator = /\|\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?/.test(formatted);
  if (hasTableSeparator) {
    formatted = formatted.replace(/\s*\|\s*\|\s*/g, '\n');
  }

  return formatted
    // Ensure blank line before table start if glued to previous text
    .replace(/([^\n])\n?(\|[^\n]+\|\n\|(?:\s*:?---+:?\s*\|)+)/g, '$1\n\n$2')
    // Ensure blank line after table if glued to trailing text
    .replace(/(\|(?:\s*:?---+:?\s*\|)+(?:\n\|[^\n]+\|)+)\n?([^\n|])/g, '$1\n\n$2');
}

function AnswerContent({ answer, isStreaming }) {
  const formattedAnswer = formatMarkdown(answer);

  return (
    <div className="answer-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p>{renderWithCitations(children)}</p>,
          li: ({ children }) => <li>{renderWithCitations(children)}</li>,
          td: ({ children }) => <td>{renderWithCitations(children)}</td>,
          th: ({ children }) => <th>{renderWithCitations(children)}</th>,
          h1: ({ children }) => <h1>{renderWithCitations(children)}</h1>,
          h2: ({ children }) => <h2>{renderWithCitations(children)}</h2>,
          h3: ({ children }) => <h3>{renderWithCitations(children)}</h3>,
          h4: ({ children }) => <h4>{renderWithCitations(children)}</h4>,
          blockquote: ({ children }) => <blockquote>{renderWithCitations(children)}</blockquote>,
          table: ({ children }) => (
            <div className="table-scroll">
              <table>{children}</table>
            </div>
          ),
          code: ({ className, children, inline }) => {
            const language = className?.replace('language-', '');
            const source = String(children).replace(/\n$/, '');
            if (!inline && language === 'mermaid') {
              return <MermaidDiagram source={source} isStreaming={isStreaming} />;
            }
            return inline ? (
              <code className="inline-code">{children}</code>
            ) : (
              <pre className="code-block">
                <code>{children}</code>
              </pre>
            );
          },
        }}
      >
        {formattedAnswer}
      </ReactMarkdown>
    </div>
  );
}

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [question, setQuestion] = useState('');
  const [conversation, setConversation] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE}/documents`);
      if (!response.ok) {
        throw new Error('Unable to load documents.');
      }
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (error) {
      setUploadStatus(error.message);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleUpload = async (event) => {
    event.preventDefault();
    if (!selectedFile || isUploading) return;

    setIsUploading(true);
    setUploadStatus('Uploading...');
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed.');
      }

      setUploadStatus(`✓ Uploaded: ${data.filename} (${data.chunks_added} chunks)`);
      setSelectedFile(null);
      event.target.reset();
      await fetchDocuments();
    } catch (error) {
      setUploadStatus(error.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleAsk = async (event) => {
    event.preventDefault();
    const cleanQuestion = question.trim();
    if (!cleanQuestion || isStreaming) return;

    const conversationIndex = conversation.length;
    setConversation((currentConversation) => [
      ...currentConversation,
      { question: cleanQuestion, answer: '', model: '', citations: [] },
    ]);
    setQuestion('');
    setIsStreaming(true);

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: cleanQuestion, top_k: 5 }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Query failed.');
      }
      if (!response.body) throw new Error('The query returned no response stream.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const applyStreamMessage = (message) => {
        const payload = message
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => (line.startsWith('data: ') ? line.slice(6) : line.slice(5)))
          .join('\n');

        if (!payload) return;

        try {
          const eventData = JSON.parse(payload);
          if (eventData?.type === 'metadata') {
            setConversation((currentConversation) =>
              currentConversation.map((entry, index) =>
                index === conversationIndex
                  ? { ...entry, model: eventData.model || '', citations: eventData.citations || [] }
                  : entry
              )
            );
            return;
          }
          if (eventData?.type === 'token' && typeof eventData.token === 'string') {
            setConversation((currentConversation) =>
              currentConversation.map((entry, index) =>
                index === conversationIndex
                  ? { ...entry, answer: entry.answer + eventData.token }
                  : entry
              )
            );
            return;
          }
        } catch {
          // Support plain-text SSE responses from older backend versions.
        }

        setConversation((currentConversation) =>
          currentConversation.map((entry, index) =>
            index === conversationIndex
              ? { ...entry, answer: entry.answer + payload }
              : entry
          )
        );
      };

      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        buffer = buffer.replace(/\r\n/g, '\n');

        const messages = buffer.split('\n\n');
        buffer = messages.pop() || '';

        messages.forEach((message) => {
          if (message.trim()) applyStreamMessage(message);
        });

        if (done) {
          buffer += decoder.decode();
          break;
        }
      }

      if (buffer.trim()) applyStreamMessage(buffer);
    } catch (error) {
      setConversation((currentConversation) =>
        currentConversation.map((entry, index) =>
          index === conversationIndex
            ? { ...entry, answer: `Error: ${error.message}` }
            : entry
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="page-header">
        <p className="eyebrow">DOCUMENT INTELLIGENCE</p>
        <h1>Ask your documents.</h1>
        <p className="intro">Upload a file, then get clear answers grounded in its contents.</p>
      </header>

      <main className="content">
        {/* 01: Upload section */}
        <section className="section-panel" aria-labelledby="upload-heading">
          <div className="section-heading">
            <span className="section-number">01</span>
            <div>
              <h2 id="upload-heading">Upload documents</h2>
              <p>PDF, DOCX, and PPTX files are supported.</p>
            </div>
          </div>
          <form className="upload-form" onSubmit={handleUpload}>
            <input
              type="file"
              accept=".pdf,.docx,.pptx"
              onChange={(event) => setSelectedFile(event.target.files[0] || null)}
            />
            <button type="submit" disabled={!selectedFile || isUploading}>
              {isUploading ? 'Uploading...' : 'Upload'}
            </button>
          </form>
          {uploadStatus && <p className="status-message">{uploadStatus}</p>}
        </section>

        {/* 02: Documents list section */}
        <section className="section-panel" aria-labelledby="documents-heading">
          <div className="section-heading">
            <span className="section-number">02</span>
            <div>
              <h2 id="documents-heading">Your documents</h2>
              <p>Files currently available to the assistant.</p>
            </div>
          </div>
          {documents.length > 0 ? (
            <ul className="document-list">
              {documents.map((document) => (
                <li key={document}>{document}</li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">No documents uploaded yet</p>
          )}
        </section>

        {/* 03: Chat section */}
        <section className="section-panel chat-panel" aria-labelledby="chat-heading">
          <div className="section-heading">
            <span className="section-number">03</span>
            <div>
              <h2 id="chat-heading">Ask a question</h2>
              <p>The answer will stream in as it is generated.</p>
            </div>
          </div>
          <form className="question-form" onSubmit={handleAsk}>
            <input
              type="text"
              value={question}
              placeholder="What would you like to know?"
              onChange={(event) => setQuestion(event.target.value)}
              aria-label="Question"
            />
            <button type="submit" disabled={!question.trim() || isStreaming}>
              {isStreaming ? 'Answering...' : 'Ask'}
            </button>
          </form>

          {conversation.length > 0 && (
            <div className="conversation" aria-live="polite">
              {conversation.map((entry, index) => {
                // Deduplicate source citations by file and page
                const uniqueCitations = (entry.citations || []).filter(
                  (citation, citationIdx, arr) =>
                    citationIdx ===
                    arr.findIndex(
                      (c) =>
                        c.source === citation.source &&
                        String(c.page || '') === String(citation.page || '')
                    )
                );

                return (
                  <article className="chat-exchange" key={`${entry.question}-${index}`}>
                    <div className="question-bubble">
                      <span className="message-label">You</span>
                      <p>{entry.question}</p>
                    </div>

                    <div className="answer-box">
                      <div className="answer-header">
                        <span className="message-label">Assistant</span>
                        {entry.model && <span className="model-label">{entry.model}</span>}
                      </div>

                      {/* Visual Block A: Retrieved context summary */}
                      {uniqueCitations.length > 0 && (
                        <div className="sources-summary-block">
                          <span className="sources-summary-label">Sources</span>
                          <div className="sources-list">
                            {uniqueCitations.map((citation, citationIndex) => (
                              <span
                                className="source-tag"
                                key={`${citation.source}-${citation.page}-${citationIndex}`}
                              >
                                {citation.source}
                                {citation.page ? ` (p. ${citation.page})` : ''}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Visual Block B: LLM answer text (with styled inline citations) */}
                      <div className="llm-answer-block">
                        {entry.answer ? (
                          <AnswerContent
                            answer={entry.answer}
                            isStreaming={index === conversation.length - 1 && isStreaming}
                          />
                        ) : (
                          <p className="thinking-indicator">
                            {index === conversation.length - 1 && isStreaming ? 'Thinking...' : ''}
                          </p>
                        )}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
