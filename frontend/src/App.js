import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import "./App.css";

const API = "http://localhost:8000";

const AGENTS = [
  { id: "transcriber", label: "Transcriber Agent", emoji: "🎤", desc: "Converting speech to text" },
  { id: "analyzer",    label: "Analyzer Agent",    emoji: "🧠", desc: "Extracting action items" },
  { id: "action_taker",label: "Action Agent",      emoji: "⚡", desc: "Slack + Calendar update" },
];

export default function App() {
  const [agentStatus, setAgentStatus]     = useState({});
  const [result, setResult]               = useState(null);
  const [logs, setLogs]                   = useState([]);
  const [loading, setLoading]             = useState(false);
  const [mode, setMode]                   = useState("upload");   // upload | zoom
  const [tab, setTab]                     = useState("process");  // process | history
  const [history, setHistory]             = useState([]);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [historyLoading, setHistoryLoading]   = useState(false);
  const [error, setError]                 = useState(null);
  const [wsStatus, setWsStatus]           = useState("connecting");
  const wsRef        = useRef(null);
  const fileRef      = useRef(null);
  const logsEndRef   = useRef(null);

  // ── WebSocket ──────────────────────────────────────────────────────────────
  const connectWS = useCallback(() => {
    const ws = new WebSocket("ws://localhost:8000/ws");
    ws.onopen  = () => setWsStatus("connected");
    ws.onclose = () => { setWsStatus("disconnected"); setTimeout(connectWS, 3000); };
    ws.onerror = () => setWsStatus("error");
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setAgentStatus((prev) => ({ ...prev, [data.step]: data.status }));
      setLogs((prev) => [...prev, { time: new Date().toLocaleTimeString(), msg: data.message }]);
    };
    wsRef.current = ws;
  }, []);

  useEffect(() => { connectWS(); return () => wsRef.current?.close(); }, [connectWS]);
  useEffect(() => { logsEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);
  useEffect(() => { if (tab === "history") fetchHistory(); }, [tab]);

  // ── History ────────────────────────────────────────────────────────────────
  async function fetchHistory() {
    setHistoryLoading(true);
    try {
      const res = await axios.get(`${API}/meetings`);
      setHistory(res.data);
    } catch (e) {
      setError("Could not load meeting history.");
    }
    setHistoryLoading(false);
  }

  async function fetchMeetingDetail(id) {
    try {
      const res = await axios.get(`${API}/meetings/${id}`);
      setSelectedMeeting(res.data);
    } catch {
      setError("Could not load meeting details.");
    }
  }

  // ── Upload ─────────────────────────────────────────────────────────────────
  const handleUpload = async (e) => {
    e.preventDefault();
    const file = fileRef.current?.files[0];
    if (!file) return;
    const allowed = [".wav", ".mp3", ".m4a", ".mp4"];
    if (!allowed.some((ext) => file.name.toLowerCase().endsWith(ext))) {
      setError("Please upload a .wav, .mp3, .m4a or .mp4 file.");
      return;
    }
    resetState();
    const formData = new FormData();
    formData.append("audio", file);
    try {
      const res = await axios.post(`${API}/process-meeting`, formData, { timeout: 300000 });
      if (res.data.success) {
        setResult(res.data);
      } else {
        setError(res.data.error || "Processing failed.");
      }
    } catch (err) {
      setError(err.response?.data?.error || "Server error. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  // ── Helpers ────────────────────────────────────────────────────────────────
  function resetState() {
    setLoading(true);
    setResult(null);
    setLogs([]);
    setAgentStatus({});
    setError(null);
  }

  const downloadPDF = (meetingId) => window.open(`${API}/meetings/${meetingId}/pdf`, "_blank");

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="app">
      <div className="header">
        <h1>🤖 MeetingMind AI</h1>
        <p>Autonomous Meeting Agent — Listens, Understands, Acts</p>
        <div className={`ws-badge ws-${wsStatus}`}>
          {wsStatus === "connected" ? "🟢 Live" : wsStatus === "connecting" ? "🟡 Connecting..." : "🔴 Disconnected"}
        </div>
      </div>

      {/* Main Tabs */}
      <div className="main-tabs">
        <button className={tab === "process" ? "active" : ""} onClick={() => setTab("process")}>🚀 Process Meeting</button>
        <button className={tab === "history" ? "active" : ""} onClick={() => setTab("history")}>📚 History</button>
      </div>

      {error && (
        <div className="error-banner">
          ❌ {error}
          <button className="error-close" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* ── PROCESS TAB ── */}
      {tab === "process" && (
        <>
          <div className="mode-toggle">
            <button className={mode === "upload" ? "active" : ""} onClick={() => setMode("upload")}>📁 Upload File</button>
            <button className={mode === "zoom"   ? "active" : ""} onClick={() => setMode("zoom")}>📞 Zoom Auto</button>
          </div>

          <div className="card">
            {mode === "upload" && (
              <form onSubmit={handleUpload}>
                <input type="file" accept=".wav,.mp3,.m4a,.mp4" ref={fileRef} />
                <button type="submit" disabled={loading}>
                  {loading ? "⏳ Processing..." : "🚀 Process Meeting"}
                </button>
              </form>
            )}

            {mode === "zoom" && (
              <div className="zoom-info">
                <div className="zoom-icon">📞</div>
                <h3>Zoom Auto-Processing</h3>
                <p>When your Zoom meeting ends, MeetingMind automatically:</p>
                <ol>
                  <li>Receives the recording via Zoom webhook</li>
                  <li>Downloads and transcribes the audio</li>
                  <li>Extracts action items with Groq AI</li>
                  <li>Sends Slack notifications + creates Calendar events</li>
                </ol>
                <div className="zoom-status-box">
                  <span>Webhook endpoint:</span>
                  <code>POST {window.location.protocol}//{window.location.hostname}:8000/zoom-webhook</code>
                </div>
                <p className="muted">Configure this URL in your Zoom App → Feature → Event Subscriptions.</p>
              </div>
            )}
          </div>

          {/* Agent Status */}
          <div className="agents">
            {AGENTS.map((agent) => (
              <div key={agent.id} className={`agent-card ${agentStatus[agent.id] || ""}`}>
                <div className="agent-emoji">{agent.emoji}</div>
                <div className="agent-info">
                  <strong>{agent.label}</strong>
                  <span>{agent.desc}</span>
                </div>
                <div className="agent-badge">
                  {agentStatus[agent.id] === "running" && <span className="badge running">Running...</span>}
                  {agentStatus[agent.id] === "done"    && <span className="badge done">✅ Done</span>}
                  {agentStatus[agent.id] === "error"   && <span className="badge err">❌ Error</span>}
                  {!agentStatus[agent.id]              && <span className="badge idle">Idle</span>}
                </div>
              </div>
            ))}
          </div>

          {/* Live Logs */}
          {logs.length > 0 && (
            <div className="logs">
              <h3>📋 Live Agent Logs</h3>
              {logs.map((log, i) => (
                <div key={i} className="log-item">
                  <span className="log-time">{log.time}</span>
                  <span>{log.msg}</span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}

          {result && <MeetingResult result={result} onDownloadPDF={downloadPDF} />}
        </>
      )}

      {/* ── HISTORY TAB ── */}
      {tab === "history" && (
        <div className="history-section">
          {selectedMeeting ? (
            <>
              <button className="back-btn" onClick={() => setSelectedMeeting(null)}>← Back to History</button>
              <MeetingResult result={selectedMeeting} onDownloadPDF={downloadPDF} />
            </>
          ) : (
            <>
              <div className="history-header">
                <h3>📚 Past Meetings ({history.length})</h3>
                <button className="refresh-btn" onClick={fetchHistory}>🔄 Refresh</button>
              </div>
              {historyLoading ? (
                <div className="loading-text">Loading meetings...</div>
              ) : history.length === 0 ? (
                <div className="empty-state">No meetings yet. Upload an audio file or wait for a Zoom recording.</div>
              ) : (
                <div className="history-list">
                  {history.map((m) => (
                    <div key={m.id} className="history-card" onClick={() => fetchMeetingDetail(m.id)}>
                      <div className="history-card-top">
                        <span className="meeting-id">Meeting #{m.id}</span>
                        <span className="source-badge">{sourceLabel(m.source)}</span>
                        <span className="meeting-date">{new Date(m.timestamp).toLocaleString()}</span>
                      </div>
                      <p className="history-summary">{m.summary}</p>
                      <div className="history-footer">
                        <span className="action-count">✅ {m.action_items_count} action items</span>
                        <button className="pdf-btn" onClick={(e) => { e.stopPropagation(); downloadPDF(m.id); }}>
                          📄 PDF
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function sourceLabel(source = "") {
  if (source.startsWith("zoom")) return "📞 Zoom";
  if (source === "browser_mic") return "🎙️ Mic";
  if (source === "voice") return "🎤 Voice";
  return "📁 Upload";
}

function MeetingResult({ result, onDownloadPDF }) {
  const [copied, setCopied] = useState(false);

  const copyActions = () => {
    const text = result.action_items?.map(
      (i) => `• [${i.priority?.toUpperCase()}] ${i.assignee}: ${i.task}${i.deadline ? ` (by ${i.deadline})` : ""}`
    ).join("\n");
    navigator.clipboard.writeText(text || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="results">
      {result.meeting_id && (
        <div className="result-actions-bar">
          <span className="meeting-id-badge">Meeting #{result.meeting_id}</span>
          <button className="pdf-download-btn" onClick={() => onDownloadPDF(result.meeting_id)}>
            📄 Download PDF
          </button>
        </div>
      )}

      <div className="card">
        <h3>📝 Summary</h3>
        <p>{result.summary || "No summary available."}</p>
        {result.sentiment && (
          <p style={{marginTop:"8px"}}>
            <strong>Sentiment:</strong> {result.sentiment === "positive" ? "😊 Positive" : result.sentiment === "negative" ? "😟 Negative" : "😐 Neutral"}
            {result.effectiveness_score ? <span style={{marginLeft:"16px"}}><strong>Effectiveness:</strong> {result.effectiveness_score}/10 — {result.effectiveness_reason}</span> : null}
          </p>
        )}
        {result.risks?.length > 0 && (
          <div style={{marginTop:"8px"}}>
            <strong>⚠️ Risks:</strong>
            {result.risks.map((r, i) => <div key={i} className="action-taken" style={{background:"#fff3cd",color:"#856404"}}>⚠️ {r}</div>)}
          </div>
        )}
        {result.repeated_misses?.length > 0 && (
          <div style={{marginTop:"8px"}}>
            <strong>🔁 Repeated Misses:</strong>
            {result.repeated_misses.map((r, i) => <div key={i} className="action-taken" style={{background:"#f8d7da",color:"#721c24"}}>🔁 {r}</div>)}
          </div>
        )}
      </div>

      {result.transcript && (
        <details className="card transcript-card">
          <summary>🎤 Full Transcript</summary>
          <p className="transcript-text">{result.transcript}</p>
        </details>
      )}

      <div className="card">
        <div className="card-header-row">
          <h3>✅ Action Items</h3>
          {result.action_items?.length > 0 && (
            <button className="copy-btn" onClick={copyActions}>{copied ? "✅ Copied!" : "📋 Copy"}</button>
          )}
        </div>
        {!result.action_items?.length && <p className="muted">No action items found.</p>}
        {result.action_items?.map((item, i) => (
          <div key={i} className="action-item">
            <span className={`priority ${item.priority}`}>{item.priority?.toUpperCase()}</span>
            <div>
              <strong>{item.assignee}</strong> — {item.task}
              {item.deadline && <span className="deadline"> 📅 {item.deadline}</span>}
            </div>
          </div>
        ))}
      </div>

      {result.agent_decisions?.length > 0 && (
        <div className="card">
          <h3>🤔 Agent Decisions</h3>
          {result.agent_decisions.map((d, i) => <div key={i} className="action-taken" style={{background:"#e8f4fd",color:"#0c5460"}}>{d}</div>)}
        </div>
      )}

      <div className="card">
        <h3>⚡ Actions Taken</h3>
        {!result.actions_taken?.length && <p className="muted">No actions taken.</p>}
        {result.actions_taken?.map((action, i) => (
          <div key={i} className="action-taken">{action}</div>
        ))}
      </div>
    </div>
  );
}
