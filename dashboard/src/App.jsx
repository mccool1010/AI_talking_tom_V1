import { useState, useEffect, useRef, useCallback } from 'react'

// Same origin when served by the backend; the backend port when running `npm run dev`.
const API = import.meta.env.VITE_API_URL ?? (window.location.port === '5173' ? 'http://localhost:8000' : '')
const WS_BASE = (API || window.location.origin).replace(/^http/, 'ws')

const TOKEN_KEY = 'tom_session'
function getToken() {
  try { return sessionStorage.getItem(TOKEN_KEY) } catch { return null }
}
function setToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token)
    else sessionStorage.removeItem(TOKEN_KEY)
  } catch { /* storage unavailable: session lasts until reload */ }
}

class AuthError extends Error {}

async function apiFetch(path, options = {}) {
  const token = getToken()
  const res = await fetch(API + path, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (res.status === 401 || res.status === 409) throw new AuthError()
  return res
}

// ---- WebSocket Hook ----
function useWebSocket(url, onAuthLost) {
  const [data, setData] = useState(null)
  const ws = useRef(null)

  useEffect(() => {
    let stopped = false
    let timer = null
    const connect = () => {
      ws.current = new WebSocket(url)
      ws.current.onmessage = (e) => setData(JSON.parse(e.data))
      ws.current.onclose = (e) => {
        if (stopped) return
        if (e.code === 4401) { onAuthLost(); return }
        timer = setTimeout(connect, 2000)
      }
    }
    connect()
    return () => {
      stopped = true
      clearTimeout(timer)
      ws.current?.close()
    }
  }, [url, onAuthLost])

  return data
}

// ---- Bar Component ----
function Bar({ label, value, max = 100, color = 'bar-blue' }) {
  return (
    <div className="stat-row">
      <div className="stat-label">
        <span>{label}</span>
        <span className="value">{Math.round(value)}</span>
      </div>
      <div className="bar-track">
        <div className={`bar-fill ${color}`} style={{ width: `${(value / max) * 100}%` }} />
      </div>
    </div>
  )
}

function errorText(data) {
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) return data.detail.map(d => d.msg).join('; ')
  return data?.error || 'Request failed'
}

// ---- Login Page ----
function LoginPage({ onLogin }) {
  const [tab, setTab] = useState('login')
  const [userId, setUserId] = useState('')
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const endpoint = tab === 'login' ? '/api/auth/login' : '/api/auth/signup'
      const body = tab === 'login'
        ? { user_id: userId, password }
        : { user_id: userId, user_name: userName, password }

      const res = await fetch(API + endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      const data = await res.json()
      if (!res.ok) { setError(errorText(data)); return }

      if (tab === 'signup') {
        // Auto-login after signup
        const loginRes = await fetch(API + '/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId, password })
        })
        const loginData = await loginRes.json()
        if (loginRes.ok) { setToken(loginData.token); onLogin(loginData) }
        else setError(errorText(loginData))
      } else {
        setToken(data.token)
        onLogin(data)
      }
    } catch { setError('Cannot reach server') }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>🐱 AI Talking Tom</h1>
        <p className="subtitle">Your intelligent companion dashboard</p>
        <div className="auth-tabs">
          <button className={tab === 'login' ? 'active' : ''} onClick={() => setTab('login')}>Login</button>
          <button className={tab === 'signup' ? 'active' : ''} onClick={() => setTab('signup')}>Sign Up</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>User ID</label>
            <input value={userId} onChange={e => setUserId(e.target.value)} required />
          </div>
          {tab === 'signup' && (
            <div className="form-group">
              <label>Display Name</label>
              <input value={userName} onChange={e => setUserName(e.target.value)} required />
            </div>
          )}
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              minLength={tab === 'signup' ? 8 : undefined} required={tab === 'signup'} />
          </div>
          <button className="btn-primary" type="submit">
            {tab === 'login' ? 'Login' : 'Create Account'}
          </button>
        </form>
        {error && <p className="error-msg">{error}</p>}
      </div>
    </div>
  )
}

// ---- Dashboard Page ----
function Dashboard({ user, onLogout }) {
  const token = getToken()
  const live = useWebSocket(`${WS_BASE}/ws/state?token=${encodeURIComponent(token || '')}`, onLogout)
  const [memories, setMemories] = useState({ likes: [], dislikes: [], facts: [] })
  const [conversations, setConversations] = useState([])
  const [personality, setPersonality] = useState(null)
  const [emotions, setEmotions] = useState([])

  useEffect(() => {
    const load = async () => {
      try {
        const [memRes, convRes, stateRes] = await Promise.all([
          apiFetch('/api/memories'),
          apiFetch('/api/conversations'),
          apiFetch('/api/state')
        ])
        setMemories(await memRes.json())
        const convData = await convRes.json()
        setConversations(convData.messages || [])
        const stateData = await stateRes.json()
        setPersonality(stateData.personality)
        setEmotions(stateData.recent_emotions || [])
      } catch (err) {
        if (err instanceof AuthError) onLogout()
      }
    }
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [onLogout])

  const handleLogout = async () => {
    try { await apiFetch('/api/auth/logout', { method: 'POST' }) } catch { /* already logged out */ }
    onLogout()
  }

  const state = live?.state || { energy: 0, friendliness: 0, curiosity: 0 }
  const needs = live?.needs || { hunger: 0, sleepiness: 0, social_need: 0 }
  const rel = live?.relationship || { trust: 0, friendship: 0, attachment: 0 }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>🐱 Tom Dashboard</h1>
        <div className="user-info">
          <span className="user-name">Logged in as <strong>{user.user_name}</strong></span>
          <button className="btn-logout" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <div className="grid">
        {/* State */}
        <div className="card">
          <div className="card-title"><span className="icon">⚡</span> State</div>
          <Bar label="Energy" value={state.energy} color="bar-green" />
          <Bar label="Friendliness" value={state.friendliness} color="bar-blue" />
          <Bar label="Curiosity" value={state.curiosity} color="bar-purple" />
        </div>

        {/* Needs */}
        <div className="card">
          <div className="card-title"><span className="icon">🍽️</span> Needs</div>
          <Bar label="Hunger" value={needs.hunger} color="bar-amber" />
          <Bar label="Sleepiness" value={needs.sleepiness} color="bar-purple" />
          <Bar label="Social Need" value={needs.social_need} color="bar-pink" />
        </div>

        {/* Relationship */}
        <div className="card">
          <div className="card-title"><span className="icon">💛</span> Relationship</div>
          <Bar label="Trust" value={rel.trust} color="bar-blue" />
          <Bar label="Friendship" value={rel.friendship} color="bar-green" />
          <Bar label="Attachment" value={rel.attachment} color="bar-purple" />
        </div>

        {/* Personality */}
        <div className="card">
          <div className="card-title"><span className="icon">🧠</span> Personality</div>
          {personality ? (
            <div className="trait-grid">
              {Object.entries(personality).map(([k, v]) => (
                <div className="trait-item" key={k}>
                  <div className="trait-value">{Number(v).toFixed(1)}</div>
                  <div className="trait-name">{k.replace('_', ' ')}</div>
                </div>
              ))}
            </div>
          ) : <p className="no-data">Loading...</p>}
        </div>

        {/* Emotions */}
        <div className="card">
          <div className="card-title"><span className="icon">😊</span> Recent Emotions</div>
          {emotions.length > 0 ? (
            <div className="emotion-list">
              {emotions.map((em, i) => {
                const emotion = typeof em === 'string' ? em : (em.emotion || em.dominant || 'neutral')
                return <span key={i} className={`emotion-badge ${emotion}`}>{emotion}</span>
              })}
            </div>
          ) : <p className="no-data">No emotions recorded yet</p>}
        </div>

        {/* Camera */}
        <div className="card">
          <div className="card-title"><span className="icon">📷</span> Camera Feed</div>
          <div className="camera-feed">
            <img src={`${API}/api/camera?token=${encodeURIComponent(token || '')}`} alt="Live camera" />
          </div>
        </div>

        {/* Memories */}
        <div className="card">
          <div className="card-title"><span className="icon">📝</span> Memories</div>
          <div className="memory-section">
            <h4>Likes</h4>
            {memories.likes?.length > 0
              ? memories.likes.map((m, i) => <span key={i} className="memory-tag like">{m.value || m}</span>)
              : <p className="no-data">None yet</p>}
          </div>
          <div className="memory-section">
            <h4>Dislikes</h4>
            {memories.dislikes?.length > 0
              ? memories.dislikes.map((m, i) => <span key={i} className="memory-tag dislike">{m.value || m}</span>)
              : <p className="no-data">None yet</p>}
          </div>
          <div className="memory-section">
            <h4>Facts</h4>
            {memories.facts?.length > 0
              ? memories.facts.map((m, i) => <span key={i} className="memory-tag fact">{m.value || m}</span>)
              : <p className="no-data">None yet</p>}
          </div>
        </div>

        {/* Conversation Log */}
        <div className="card">
          <div className="card-title"><span className="icon">💬</span> Conversation Log</div>
          <div className="chat-log">
            {conversations.length > 0 ? conversations.map((msg, i) => (
              <div key={i} className={`chat-msg ${msg.role}`}>
                <div className="role">{msg.role}</div>
                <div>{msg.content}</div>
              </div>
            )) : <p className="no-data">No conversations yet</p>}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---- App (Router) ----
export default function App() {
  const [user, setUser] = useState(null)

  // Check if already logged in on mount
  const handleLogout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    if (!getToken()) return
    apiFetch('/api/auth/status')
      .then(r => r.json())
      .then(d => { if (d.logged_in) setUser(d); else setToken(null) })
      .catch(() => setToken(null))
  }, [])

  if (!user) return <LoginPage onLogin={setUser} />
  return <Dashboard user={user} onLogout={handleLogout} />
}
