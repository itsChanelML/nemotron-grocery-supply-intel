"use client";
// components/CommandCenter.jsx
// Orchaid — Main split-panel command center
// Left: Agent roster + live telemetry feed
// Right: Contextual chat interface (routes to /api/chat)

import { useState, useEffect, useRef } from "react";

const AGENTS = {
  forecasting: {
    id: "forecasting", name: "Forecasting Agent", role: "Demand & Spoilage Intelligence",
    icon: "◈", color: "#00d4aa",
    hint: 'Try: "What are our highest spoilage risks right now?"',
  },
  equipment: {
    id: "equipment", name: "Equipment Agent", role: "Cold Chain & Asset Health",
    icon: "⬡", color: "#3b9eff",
    hint: 'Try: "What equipment needs immediate attention?"',
  },
  safety: {
    id: "safety", name: "Safety Agent", role: "FDA & OSHA Compliance",
    icon: "⬟", color: "#ff6b35",
    hint: 'Try: "Are there any active recalls affecting our inventory?"',
  },
  document: {
    id: "document", name: "Document Agent", role: "BOL & Invoice RAG Intelligence",
    icon: "◫", color: "#b794f4",
    hint: 'Try: "Which BOLs have open discrepancies?"',
  },
};

const LEVEL_COLORS = { CRITICAL: "#ff3b3b", HIGH: "#ff6b35", MEDIUM: "#f5c842", LOW: "#00d4aa" };

const FEED_EVENTS = [
  { time: "09:47:03", agent: "safety",      level: "CRITICAL", msg: "FDA Class II recall — romaine lot #RLT-2024-0891. 340 units in dock. Quarantine pending." },
  { time: "09:44:21", agent: "equipment",   level: "HIGH",     msg: "R-12 compressor cycle +17% above baseline. Cold chain risk escalating." },
  { time: "09:41:08", agent: "document",    level: "MEDIUM",   msg: "BOL #74839 missing cold chain temp log. FDA 21 CFR 117 non-compliance flag." },
  { time: "09:38:55", agent: "forecasting", level: "HIGH",     msg: "Salmon fillets: 2.1d to expiry, 340 units unsold. Markdown recommendation triggered." },
  { time: "09:35:12", agent: "equipment",   level: "MEDIUM",   msg: "AMR-07 odometry drift 3.2x spec. Navigation accuracy degraded." },
  { time: "09:31:44", agent: "safety",      level: "MEDIUM",   msg: "3 AMR-human proximity events this shift. Pattern analysis initiated." },
  { time: "09:28:09", agent: "forecasting", level: "LOW",      msg: "Bread velocity +34% above 7-day avg. Local event demand signal confirmed." },
  { time: "09:25:33", agent: "document",    level: "MEDIUM",   msg: "BOL #74821: 18-case delta vs. Del Monte invoice. Dispute workflow opened." },
  { time: "09:22:17", agent: "equipment",   level: "LOW",      msg: "R-03 door seal integrity at 91%. Scheduled inspection recommended." },
  { time: "09:18:50", agent: "safety",      level: "LOW",      msg: "2 operator forklift certs expiring in 14 days. Renewal reminders sent." },
];

const METRICS = [
  { label: "Active SKUs",    value: "4,847", delta: "+23",   good: true  },
  { label: "At-Risk Units",  value: "701",   delta: "+89",   good: false },
  { label: "Compliance",     value: "91.4%", delta: "-2.1%", good: false },
  { label: "Fleet Uptime",   value: "94.7%", delta: "+0.3%", good: true  },
  { label: "BOL Accuracy",   value: "93.6%", delta: "-0.8%", good: false },
  { label: "Cold Chain OK",  value: "45/47", delta: "-2",    good: false },
];

export default function CommandCenter() {
  const [activeAgent, setActiveAgent] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [time, setTime] = useState("");
  const [feedEvents, setFeedEvents] = useState(FEED_EVENTS);
  const [toast, setToast] = useState(null);         // { action, loop, status, loopTrace }
  const [modal, setModal] = useState(null);         // same shape as toast, shown in modal
  const bottomRef = useRef(null);

  useEffect(() => {
    const tick = () => setTime(new Date().toTimeString().slice(0, 8));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // Clear chat when switching agents
  useEffect(() => { setMessages([]); }, [activeAgent]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-dismiss toast after 8 seconds
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 8000);
    return () => clearTimeout(id);
  }, [toast]);

  const agent = activeAgent ? AGENTS[activeAgent] : null;
  const accentColor = agent?.color || "#00d4aa";
  const filteredFeed = activeAgent ? feedEvents.filter(e => e.agent === activeAgent) : feedEvents;

  function handlePhysicalAction(physicalAction) {
    if (!physicalAction || physicalAction.error) return;

    // Flash new event into the telemetry feed
    const feedEvent = physicalAction.feed_event || physicalAction.feedEvent;
    if (feedEvent) {
      setFeedEvents(prev => [
        { ...feedEvent, isNew: true, actionBadge: feedEvent.action_badge || feedEvent.actionBadge || physicalAction.status },
        ...prev,
      ]);
    }

    // Normalize snake_case from Python → camelCase for modal rendering
    if (physicalAction.loop_trace && !physicalAction.loopTrace) {
      physicalAction.loopTrace = physicalAction.loop_trace;
    }

    // Show toast
    setToast(physicalAction);
  }

  async function sendMessage() {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setLoading(true);

    const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_id: activeAgent || "orchestrator", messages: next }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.response || data.error || "No response." }]);

      // Handle physical action if triggered
      if (data.physical_action) {
        setTimeout(() => handlePhysicalAction(data.physical_action), 800);
      }
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "⚠ Agent communication error. Check server logs." }]);
    }
    setLoading(false);
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Lato:wght@300;400;700&family=Bebas+Neue&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes pulse { 0%,100%{opacity:0.3;transform:scale(0.8)} 50%{opacity:1;transform:scale(1.2)} }
        @keyframes scan { from{transform:translateX(-100%)} to{transform:translateX(100%)} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:translateY(0)} }
        @keyframes slideUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        @keyframes flashIn { 0%{background:rgba(0,212,170,0.2)} 100%{background:transparent} }
        input::placeholder { color: rgba(255,255,255,0.25); }
        input:focus { outline: none; }
        .action-flash { animation: flashIn 2s ease forwards; }
      `}</style>

      <div style={{ width:"100vw", height:"100vh", background:"#070c15", display:"flex", flexDirection:"column",
        backgroundImage:`radial-gradient(ellipse 70% 50% at 15% 20%, rgba(0,212,170,0.04) 0%, transparent 60%),
          radial-gradient(ellipse 50% 40% at 85% 80%, rgba(59,158,255,0.04) 0%, transparent 60%)`,
        fontFamily:"'DM Mono', monospace", color:"rgba(255,255,255,0.85)", overflow:"hidden",
        position:"relative" }}>

        {/* ── Toast notification ───────────────────────────────────── */}
        {toast && (
          <div onClick={() => { setModal(toast); setToast(null); }} style={{
            position:"absolute", bottom:40, right:20, zIndex:100,
            width:340, padding:"14px 16px",
            background:"rgba(10,18,30,0.97)",
            border:`1px solid ${
              toast.loop === "equipment_dispatch" ? "#3b9eff" :
              toast.loop === "wms_quarantine" ? "#ff6b35" : "#00d4aa"
            }`,
            borderRadius:10,
            boxShadow:`0 8px 40px rgba(0,0,0,0.6), 0 0 20px ${
              toast.loop === "equipment_dispatch" ? "rgba(59,158,255,0.15)" :
              toast.loop === "wms_quarantine" ? "rgba(255,107,53,0.15)" : "rgba(0,212,170,0.15)"
            }`,
            cursor:"pointer",
            animation:"slideUp 0.3s ease",
          }}>
            <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
              <div style={{
                width:28, height:28, borderRadius:6, flexShrink:0,
                display:"flex", alignItems:"center", justifyContent:"center", fontSize:14,
                background: toast.loop === "equipment_dispatch" ? "rgba(59,158,255,0.2)" :
                            toast.loop === "wms_quarantine" ? "rgba(255,107,53,0.2)" : "rgba(0,212,170,0.2)",
              }}>
                {toast.loop === "equipment_dispatch" ? "📲" :
                 toast.loop === "wms_quarantine" ? "🚫" : "🏷️"}
              </div>
              <div style={{ flex:1 }}>
                <div style={{ fontSize:9, letterSpacing:"0.12em", color:
                  toast.loop === "equipment_dispatch" ? "#3b9eff" :
                  toast.loop === "wms_quarantine" ? "#ff6b35" : "#00d4aa"
                }}>PHYSICAL AI — LOOP CLOSED</div>
                <div style={{ fontSize:11, color:"rgba(255,255,255,0.85)", marginTop:2, fontFamily:"'Lato', sans-serif" }}>
                  {toast.loop === "equipment_dispatch" ? "Maintenance dispatch → Google Chat" :
                   toast.loop === "wms_quarantine" ? "Inventory quarantine → WMS updated" :
                   "Markdown applied → POS updated"}
                </div>
              </div>
              <div style={{
                padding:"2px 7px", borderRadius:3, fontSize:8, letterSpacing:"0.1em", fontWeight:700,
                background: toast.loop === "equipment_dispatch" ? "rgba(59,158,255,0.2)" :
                            toast.loop === "wms_quarantine" ? "rgba(255,107,53,0.2)" : "rgba(0,212,170,0.2)",
                color: toast.loop === "equipment_dispatch" ? "#3b9eff" :
                       toast.loop === "wms_quarantine" ? "#ff6b35" : "#00d4aa",
              }}>{toast.status}</div>
            </div>
            <div style={{ fontSize:9, color:"rgba(255,255,255,0.4)", fontFamily:"'Lato', sans-serif" }}>
              Tap to view full loop trace →
            </div>
          </div>
        )}

        {/* ── Loop Trace Modal ─────────────────────────────────────── */}
        {modal && (
          <div onClick={() => setModal(null)} style={{
            position:"absolute", inset:0, zIndex:200,
            background:"rgba(0,0,0,0.75)", backdropFilter:"blur(6px)",
            display:"flex", alignItems:"center", justifyContent:"center",
          }}>
            <div onClick={e => e.stopPropagation()} style={{
              width:520, maxWidth:"90vw",
              background:"rgba(10,18,30,0.98)",
              border:`1px solid ${
                modal.loop === "equipment_dispatch" ? "#3b9eff" :
                modal.loop === "wms_quarantine" ? "#ff6b35" : "#00d4aa"
              }`,
              borderRadius:12,
              boxShadow:"0 24px 80px rgba(0,0,0,0.8)",
              overflow:"hidden",
            }}>
              {/* Modal header */}
              <div style={{
                padding:"16px 20px",
                borderBottom:"1px solid rgba(255,255,255,0.08)",
                display:"flex", alignItems:"center", gap:12,
                background: modal.loop === "equipment_dispatch" ? "rgba(59,158,255,0.08)" :
                            modal.loop === "wms_quarantine" ? "rgba(255,107,53,0.08)" : "rgba(0,212,170,0.08)",
              }}>
                <div style={{ fontSize:20 }}>
                  {modal.loop === "equipment_dispatch" ? "📲" :
                   modal.loop === "wms_quarantine" ? "🚫" : "🏷️"}
                </div>
                <div>
                  <div style={{ fontSize:11, letterSpacing:"0.1em", color:
                    modal.loop === "equipment_dispatch" ? "#3b9eff" :
                    modal.loop === "wms_quarantine" ? "#ff6b35" : "#00d4aa"
                  }}>PHYSICAL AI LOOP TRACE</div>
                  <div style={{ fontSize:9, color:"rgba(255,255,255,0.4)", marginTop:2 }}>
                    {modal.loop === "equipment_dispatch" ? "Equipment Agent → Google Chat Dispatch" :
                     modal.loop === "wms_quarantine" ? "Safety Agent → WMS Quarantine" :
                     "Forecasting Agent → POS Markdown"} · {modal.timestamp?.slice(11,19)} UTC
                  </div>
                </div>
                <button onClick={() => setModal(null)} style={{
                  marginLeft:"auto", background:"none", border:"none",
                  color:"rgba(255,255,255,0.4)", cursor:"pointer", fontSize:16,
                }}>✕</button>
              </div>

              {/* Loop trace steps */}
              <div style={{ padding:"20px", display:"flex", flexDirection:"column", gap:0 }}>
                {modal.loopTrace && Object.values(modal.loopTrace).map((step, i, arr) => (
                  <div key={i}>
                    <div style={{ display:"flex", gap:12, alignItems:"flex-start" }}>
                      <div style={{ display:"flex", flexDirection:"column", alignItems:"center" }}>
                        <div style={{
                          width:32, height:32, borderRadius:"50%", flexShrink:0,
                          display:"flex", alignItems:"center", justifyContent:"center",
                          fontSize:14,
                          background: i === arr.length - 1 ? "rgba(0,212,170,0.2)" : "rgba(255,255,255,0.06)",
                          border: i === arr.length - 1 ? "1px solid rgba(0,212,170,0.5)" : "1px solid rgba(255,255,255,0.1)",
                        }}>{step.icon}</div>
                        {i < arr.length - 1 && (
                          <div style={{ width:1, height:20, background:"rgba(255,255,255,0.08)", margin:"4px 0" }} />
                        )}
                      </div>
                      <div style={{ flex:1, paddingBottom: i < arr.length - 1 ? 4 : 0 }}>
                        <div style={{ fontSize:9, letterSpacing:"0.1em", color:"rgba(255,255,255,0.4)", marginBottom:3 }}>
                          STEP {i + 1} — {step.label?.toUpperCase()}
                        </div>
                        <div style={{ fontSize:11, color:"rgba(255,255,255,0.8)", lineHeight:1.6, fontFamily:"'Lato', sans-serif" }}>
                          {step.detail}
                        </div>
                        {step.model && (
                          <div style={{ fontSize:8, color:"rgba(255,255,255,0.3)", marginTop:4 }}>
                            Model: {step.model}
                          </div>
                        )}
                        {step.channel && (
                          <div style={{ fontSize:8, color:"rgba(255,255,255,0.3)", marginTop:4 }}>
                            Channel: {step.channel}
                          </div>
                        )}
                        {step.demo && (
                          <div style={{ fontSize:8, color:"#f5c842", marginTop:4 }}>
                            ⚠ Add GOOGLE_CHAT_WEBHOOK_URL to send live Google Chat alerts
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Modal footer */}
              <div style={{
                padding:"12px 20px",
                borderTop:"1px solid rgba(255,255,255,0.06)",
                display:"flex", justifyContent:"space-between", alignItems:"center",
              }}>
                <div style={{ fontSize:8, color:"rgba(255,255,255,0.25)" }}>
                  Action ID: {modal.actionId} · MAIW Blueprint · Physical AI Loop
                </div>
                <button onClick={() => setModal(null)} style={{
                  padding:"6px 14px", borderRadius:5, border:"none", cursor:"pointer",
                  background:"rgba(255,255,255,0.08)", color:"rgba(255,255,255,0.6)",
                  fontSize:9, fontFamily:"'DM Mono', monospace", letterSpacing:"0.08em",
                }}>CLOSE</button>
              </div>
            </div>
          </div>
        )}

        {/* ── Top bar ─────────────────────────────────────── */}
        <div style={{ height:52, background:"rgba(0,0,0,0.45)", borderBottom:"1px solid rgba(0,212,170,0.18)",
          display:"flex", alignItems:"center", padding:"0 20px", gap:20, flexShrink:0, position:"relative" }}>
          <div style={{ position:"absolute", bottom:0, left:0, right:0, height:1,
            background:"linear-gradient(90deg,transparent,#00d4aa33,transparent)" }} />

          <span style={{ fontFamily:"'Bebas Neue'", fontSize:21, letterSpacing:"0.12em", color:"#00d4aa" }}>ORCHAID</span>
          <span style={{ fontSize:8, color:"rgba(255,255,255,0.25)", letterSpacing:"0.15em" }}>
            STATER BROS. DC · SAN BERNARDINO, CA · MAIW LITE
          </span>

          <div style={{ width:1, height:22, background:"rgba(255,255,255,0.08)" }} />

          <div style={{ display:"flex", gap:16 }}>
            {METRICS.map(m => (
              <div key={m.label}>
                <div style={{ fontSize:7, color:"rgba(255,255,255,0.3)", letterSpacing:"0.1em", marginBottom:2 }}>{m.label}</div>
                <div style={{ display:"flex", alignItems:"baseline", gap:4 }}>
                  <span style={{ fontSize:12, fontWeight:500 }}>{m.value}</span>
                  <span style={{ fontSize:8, color: m.good ? "#00d4aa" : "#ff6b35" }}>{m.delta}</span>
                </div>
              </div>
            ))}
          </div>

          <div style={{ marginLeft:"auto", display:"flex", alignItems:"center", gap:14 }}>
            <span style={{ fontSize:10, color:"rgba(255,255,255,0.4)" }}>
              <span style={{ color:"#00d4aa", animation:"blink 2s ease infinite" }}>●</span> {time} PST
            </span>
            {[["1 CRITICAL","#ff3b3b"],["2 HIGH","#ff6b35"]].map(([label, color]) => (
              <div key={label} style={{ padding:"3px 8px", borderRadius:3, fontSize:8, letterSpacing:"0.08em",
                background:`${color}18`, border:`1px solid ${color}44`, color }}>{label}</div>
            ))}
          </div>
        </div>

        {/* ── Body ────────────────────────────────────────── */}
        <div style={{ flex:1, display:"flex", overflow:"hidden" }}>

          {/* Left panel */}
          <div style={{ width:320, flexShrink:0, borderRight:"1px solid rgba(255,255,255,0.06)", display:"flex", flexDirection:"column" }}>

            {/* Agent cards */}
            <div style={{ padding:12, display:"flex", flexDirection:"column", gap:6, borderBottom:"1px solid rgba(255,255,255,0.06)" }}>
              <div style={{ fontSize:7, color:"rgba(255,255,255,0.25)", letterSpacing:"0.15em", marginBottom:4 }}>AGENT ROSTER · 4 ACTIVE</div>

              {/* Orchestrator */}
              <button onClick={() => setActiveAgent(null)} style={{
                background: !activeAgent ? "rgba(255,255,255,0.05)" : "transparent",
                border:`1px solid ${!activeAgent ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.05)"}`,
                borderRadius:5, padding:"9px 12px", cursor:"pointer", textAlign:"left", width:"100%",
                display:"flex", alignItems:"center", gap:10, transition:"all 0.2s",
              }}>
                <span style={{ fontSize:15, color:"rgba(255,255,255,0.5)" }}>◉</span>
                <div>
                  <div style={{ fontSize:9, color:"rgba(255,255,255,0.65)", letterSpacing:"0.08em" }}>ORCHESTRATOR</div>
                  <div style={{ fontSize:7, color:"rgba(255,255,255,0.28)", marginTop:2 }}>Gemini · All agents</div>
                </div>
              </button>

              {Object.values(AGENTS).map(ag => {
                const topEvent = FEED_EVENTS.find(e => e.agent === ag.id);
                const isActive = activeAgent === ag.id;
                return (
                  <button key={ag.id} onClick={() => setActiveAgent(isActive ? null : ag.id)} style={{
                    background: isActive ? `rgba(${ag.color === "#00d4aa" ? "0,212,170" : ag.color === "#3b9eff" ? "59,158,255" : ag.color === "#ff6b35" ? "255,107,53" : "183,148,244"},0.12)` : "transparent",
                    border:`1px solid ${isActive ? ag.color : "rgba(255,255,255,0.05)"}`,
                    borderRadius:5, padding:"10px 12px", cursor:"pointer", textAlign:"left", width:"100%",
                    transition:"all 0.2s", position:"relative", overflow:"hidden",
                  }}>
                    {isActive && <div style={{ position:"absolute", top:0, left:0, right:0, height:1,
                      background:`linear-gradient(90deg,transparent,${ag.color},transparent)`,
                      animation:"scan 2s linear infinite" }} />}
                    <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6 }}>
                      <span style={{ fontSize:16, color:ag.color }}>{ag.icon}</span>
                      <div style={{ flex:1 }}>
                        <div style={{ fontSize:9, color:ag.color, letterSpacing:"0.08em" }}>{ag.name}</div>
                        <div style={{ fontSize:7, color:"rgba(255,255,255,0.3)", marginTop:1 }}>{ag.role}</div>
                      </div>
                      {topEvent && (
                        <div style={{ padding:"2px 6px", borderRadius:2, fontSize:7, letterSpacing:"0.08em",
                          background:`${LEVEL_COLORS[topEvent.level]}22`, color:LEVEL_COLORS[topEvent.level],
                          border:`1px solid ${LEVEL_COLORS[topEvent.level]}44` }}>{topEvent.level}</div>
                      )}
                    </div>
                    {topEvent && <div style={{ fontSize:8, color:"rgba(255,255,255,0.32)", lineHeight:1.5 }}>
                      {topEvent.msg.slice(0, 58)}…
                    </div>}
                  </button>
                );
              })}
            </div>

            {/* Event feed */}
            <div style={{ flex:1, overflow:"hidden", display:"flex", flexDirection:"column" }}>
              <div style={{ padding:"10px 12px 6px", display:"flex", alignItems:"center" }}>
                <span style={{ fontSize:7, color:"rgba(255,255,255,0.25)", letterSpacing:"0.15em" }}>
                  TELEMETRY FEED{activeAgent ? ` · ${AGENTS[activeAgent]?.name.toUpperCase()}` : " · ALL AGENTS"}
                </span>
                <div style={{ marginLeft:"auto", width:5, height:5, borderRadius:"50%", background:"#00d4aa", animation:"pulse 2s ease infinite" }} />
              </div>
              <div style={{ flex:1, overflowY:"auto", padding:"0 8px 12px", display:"flex", flexDirection:"column", gap:3 }}>
                {filteredFeed.map((ev, i) => (
                  <div key={i} className={ev.isNew ? "action-flash" : ""} style={{
                    display:"flex", gap:10, alignItems:"flex-start", padding:"7px 10px", borderRadius:4,
                    background: i === 0 ? "rgba(255,255,255,0.03)" : "transparent",
                    borderLeft:`3px solid ${LEVEL_COLORS[ev.level]}`,
                  }}>
                    <span style={{ fontSize:9, color:"rgba(255,255,255,0.25)", whiteSpace:"nowrap", marginTop:1 }}>{ev.time}</span>
                    <span style={{ fontSize:11, color:AGENTS[ev.agent]?.color }}>{AGENTS[ev.agent]?.icon}</span>
                    <div style={{ flex:1 }}>
                      <div style={{ display:"flex", gap:6, marginBottom:2, alignItems:"center", flexWrap:"wrap" }}>
                        <span style={{ fontSize:7, color:LEVEL_COLORS[ev.level], letterSpacing:"0.1em" }}>{ev.level}</span>
                        <span style={{ fontSize:7, color:"rgba(255,255,255,0.25)" }}>{AGENTS[ev.agent]?.name}</span>
                        {ev.actionBadge && (
                          <span style={{
                            fontSize:7, letterSpacing:"0.1em", padding:"1px 5px", borderRadius:2,
                            background: ev.actionBadge === "DISPATCHED" ? "rgba(59,158,255,0.2)" :
                                        ev.actionBadge === "QUARANTINED" ? "rgba(255,107,53,0.25)" : "rgba(0,212,170,0.2)",
                            color: ev.actionBadge === "DISPATCHED" ? "#3b9eff" :
                                   ev.actionBadge === "QUARANTINED" ? "#ff6b35" : "#00d4aa",
                            border: `1px solid ${ev.actionBadge === "DISPATCHED" ? "#3b9eff44" :
                                     ev.actionBadge === "QUARANTINED" ? "#ff6b3544" : "#00d4aa44"}`,
                            fontWeight: 700,
                          }}>⚡ {ev.actionBadge}</span>
                        )}
                      </div>
                      <div style={{ fontSize:10, color:"rgba(255,255,255,0.65)", lineHeight:1.5, fontFamily:"'Lato', sans-serif" }}>{ev.msg}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right panel — Chat */}
          <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>

            {/* Chat header */}
            <div style={{ padding:"14px 20px", borderBottom:"1px solid rgba(255,255,255,0.06)", display:"flex", alignItems:"center", gap:12 }}>
              <span style={{ fontSize:20, color:accentColor }}>{agent?.icon || "◉"}</span>
              <div>
                <div style={{ fontSize:11, color:accentColor, letterSpacing:"0.08em" }}>
                  {agent ? agent.name.toUpperCase() : "MAIW ORCHESTRATOR"}
                </div>
                <div style={{ fontSize:8, color:"rgba(255,255,255,0.3)", marginTop:2 }}>
                  {agent
                    ? `NIM: ${agent.id === "safety" ? "nvidia/nemotron-3.5-lightning-30b-a3b" : "nvidia/nemotron-3-super-120b-a12b"}`
                    : "Gemini 2.5 Pro · Vertex AI · Coordinating 4 NIM agents"}
                </div>
              </div>
              <div style={{ marginLeft:"auto", display:"flex", alignItems:"center", gap:6 }}>
                <div style={{ width:6, height:6, borderRadius:"50%", background:"#00d4aa", boxShadow:"0 0 8px #00d4aa" }} />
                <span style={{ fontSize:8, color:"rgba(255,255,255,0.35)" }}>ONLINE</span>
              </div>
            </div>

            {/* Messages */}
            <div style={{ flex:1, overflowY:"auto", padding:"16px 20px", display:"flex", flexDirection:"column", gap:14 }}>
              {messages.length === 0 && (
                <div style={{ margin:"auto", textAlign:"center", opacity:0.4 }}>
                  <div style={{ fontSize:30, marginBottom:10 }}>{agent?.icon || "◉"}</div>
                  <div style={{ fontSize:10, color:"rgba(255,255,255,0.6)", lineHeight:1.9, fontFamily:"'Lato', sans-serif" }}>
                    {agent ? `${agent.name} is online.` : "Orchaid Orchestrator is online."}<br/>
                    <span style={{ color:accentColor, fontSize:9 }}>{agent?.hint || 'Try: "What\'s our highest risk right now?"'}</span>
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} style={{ display:"flex", gap:10, justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                  {m.role === "assistant" && (
                    <div style={{ width:28, height:28, borderRadius:4, flexShrink:0, display:"flex",
                      alignItems:"center", justifyContent:"center", fontSize:12, color:accentColor,
                      background:`${accentColor}22`, border:`1px solid ${accentColor}44` }}>{agent?.icon || "◉"}</div>
                  )}
                  <div style={{
                    maxWidth:"78%", padding:"10px 14px",
                    borderRadius: m.role === "user" ? "12px 12px 2px 12px" : "2px 12px 12px 12px",
                    background: m.role === "user" ? `${accentColor}22` : "rgba(255,255,255,0.04)",
                    border: m.role === "user" ? `1px solid ${accentColor}44` : "1px solid rgba(255,255,255,0.07)",
                    fontFamily:"'Lato', sans-serif", fontSize:12, color:"rgba(255,255,255,0.88)",
                    lineHeight:1.75, whiteSpace:"pre-wrap",
                  }}>{m.content}</div>
                </div>
              ))}

              {loading && (
                <div style={{ display:"flex", gap:10 }}>
                  <div style={{ width:28, height:28, borderRadius:4, display:"flex", alignItems:"center",
                    justifyContent:"center", fontSize:12, color:accentColor,
                    background:`${accentColor}22`, border:`1px solid ${accentColor}44` }}>{agent?.icon || "◉"}</div>
                  <div style={{ padding:"12px 16px", borderRadius:"2px 12px 12px 12px",
                    background:"rgba(255,255,255,0.04)", border:"1px solid rgba(255,255,255,0.07)" }}>
                    <div style={{ display:"flex", gap:4 }}>
                      {[0,1,2].map(i => <div key={i} style={{ width:5, height:5, borderRadius:"50%",
                        background:accentColor, animation:`pulse 1.2s ease ${i*0.2}s infinite` }} />)}
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div style={{ padding:"12px 16px", borderTop:"1px solid rgba(255,255,255,0.06)", display:"flex", gap:10 }}>
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                placeholder={agent ? `Ask ${agent.name}…` : "Query all agents or the orchestrator…"}
                style={{
                  flex:1, background:"rgba(255,255,255,0.04)",
                  border:`1px solid ${input ? accentColor+"55" : "rgba(255,255,255,0.08)"}`,
                  borderRadius:6, padding:"10px 14px",
                  fontFamily:"'DM Mono', monospace", fontSize:11,
                  color:"rgba(255,255,255,0.85)", transition:"border-color 0.2s",
                }}
              />
              <button onClick={sendMessage} disabled={loading || !input.trim()} style={{
                padding:"10px 18px", borderRadius:6, border:"none", cursor: loading || !input.trim() ? "default" : "pointer",
                background: loading || !input.trim() ? "rgba(255,255,255,0.06)" : `linear-gradient(135deg,${accentColor},${accentColor}bb)`,
                color: loading || !input.trim() ? "rgba(255,255,255,0.25)" : "#060b14",
                fontFamily:"'DM Mono', monospace", fontSize:11, fontWeight:700,
                letterSpacing:"0.05em", transition:"all 0.2s",
              }}>SEND</button>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div style={{ height:26, flexShrink:0, borderTop:"1px solid rgba(255,255,255,0.05)",
          background:"rgba(0,0,0,0.3)", display:"flex", alignItems:"center", padding:"0 18px", gap:18 }}>
          {[
            ["NVIDIA NIM","nemotron-3-super-120b · nemotron-3.5-lightning-30b · nemotron-3-embed-1b"],
            ["ORCHESTRATOR","Gemini 2.5 Pro · Vertex AI"],
            ["GCP","BigQuery · Document AI · Cloud Storage · Vertex AI"],
            ["COMPLIANCE","FDA OpenFDA API · Live recall cross-reference"],
            ["DEPLOYMENT","Vercel · Next.js 14"],
          ].map(([label, val]) => (
            <div key={label} style={{ display:"flex", gap:5, alignItems:"center" }}>
              <span style={{ fontSize:7, color:"rgba(255,255,255,0.2)", letterSpacing:"0.1em" }}>{label}</span>
              <span style={{ fontSize:7, color:"rgba(255,255,255,0.42)" }}>{val}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
