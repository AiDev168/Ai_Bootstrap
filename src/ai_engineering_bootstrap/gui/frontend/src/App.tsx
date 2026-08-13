import { useState, useEffect } from 'react'

interface HealthStatus {
  service: string
  status: string
  llm_available: boolean
}

interface Session {
  session_id: string
  status: string
  request: {
    natural_language_goal: string
    required_tools: string[]
  }
  delta?: {
    tool_deltas: Array<{ tool_id: string; action: string }>
  }
  plan?: {
    actions: Array<{
      action_id: string
      tool_id: string
      operation: string
      strategy: string
      risk_level: string
    }>
  }
  events?: Array<{
    event_type: string
    timestamp: string
    details: string
  }>
}

const API_BASE = 'http://localhost:8000/api/v1'

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [goal, setGoal] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedSession, setSelectedSession] = useState<Session | null>(null)
  const [activeTab, setActiveTab] = useState<'dashboard' | 'session'>('dashboard')

  useEffect(() => {
    fetchHealth()
    fetchSessions()
    const interval = setInterval(fetchSessions, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`)
      const data = await res.json()
      if (data.status === 'ok') {
        setHealth(data.data)
      }
    } catch (err) {
      console.error('Failed to fetch health:', err)
    }
  }

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`)
      const data = await res.json()
      if (data.status === 'ok') {
        setSessions(data.data.sessions || [])
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err)
    }
  }

  const createSession = async () => {
    if (!goal.trim()) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: '/tmp/my-project',
          natural_language_goal: goal,
          required_tools: [],
          optional_tools: [],
          project_dependencies: [],
          constraints: {},
        }),
      })
      const data = await res.json()
      if (data.status === 'ok') {
        setGoal('')
        await fetchSessions()
      }
    } catch (err) {
      console.error('Failed to create session:', err)
    } finally {
      setLoading(false)
    }
  }

  const viewSession = async (sessionId: string) => {
    try {
      const [stateRes, planRes, eventsRes] = await Promise.all([
        fetch(`${API_BASE}/sessions/${sessionId}/state`),
        fetch(`${API_BASE}/sessions/${sessionId}/plan`),
        fetch(`${API_BASE}/sessions/${sessionId}/events`),
      ])
      
      const stateData = await stateRes.json()
      const planData = await planRes.json()
      const eventsData = await eventsRes.json()
      
      const session = sessions.find(s => s.session_id === sessionId)
      if (session) {
        setSelectedSession({
          ...session,
          delta: stateData.status === 'ok' ? stateData.data : undefined,
          plan: planData.status === 'ok' ? planData.data : undefined,
          events: eventsData.status === 'ok' ? eventsData.data.events : undefined,
        })
        setActiveTab('session')
      }
    } catch (err) {
      console.error('Failed to load session:', err)
    }
  }

  const handleAction = async (sessionId: string, actionId: string, action: 'approve' | 'reject' | 'skip') => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/actions/${actionId}/${action}`, {
        method: 'POST',
      })
      const data = await res.json()
      if (data.status === 'ok') {
        viewSession(sessionId)
      }
    } catch (err) {
      console.error(`Failed to ${action} action:`, err)
    }
  }

  const startSession = async (sessionId: string) => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/start`, {
        method: 'POST',
      })
      const data = await res.json()
      if (data.status === 'ok') {
        viewSession(sessionId)
      }
    } catch (err) {
      console.error('Failed to start session:', err)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold text-blue-400">AI Engineering Bootstrap</h1>
          <p className="text-gray-400 mt-2">Environment Orchestrator</p>
        </div>
        <nav className="flex gap-4">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-4 py-2 rounded ${activeTab === 'dashboard' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
          >
            Dashboard
          </button>
          {selectedSession && (
            <button
              onClick={() => setActiveTab('session')}
              className={`px-4 py-2 rounded ${activeTab === 'session' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
            >
              Session Details
            </button>
          )}
        </nav>
      </header>

      {activeTab === 'dashboard' && (
        <>
          {/* Health Status */}
          <section className="mb-8 bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">System Health</h2>
            {health ? (
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-700 p-4 rounded">
                  <div className="text-gray-400 text-sm">Service</div>
                  <div className={`font-semibold ${health.status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
                    {health.status}
                  </div>
                </div>
                <div className="bg-gray-700 p-4 rounded">
                  <div className="text-gray-400 text-sm">LLM Available</div>
                  <div className={`font-semibold ${health.llm_available ? 'text-green-400' : 'text-yellow-400'}`}>
                    {health.llm_available ? 'Yes' : 'No'}
                  </div>
                </div>
                <div className="bg-gray-700 p-4 rounded">
                  <div className="text-gray-400 text-sm">API Version</div>
                  <div className="font-semibold">{health.service}</div>
                </div>
              </div>
            ) : (
              <div className="text-gray-400">Loading...</div>
            )}
          </section>

          {/* Create Session */}
          <section className="mb-8 bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Create Environment Request</h2>
            <textarea
              className="w-full bg-gray-700 text-white p-4 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
              placeholder="Describe your environment goal (e.g., 'Prepare this machine for Python AI development with Cursor, Docker, and Ruff')"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
            />
            <button
              onClick={createSession}
              disabled={loading || !goal.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-6 py-2 rounded-lg transition-colors"
            >
              {loading ? 'Creating...' : 'Create Session'}
            </button>
          </section>

          {/* Sessions List */}
          <section className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Active Sessions</h2>
            {sessions.length > 0 ? (
              <div className="space-y-4">
                {sessions.map((session) => (
                  <div key={session.session_id} className="bg-gray-700 p-4 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors" onClick={() => viewSession(session.session_id)}>
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-mono text-sm text-blue-400">{session.session_id.slice(0, 8)}...</span>
                      <span className={`px-3 py-1 rounded-full text-xs ${
                        session.status === 'CREATED' ? 'bg-blue-600' :
                        session.status === 'EXECUTING' ? 'bg-yellow-600' :
                        session.status === 'COMPLETED' ? 'bg-green-600' :
                        'bg-gray-600'
                      }`}>
                        {session.status}
                      </span>
                    </div>
                    <p className="text-gray-300 text-sm mb-2">{session.request.natural_language_goal}</p>
                    <div className="flex flex-wrap gap-2">
                      {session.request.required_tools.map((tool) => (
                        <span key={tool} className="bg-gray-600 px-2 py-1 rounded text-xs">
                          {tool}
                        </span>
                      ))}
                    </div>
                    <button className="mt-3 bg-blue-600 hover:bg-blue-700 text-white px-4 py-1 rounded text-sm">
                      View Details
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400">No active sessions</div>
            )}
          </section>
        </>
      )}

      {activeTab === 'session' && selectedSession && (
        <div className="space-y-6">
          <button onClick={() => setActiveTab('dashboard')} className="text-blue-400 hover:text-blue-300">← Back to Dashboard</button>
          
          <section className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Session {selectedSession.session_id.slice(0, 8)}...</h2>
            <div className="mb-4">
              <span className="text-gray-400">Status:</span>{' '}
              <span className={`px-3 py-1 rounded-full text-xs ${
                selectedSession.status === 'CREATED' ? 'bg-blue-600' :
                selectedSession.status === 'EXECUTING' ? 'bg-yellow-600' :
                selectedSession.status === 'COMPLETED' ? 'bg-green-600' :
                'bg-gray-600'
              }`}>
                {selectedSession.status}
              </span>
            </div>
            <p className="text-gray-300 mb-4">{selectedSession.request.natural_language_goal}</p>
            
            {selectedSession.status === 'CREATED' && (
              <button onClick={() => startSession(selectedSession.session_id)} className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg">
                Start Execution
              </button>
            )}
          </section>

          {selectedSession.delta && selectedSession.delta.tool_deltas && selectedSession.delta.tool_deltas.length > 0 && (
            <section className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Environment Delta</h2>
              <div className="space-y-2">
                {selectedSession.delta.tool_deltas.map((delta, idx) => (
                  <div key={idx} className="bg-gray-700 p-3 rounded flex justify-between">
                    <span className="font-semibold">{delta.tool_id}</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      delta.action === 'INSTALL' ? 'bg-red-600' :
                      delta.action === 'UPGRADE' ? 'bg-yellow-600' :
                      'bg-green-600'
                    }`}>
                      {delta.action}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {selectedSession.plan && selectedSession.plan.actions && selectedSession.plan.actions.length > 0 && (
            <section className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Execution Plan</h2>
              <div className="space-y-4">
                {selectedSession.plan.actions.map((action) => (
                  <div key={action.action_id} className="bg-gray-700 p-4 rounded">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-semibold text-lg">{action.tool_id}</h3>
                        <p className="text-gray-400 text-sm">{action.operation}</p>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs ${
                        action.risk_level === 'LOW' ? 'bg-green-600' :
                        action.risk_level === 'MEDIUM' ? 'bg-yellow-600' :
                        'bg-red-600'
                      }`}>
                        {action.risk_level} RISK
                      </span>
                    </div>
                    <p className="text-gray-400 text-sm mb-3">Strategy: {action.strategy}</p>
                    <div className="flex gap-2">
                      <button onClick={() => handleAction(selectedSession.session_id, action.action_id, 'approve')} className="bg-green-600 hover:bg-green-700 text-white px-4 py-1 rounded text-sm">
                        Approve
                      </button>
                      <button onClick={() => handleAction(selectedSession.session_id, action.action_id, 'skip')} className="bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-1 rounded text-sm">
                        Skip
                      </button>
                      <button onClick={() => handleAction(selectedSession.session_id, action.action_id, 'reject')} className="bg-red-600 hover:bg-red-700 text-white px-4 py-1 rounded text-sm">
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {selectedSession.events && selectedSession.events.length > 0 && (
            <section className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Execution Timeline</h2>
              <div className="space-y-2">
                {selectedSession.events.map((event, idx) => (
                  <div key={idx} className="bg-gray-700 p-3 rounded flex justify-between">
                    <span className="text-blue-400 font-mono text-sm">{event.event_type}</span>
                    <span className="text-gray-400 text-sm">{event.details}</span>
                    <span className="text-gray-500 text-xs">{new Date(event.timestamp).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
