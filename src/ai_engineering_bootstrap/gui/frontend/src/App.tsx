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
}

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [goal, setGoal] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchHealth()
    fetchSessions()
  }, [])

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/v1/health')
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
      const res = await fetch('/api/v1/sessions')
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
      const res = await fetch('/api/v1/sessions', {
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
        fetchSessions()
      }
    } catch (err) {
      console.error('Failed to create session:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <header className="mb-8">
        <h1 className="text-4xl font-bold text-blue-400">AI Engineering Bootstrap</h1>
        <p className="text-gray-400 mt-2">Environment Orchestrator</p>
      </header>

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
              <div key={session.session_id} className="bg-gray-700 p-4 rounded-lg">
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
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-400">No active sessions</div>
        )}
      </section>
    </div>
  )
}
