import { useState } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function EvidenceCard({ item }) {
  return (
    <div className="evidence-card">
      <div className="evidence-header">
        <span className={`badge badge-${item.source_type}`}>{item.source_type}</span>
        <span className="evidence-source">{item.source}</span>
        <span className="evidence-confidence">{Math.round(item.confidence * 100)}%</span>
      </div>
      <p className="evidence-content">{item.content}</p>
    </div>
  )
}

function TurnCard({ turn }) {
  return (
    <div className="turn-card">
      <div className="turn-query">
        <span className="turn-label">Merchant</span>
        <p>{turn.query}</p>
      </div>

      {turn.error && <div className="error-box">{turn.error}</div>}

      {turn.response && (
        <div className="turn-response">
          <div className="turn-meta">
            <span className="badge badge-route">{turn.response.route}</span>
            <span className={`badge badge-status-${turn.response.status}`}>
              {turn.response.status}
            </span>
          </div>

          <div className="turn-answer">
            <span className="turn-label">Assistant</span>
            <p>{turn.response.final_answer}</p>
          </div>

          {turn.response.evidence?.length > 0 && (
            <details className="evidence-details">
              <summary>Evidence ({turn.response.evidence.length})</summary>
              <div className="evidence-list">
                {turn.response.evidence.map((item, idx) => (
                  <EvidenceCard key={idx} item={item} />
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

function App() {
  const [merchantId, setMerchantId] = useState('M123')
  const [language, setLanguage] = useState('en')
  const [sessionId, setSessionId] = useState('S001')
  const [query, setQuery] = useState('')
  const [turns, setTurns] = useState([])
  const [loading, setLoading] = useState(false)

  const submitQuery = async (e) => {
    e.preventDefault()
    const trimmed = query.trim()
    if (!trimmed || loading) return

    setLoading(true)
    const pendingTurn = { query: trimmed, response: null, error: null }
    setTurns((prev) => [...prev, pendingTurn])
    setQuery('')

    try {
      const res = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          merchant_id: merchantId,
          language,
          query: trimmed,
          session_id: sessionId || null,
        }),
      })

      if (!res.ok) {
        const detail = await res.text()
        throw new Error(`Request failed (${res.status}): ${detail}`)
      }

      const data = await res.json()
      setTurns((prev) =>
        prev.map((t) => (t === pendingTurn ? { ...t, response: data } : t))
      )
    } catch (err) {
      setTurns((prev) =>
        prev.map((t) => (t === pendingTurn ? { ...t, error: err.message } : t))
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Market Merchant Support Assistant</h1>
        <p>Ask a merchant support question and see how the agent pipeline routes and answers it.</p>
      </header>

      <div className="context-bar">
        <label>
          Merchant ID
          <input value={merchantId} onChange={(e) => setMerchantId(e.target.value)} />
        </label>
        <label>
          Language
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="en">en</option>
            <option value="jp">jp</option>
          </select>
        </label>
        <label>
          Session ID
          <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
        </label>
      </div>

      <main className="conversation">
        {turns.length === 0 && (
          <div className="empty-state">
            Try: "Why is my product not visible in Japanese search results?"
          </div>
        )}
        {turns.map((turn, idx) => (
          <TurnCard key={idx} turn={turn} />
        ))}
        {loading && <div className="loading-indicator">Thinking…</div>}
      </main>

      <form className="query-form" onSubmit={submitQuery}>
        <textarea
          placeholder="Describe the merchant's issue…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submitQuery(e)
            }
          }}
          rows={2}
        />
        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? 'Sending…' : 'Send'}
        </button>
      </form>
    </div>
  )
}

export default App
