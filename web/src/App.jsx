import { useEffect, useState } from 'react';
import {
  getHealth,
  getSession,
  getTestRun,
  listSessions,
  listTestRuns,
  sendWebhook,
} from './api.js';

const DEFAULT_SESSION_ID = crypto.randomUUID();
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function formatDate(value) {
  if (!value) {
    return 'Unknown time';
  }
  return new Date(value).toLocaleString();
}

function isUuid(value) {
  return UUID_PATTERN.test(value);
}

function SessionList({ items, selectedId, onSelect, onRefresh, loading }) {
  return (
    <section className="panel panel-list">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Saved Chat</p>
          <h2>Sessions</h2>
        </div>
        <button className="ghost-button" onClick={onRefresh} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      <div className="list-scroll">
        {items.length === 0 ? (
          <p className="empty-state">No saved sessions yet.</p>
        ) : (
          items.map((item) => (
            <button
              key={item.id}
              className={`list-card ${selectedId === item.id ? 'selected' : ''}`}
              onClick={() => onSelect(item.id)}
            >
              <strong>{item.title || item.id}</strong>
              <span>{item.channel}</span>
              <small>{formatDate(item.updated_at)}</small>
            </button>
          ))
        )}
      </div>
    </section>
  );
}

function TestRunList({ items, selectedId, onSelect, onRefresh, loading }) {
  return (
    <section className="panel panel-list">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Saved Tests</p>
          <h2>Runs</h2>
        </div>
        <button className="ghost-button" onClick={onRefresh} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      <div className="list-scroll">
        {items.length === 0 ? (
          <p className="empty-state">No persisted test runs yet.</p>
        ) : (
          items.map((item) => (
            <button
              key={item.id}
              className={`list-card ${selectedId === item.id ? 'selected' : ''}`}
              onClick={() => onSelect(item.id)}
            >
              <strong>{item.suite_name}</strong>
              <span>
                {item.provider} · {item.status}
              </span>
              <small>
                {item.passed_cases}/{item.total_cases} passed
              </small>
            </button>
          ))
        )}
      </div>
    </section>
  );
}

function MessageBubble({ message }) {
  return (
    <article className={`bubble bubble-${message.role}`}>
      <div className="bubble-meta">
        <strong>{message.role === 'assistant' ? 'Assistant' : 'You'}</strong>
        <span>{formatDate(message.created_at)}</span>
      </div>
      <p>{message.content}</p>
      {message.citations?.length > 0 ? (
        <div className="chips">
          {message.citations.map((citation) => (
            <span key={citation} className="chip">
              {citation}
            </span>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function ChunkPanel({ response }) {
  const chunks = response?.chunks || [];
  return (
    <section className="panel detail-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Retrieved Context</p>
          <h2>Chunks</h2>
        </div>
      </div>
      {chunks.length === 0 ? (
        <p className="empty-state">No retrieval chunks to display for the current response.</p>
      ) : (
        <div className="stack">
          {chunks.map((chunk, index) => (
            <article key={`${chunk.scholar}-${index}`} className="detail-card">
              <div className="detail-row">
                <strong>{chunk.source_title || chunk.scholar}</strong>
                <span>{chunk.score}</span>
              </div>
              <small>
                {chunk.scholar} · {chunk.surah_number}:{chunk.ayah_start}
                {chunk.ayah_end && chunk.ayah_end !== chunk.ayah_start ? `-${chunk.ayah_end}` : ''}
              </small>
              <p>{chunk.content_preview}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function SessionDetail({ detail }) {
  return (
    <section className="panel detail-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Session Detail</p>
          <h2>{detail?.session?.title || 'Saved session'}</h2>
        </div>
      </div>
      {!detail ? (
        <p className="empty-state">Choose a saved session to inspect its transcript.</p>
      ) : (
        <div className="stack">
          <div className="detail-card">
            <div className="detail-row">
              <strong>{detail.session.channel}</strong>
              <span>{detail.session.user_id}</span>
            </div>
            <small>Updated {formatDate(detail.session.updated_at)}</small>
          </div>
          {detail.messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </div>
      )}
    </section>
  );
}

function TestRunDetail({ detail }) {
  return (
    <section className="panel detail-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Test Detail</p>
          <h2>{detail?.run?.suite_name || 'Saved run'}</h2>
        </div>
      </div>
      {!detail ? (
        <p className="empty-state">Choose a saved test run to inspect case-by-case output.</p>
      ) : (
        <div className="stack">
          <div className="detail-card">
            <div className="detail-row">
              <strong>{detail.run.provider}</strong>
              <span>{detail.run.status}</span>
            </div>
            <small>
              {detail.run.passed_cases}/{detail.run.total_cases} passed · created{' '}
              {formatDate(detail.run.created_at)}
            </small>
          </div>
          {detail.cases.map((item) => (
            <article key={item.id} className="detail-card">
              <div className="detail-row">
                <strong>{item.query}</strong>
                <span className={`status-pill status-${item.status}`}>{item.status}</span>
              </div>
              <small>
                expected {item.expected}
                {item.actual_intent ? ` · got ${item.actual_intent}` : ''}
              </small>
              {item.reason ? <p>{item.reason}</p> : null}
              {item.response_text ? <p>{item.response_text}</p> : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState('');
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState('');
  const [selectedSession, setSelectedSession] = useState(null);
  const [testRuns, setTestRuns] = useState([]);
  const [testRunsLoading, setTestRunsLoading] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [selectedRun, setSelectedRun] = useState(null);
  const [message, setMessage] = useState('');
  const [sessionId, setSessionId] = useState(DEFAULT_SESSION_ID);
  const [provider, setProvider] = useState('anthropic');
  const [scholar, setScholar] = useState('');
  const [topK, setTopK] = useState(5);
  const [save, setSave] = useState(true);
  const [conversation, setConversation] = useState([]);
  const [currentResponse, setCurrentResponse] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [requestError, setRequestError] = useState('');

  async function loadHealth() {
    try {
      const result = await getHealth();
      setHealth(result);
      setHealthError('');
      if (result.providers?.length && !result.providers.includes(provider)) {
        setProvider(result.providers[0]);
      }
    } catch (error) {
      setHealthError(error.message);
    }
  }

  async function loadSessions() {
    setSessionsLoading(true);
    try {
      const result = await listSessions();
      setSessions(result);
    } finally {
      setSessionsLoading(false);
    }
  }

  async function loadTestRuns() {
    setTestRunsLoading(true);
    try {
      const result = await listTestRuns();
      setTestRuns(result);
    } finally {
      setTestRunsLoading(false);
    }
  }

  useEffect(() => {
    loadHealth();
    loadSessions();
    loadTestRuns();
  }, []);

  useEffect(() => {
    if (!selectedSessionId) {
      setSelectedSession(null);
      return;
    }
    getSession(selectedSessionId)
      .then((result) => setSelectedSession(result))
      .catch(() => setSelectedSession(null));
  }, [selectedSessionId]);

  useEffect(() => {
    if (!selectedRunId) {
      setSelectedRun(null);
      return;
    }
    getTestRun(selectedRunId)
      .then((result) => setSelectedRun(result))
      .catch(() => setSelectedRun(null));
  }, [selectedRunId]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!message.trim()) {
      return;
    }
    if (save && !isUuid(sessionId)) {
      setRequestError('Saved sessions currently require a UUID session ID.');
      return;
    }

    const userTurn = {
      role: 'user',
      content: message.trim(),
      created_at: new Date().toISOString(),
      citations: [],
    };

    const nextConversation = [...conversation, userTurn];
    setConversation(nextConversation);
    setSubmitting(true);
    setRequestError('');

    try {
      const response = await sendWebhook({
        channel: 'web',
        session_id: sessionId,
        user_id: 'local-user',
        message: userTurn.content,
        conversation_history: nextConversation.map((item) => ({
          role: item.role,
          content: item.content,
        })),
        options: {
          provider,
          scholar: scholar || null,
          top_k: Number(topK),
          save,
        },
      });

      const assistantTurn = {
        role: 'assistant',
        content: response.answer,
        created_at: new Date().toISOString(),
        citations: response.citations,
      };
      setConversation((current) => [...current, assistantTurn]);
      setCurrentResponse(response);
      setMessage('');

      if (save) {
        loadSessions();
        setSelectedSessionId(response.session_id);
      }
    } catch (error) {
      setRequestError(error.message);
      setConversation((current) => current.slice(0, -1));
    } finally {
      setSubmitting(false);
    }
  }

  function handleNewSession() {
    const nextId = crypto.randomUUID();
    setSessionId(nextId);
    setConversation([]);
    setCurrentResponse(null);
    setSelectedSessionId('');
    setRequestError('');
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">TafsirBot Local Web PoC</p>
          <h1>Chat, inspect retrieval, and review saved runs from one surface.</h1>
        </div>
        <div className="hero-status">
          <div className={`status-card ${healthError ? 'status-error' : ''}`}>
            <strong>{healthError ? 'API unavailable' : 'API healthy'}</strong>
            <span>
              {healthError ||
                `${health?.providers?.join(', ') || 'No providers'} · persistence ${
                  health?.persistence ? 'on' : 'off'
                }`}
            </span>
          </div>
          <button className="ghost-button" onClick={loadHealth}>
            Refresh Health
          </button>
        </div>
      </header>

      <main className="app-grid">
        <aside className="side-column">
          <SessionList
            items={sessions}
            selectedId={selectedSessionId}
            onSelect={setSelectedSessionId}
            onRefresh={loadSessions}
            loading={sessionsLoading}
          />
          <TestRunList
            items={testRuns}
            selectedId={selectedRunId}
            onSelect={setSelectedRunId}
            onRefresh={loadTestRuns}
            loading={testRunsLoading}
          />
        </aside>

        <section className="panel chat-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Live Query</p>
              <h2>Conversation</h2>
            </div>
            <button className="ghost-button" onClick={handleNewSession}>
              New session
            </button>
          </div>

          <div className="controls">
            <label>
              Session ID
              <input
                value={sessionId}
                onChange={(event) => setSessionId(event.target.value)}
                placeholder="UUID for saved sessions"
              />
            </label>
            <label>
              Provider
              <select value={provider} onChange={(event) => setProvider(event.target.value)}>
                {(health?.providers || ['anthropic', 'openai']).map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Scholar
              <input
                placeholder="ibn_kathir or maududi"
                value={scholar}
                onChange={(event) => setScholar(event.target.value)}
              />
            </label>
            <label>
              Top K
              <input
                type="number"
                min="1"
                max="20"
                value={topK}
                onChange={(event) => setTopK(event.target.value)}
              />
            </label>
            <label className="toggle">
              <input
                type="checkbox"
                checked={save}
                onChange={(event) => setSave(event.target.checked)}
              />
              Save exchange
            </label>
          </div>

          <div className="conversation">
            {conversation.length === 0 ? (
              <p className="empty-state">
                Start a chat to see the live response and retrieval metadata.
              </p>
            ) : (
              conversation.map((item, index) => (
                <MessageBubble key={`${item.role}-${index}`} message={item} />
              ))
            )}
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <textarea
              rows="4"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Ask about a verse, a theme, or a fiqh question."
            />
            <div className="composer-row">
              {requestError ? <p className="error-text">{requestError}</p> : <span />}
              <button className="primary-button" type="submit" disabled={submitting}>
                {submitting ? 'Sending…' : 'Send'}
              </button>
            </div>
          </form>
        </section>

        <aside className="detail-column">
          <ChunkPanel response={currentResponse} />
          <SessionDetail detail={selectedSession} />
          <TestRunDetail detail={selectedRun} />
        </aside>
      </main>
    </div>
  );
}

export default App;
