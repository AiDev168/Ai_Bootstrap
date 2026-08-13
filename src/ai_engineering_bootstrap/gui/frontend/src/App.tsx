import { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';

// Types
interface HealthData {
  service: string;
  status: string;
  llm_available: boolean;
  api_version?: string;
}

interface Session {
  session_id: string;
  status: string;
  created_at: string;
  request?: {
    natural_language_goal?: string;
  };
}

interface ToolStatus {
  tool_id: string;
  status: string;
  version?: string;
}

interface EnvironmentDelta {
  tools: Record<string, ToolStatus>;
}

interface PlanAction {
  action_id: string;
  tool_id: string;
  operation: string;
  strategy?: string;
  risk_level?: string;
  status?: string;
}

interface SessionState {
  session_id: string;
  status: string;
  actual_state?: { tools: Record<string, ToolStatus> };
  desired_state?: { tools: Record<string, ToolStatus> };
  delta?: EnvironmentDelta;
  plan?: PlanAction[];
}

// API Helper
const API_BASE = 'http://localhost:8000/api/v1';

async function fetchAPI<T>(endpoint: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) return null;
    const json = await res.json();
    return json.data || json;
  } catch (e) {
    console.error('API Error:', e);
    return null;
  }
}

async function postAPI<T>(endpoint: string, body?: any): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json.data || json;
  } catch (e) {
    console.error('API Error:', e);
    return null;
  }
}

function App() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [goal, setGoal] = useState('');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<SessionState | null>(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<'dashboard' | 'session'>('dashboard');

  // Load initial data
  useEffect(() => {
    loadHealth();
    loadSessions();
    const interval = setInterval(() => {
      loadHealth();
      if (activeSession) loadSessionState(activeSession.session_id);
      else loadSessions();
    }, 3000);
    return () => clearInterval(interval);
  }, [activeSession]);

  const loadHealth = async () => {
    const data = await fetchAPI<HealthData>('/health');
    if (data) setHealth(data);
  };

  const loadSessions = async () => {
    const data = await fetchAPI<Session[]>('/sessions');
    if (data) setSessions(Array.isArray(data) ? data : []);
  };

  const createSession = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    const result = await postAPI<Session>('/sessions', {
      natural_language_goal: goal,
      project_path: '/tmp/project',
      required_tools: [],
    });
    if (result) {
      setGoal('');
      await loadSessions();
      // Auto-switch to session view
      await loadSessionState(result.session_id);
    }
    setLoading(false);
  };

  const loadSessionState = async (sessionId: string) => {
    const state = await fetchAPI<SessionState>(`/sessions/${sessionId}/state`);
    if (state) {
      setActiveSession(state);
      setView('session');
      // Fetch plan if not present
      if (!state.plan) {
        const plan = await fetchAPI<PlanAction[]>(`/sessions/${sessionId}/plan`);
        if (plan) {
          setActiveSession({ ...state, plan: Array.isArray(plan) ? plan : [] });
        }
      }
    }
  };

  const handleAction = async (actionId: string, actionType: 'approve' | 'reject' | 'skip') => {
    if (!activeSession) return;
    await postAPI(`/sessions/${activeSession.session_id}/actions/${actionId}/${actionType}`);
    // Refresh state
    await loadSessionState(activeSession.session_id);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6 font-sans text-gray-900">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-indigo-700">AI Engineering Bootstrap</h1>
          <p className="text-lg text-gray-600">Environment Orchestrator</p>
        </div>
        <nav className="flex gap-4">
          <button
            onClick={() => setView('dashboard')}
            className={`px-4 py-2 rounded ${view === 'dashboard' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
          >
            Dashboard
          </button>
          {activeSession && (
            <button
              onClick={() => setView('session')}
              className={`px-4 py-2 rounded ${view === 'session' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
            >
              Session: {activeSession.session_id.slice(0, 8)}...
            </button>
          )}
        </nav>
      </header>

      {view === 'dashboard' && (
        <main className="space-y-8">
          {/* System Health */}
          <section className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-4 text-xl font-semibold">System Health</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="rounded bg-gray-50 p-4">
                <p className="text-sm text-gray-500">Service</p>
                <p className={`text-lg font-medium ${health?.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
                  {health?.status || 'unknown'}
                </p>
              </div>
              <div className="rounded bg-gray-50 p-4">
                <p className="text-sm text-gray-500">LLM Available</p>
                <p className={`text-lg font-medium ${health?.llm_available ? 'text-green-600' : 'text-yellow-600'}`}>
                  {health?.llm_available ? 'Yes' : 'No (Fallback Mode)'}
                </p>
              </div>
              <div className="rounded bg-gray-50 p-4">
                <p className="text-sm text-gray-500">API Version</p>
                <p className="text-lg font-medium">{health?.api_version || 'v1'}</p>
              </div>
            </div>
          </section>

          {/* Create Request */}
          <section className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-4 text-xl font-semibold">Create Environment Request</h2>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Describe your environment goal (e.g., 'Prepare this machine for Python AI development with Cursor, Docker, and Ruff')"
              className="mb-4 w-full rounded border border-gray-300 p-3 focus:border-indigo-500 focus:outline-none"
              rows={4}
            />
            <button
              onClick={createSession}
              disabled={loading || !goal.trim()}
              className="w-full rounded bg-indigo-600 py-3 font-medium text-white transition hover:bg-indigo-700 disabled:bg-gray-400"
            >
              {loading ? 'Creating...' : 'Create Session'}
            </button>
          </section>

          {/* Active Sessions */}
          <section className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-4 text-xl font-semibold">Active Sessions</h2>
            {sessions.length === 0 ? (
              <p className="text-gray-500">No active sessions</p>
            ) : (
              <div className="space-y-3">
                {sessions.map((s) => (
                  <div key={s.session_id} className="flex items-center justify-between rounded border p-4">
                    <div>
                      <p className="font-medium">{s.request?.natural_language_goal || 'Environment Setup'}</p>
                      <p className="text-sm text-gray-500">ID: {s.session_id}</p>
                      <p className="text-sm text-gray-500">Status: <span className="font-medium text-indigo-600">{s.status}</span></p>
                    </div>
                    <button
                      onClick={() => loadSessionState(s.session_id)}
                      className="rounded bg-indigo-100 px-4 py-2 text-indigo-700 hover:bg-indigo-200"
                    >
                      View Details
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </main>
      )}

      {view === 'session' && activeSession && (
        <main className="space-y-6">
          <button onClick={() => setView('dashboard')} className="text-indigo-600 hover:underline">← Back to Dashboard</button>
          
          <section className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-4 text-xl font-semibold">Session: {activeSession.session_id}</h2>
            <p className="mb-2"><strong>Status:</strong> {activeSession.status}</p>
            
            {/* Delta View */}
            {activeSession.delta?.tools && Object.keys(activeSession.delta.tools).length > 0 && (
              <div className="mb-6">
                <h3 className="mb-2 font-semibold">Environment Delta</h3>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(activeSession.delta.tools).map(([toolId, tool]) => (
                    <div key={toolId} className="rounded border p-3">
                      <p className="font-medium capitalize">{toolId}</p>
                      <p className="text-sm text-gray-600">Current: <span className={tool.status === 'missing' ? 'text-red-500' : 'text-green-600'}>{tool.status}</span></p>
                      {tool.version && <p className="text-xs text-gray-500">Version: {tool.version}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Plan & Approval */}
            {activeSession.plan && activeSession.plan.length > 0 ? (
              <div>
                <h3 className="mb-2 font-semibold">Execution Plan & Approval</h3>
                <div className="space-y-4">
                  {activeSession.plan.map((action) => (
                    <div key={action.action_id} className="rounded border p-4">
                      <div className="mb-2 flex items-start justify-between">
                        <div>
                          <p className="font-medium capitalize">{action.tool_id}</p>
                          <p className="text-sm text-gray-600">Operation: {action.operation}</p>
                          {action.strategy && <p className="text-xs text-gray-500">Strategy: {action.strategy}</p>}
                          {action.risk_level && <p className="text-xs text-gray-500">Risk: <span className={action.risk_level === 'high' ? 'text-red-500' : 'text-yellow-600'}>{action.risk_level}</span></p>}
                        </div>
                        <span className={`rounded px-2 py-1 text-xs font-medium ${action.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : action.status === 'approved' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                          {action.status || 'pending'}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => handleAction(action.action_id, 'approve')} className="rounded bg-green-600 px-3 py-1 text-sm text-white hover:bg-green-700">Approve</button>
                        <button onClick={() => handleAction(action.action_id, 'reject')} className="rounded bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-700">Reject</button>
                        <button onClick={() => handleAction(action.action_id, 'skip')} className="rounded bg-gray-600 px-3 py-1 text-sm text-white hover:bg-gray-700">Skip</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-gray-500">No actions planned yet or plan loading...</p>
            )}
          </section>
        </main>
      )}
    </div>
  );
}

const root = createRoot(document.getElementById('root')!);
root.render(<App />);
