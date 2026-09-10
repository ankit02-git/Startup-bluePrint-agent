import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./index.css";

const API_BASE = process.env.REACT_APP_API_URL || "";

const SECTION_CONFIG = [
  { key: "executive_summary",    label: "Executive Summary",      icon: "📋" },
  { key: "business_model_canvas",label: "Business Model Canvas",  icon: "🗺️" },
  { key: "market_analysis",      label: "Market Analysis",        icon: "📊" },
  { key: "revenue_model",        label: "Revenue Model",          icon: "💰" },
  { key: "estimated_budget",     label: "Estimated Budget",       icon: "💵" },
  { key: "go_to_market",         label: "Go-To-Market Strategy",  icon: "🚀" },
  { key: "funding_roadmap",      label: "Funding Roadmap",        icon: "🏦" },
  { key: "legal_compliance",     label: "Legal & Compliance",     icon: "⚖️" },
  { key: "tech_stack",           label: "Technology Stack",       icon: "🛠️" },
  { key: "action_plan",          label: "90-Day Action Plan",     icon: "📅" },
  { key: "full_blueprint",       label: "Full Blueprint",         icon: "📄" },
];

const EXAMPLE_IDEAS = [
  "An AI-powered mental health app for college students that provides anonymous peer support and connects them with licensed therapists in India.",
  "A B2B SaaS platform that uses computer vision to automate quality control inspections in food manufacturing factories.",
  "A hyperlocal delivery service for organic farm produce connecting urban consumers directly with rural farmers in Tier 2 Indian cities.",
  "A blockchain-based carbon credit trading platform for SMEs to offset their emissions and access green financing.",
  "An EdTech platform using AR/VR to teach practical vocational skills like plumbing and electrical work to unemployed youth.",
];

const LOADING_STEPS = [
  "Analyzing your startup idea...",
  "Retrieving market research data...",
  "Fetching funding and investor information...",
  "Querying legal and compliance requirements...",
  "Retrieving go-to-market strategies...",
  "Sending to IBM Granite AI for blueprint generation...",
  "Structuring your complete blueprint...",
];

// ─── Lightweight markdown renderer ───────────────────────────────────────────
function renderLine(line, idx) {
  // Heading levels
  const h3 = line.match(/^###\s+(.*)/);
  if (h3) return <h3 key={idx} className="md-h3">{inlineFormat(h3[1])}</h3>;
  const h2 = line.match(/^##\s+(.*)/);
  if (h2) return <h2 key={idx} className="md-h2">{inlineFormat(h2[1])}</h2>;
  const h1 = line.match(/^#\s+(.*)/);
  if (h1) return <h1 key={idx} className="md-h1">{inlineFormat(h1[1])}</h1>;
  // Bullet list
  const bullet = line.match(/^[-*]\s+(.*)/);
  if (bullet) return <li key={idx} className="md-li">{inlineFormat(bullet[1])}</li>;
  // Numbered list
  const numbered = line.match(/^\d+\.\s+(.*)/);
  if (numbered) return <li key={idx} className="md-li md-li-num">{inlineFormat(numbered[1])}</li>;
  // Horizontal rule
  if (/^---+$/.test(line.trim())) return <hr key={idx} className="md-hr" />;
  // Empty line → spacer
  if (!line.trim()) return <div key={idx} className="md-gap" />;
  // Normal paragraph line
  return <p key={idx} className="md-p">{inlineFormat(line)}</p>;
}

function inlineFormat(text) {
  // Split on **bold**, *italic*, `code`
  const parts = [];
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let last = 0;
  let match;
  let i = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push(<span key={i++}>{text.slice(last, match.index)}</span>);
    if (match[2]) parts.push(<strong key={i++}>{match[2]}</strong>);
    else if (match[3]) parts.push(<em key={i++}>{match[3]}</em>);
    else if (match[4]) parts.push(<code key={i++} className="md-code">{match[4]}</code>);
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(<span key={i++}>{text.slice(last)}</span>);
  return parts.length ? parts : text;
}

function MdContent({ text }) {
  if (!text) return null;
  const lines = text.split("\n");
  const nodes = lines.map((line, idx) => renderLine(line, idx));
  return <div className="md-body">{nodes}</div>;
}
// ─────────────────────────────────────────────────────────────────────────────

function SectionCard({ sectionKey, title, icon, content }) {
  const [isOpen, setIsOpen] = useState(true);
  return (
    <div className="section-card" id={`section-${sectionKey}`}>
      <div className="section-card-header" onClick={() => setIsOpen(o => !o)}>
        <span className="section-icon">{icon}</span>
        <span className="section-title">{title}</span>
        <span className={`section-chevron ${isOpen ? "open" : ""}`}>▼</span>
      </div>
      {isOpen && (
        <div className="section-body">
          <MdContent text={content} />
        </div>
      )}
    </div>
  );
}

function LoadingState({ step }) {
  return (
    <div className="loading-card">
      <div className="loading-spinner" />
      <div className="loading-title">Generating Your Startup Blueprint</div>
      <div className="loading-subtitle">
        IBM Granite is analyzing your idea using RAG‑powered knowledge...
      </div>
      <div className="progress-steps">
        {LOADING_STEPS.map((s, i) => (
          <div key={i} className={`progress-step ${i < step ? "done" : i === step ? "active" : ""}`}>
            <div className="step-dot" />
            {s}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [idea, setIdea]               = useState("");
  const [industry, setIndustry]       = useState("");
  const [targetMarket, setTargetMarket] = useState("");
  const [loading, setLoading]         = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [blueprint, setBlueprint]     = useState(null);
  const [error, setError]             = useState(null);
  const [showRaw, setShowRaw]         = useState(false);
  const [healthStatus, setHealthStatus] = useState(null);
  const stepInterval = useRef(null);
  const resultRef    = useRef(null);

  useEffect(() => {
    axios.get(`${API_BASE}/api/health`)
      .then(res => setHealthStatus(res.data))
      .catch(() => setHealthStatus(null));
  }, []);

  const startLoadingSteps = () => {
    setLoadingStep(0);
    stepInterval.current = setInterval(() => {
      setLoadingStep(s => {
        if (s >= LOADING_STEPS.length - 1) { clearInterval(stepInterval.current); return s; }
        return s + 1;
      });
    }, 2500);
  };

  const handleGenerate = async () => {
    if (idea.trim().length < 20) return;
    setError(null);
    setBlueprint(null);
    setShowRaw(false);
    setLoading(true);
    startLoadingSteps();
    try {
      const response = await axios.post(`${API_BASE}/api/blueprint`, {
        idea: idea.trim(),
        industry: industry || undefined,
        target_market: targetMarket || undefined,
      });
      setBlueprint(response.data);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to generate blueprint.");
    } finally {
      clearInterval(stepInterval.current);
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!blueprint) return;
    const content = `STARTUP BLUEPRINT\n${"=".repeat(60)}\n\nIdea: ${blueprint.idea}\nModel: ${blueprint.model_used}\nTime: ${blueprint.generation_time_seconds}s\n\n${"=".repeat(60)}\n\n${blueprint.raw_blueprint}`;
    const blob = new Blob([content], { type: "text/plain" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = "startup-blueprint.txt"; a.click();
    URL.revokeObjectURL(url);
  };

  const availableSections = blueprint
    ? SECTION_CONFIG.filter(s => blueprint.sections?.[s.key])
    : [];

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-brand">
          <div className="header-logo">SB</div>
          <div>
            <div className="header-title">Startup Blueprint Generator</div>
            <div className="header-subtitle">RAG + IBM Granite AI Agent</div>
          </div>
        </div>
        <div className="ibm-badge">⚡ Powered by IBM Granite</div>
      </header>

      <main className="main-container">
        {/* ── Hero ── */}
        <section className="hero">
          <h1 className="hero-title">From Startup Idea to<br />Complete Blueprint</h1>
          <p className="hero-description">
            Describe your startup idea in plain English. Our AI agent, powered by IBM Granite
            and RAG technology, retrieves market data, funding options, legal requirements, and
            competitor insights to generate a complete, actionable business blueprint.
          </p>
          <div className="hero-tags">
            <span className="hero-tag highlight">IBM Granite AI</span>
            <span className="hero-tag highlight">RAG‑Powered</span>
            <span className="hero-tag">Market Analysis</span>
            <span className="hero-tag">Business Model Canvas</span>
            <span className="hero-tag">Funding Roadmap</span>
            <span className="hero-tag">Legal Compliance</span>
            <span className="hero-tag">Go‑To‑Market</span>
            <span className="hero-tag">90‑Day Plan</span>
          </div>
        </section>

        {/* ── IBM Config Warning ── */}
        {healthStatus && !healthStatus.ibm_granite_configured && (
          <div className="config-warning">
            <span className="config-warning-icon">⚠️</span>
            <div>
              <div className="config-warning-title">IBM watsonx.ai Not Configured</div>
              <div className="config-warning-text">
                Set <strong>WATSONX_API_KEY</strong> and <strong>WATSONX_PROJECT_ID</strong> in{" "}
                <code>backend/.env</code>.{" "}
                <a href="https://cloud.ibm.com/registration" target="_blank" rel="noreferrer">
                  Get a free IBM Cloud account →
                </a>
              </div>
            </div>
          </div>
        )}

        {/* ── Input Card ── */}
        <div className="input-card">
          <div className="input-card-title">💡 Describe Your Startup Idea</div>
          <div className="input-card-subtitle">
            Be specific: include the problem, your target users, and your unique angle.
          </div>

          <div className="examples-section">
            <div className="examples-title">Try an example:</div>
            <div className="examples-list">
              {EXAMPLE_IDEAS.map((ex, i) => (
                <button key={i} className="example-chip" onClick={() => setIdea(ex)} title={ex}>
                  {ex.split(" ").slice(0, 6).join(" ")}…
                </button>
              ))}
            </div>
          </div>

          <textarea
            className="idea-textarea"
            placeholder="E.g., A mobile app that uses AI to help farmers in rural India detect crop diseases by taking photos, providing instant diagnosis and connecting them with local agronomists and relevant government subsidy schemes..."
            value={idea}
            onChange={e => setIdea(e.target.value)}
            rows={5}
            maxLength={2000}
          />
          <div className="char-count">{idea.length}/2000 characters</div>

          <div className="input-row">
            <div className="input-field">
              <label>Industry (optional)</label>
              <input type="text" placeholder="e.g., AgriTech, FinTech, HealthTech"
                value={industry} onChange={e => setIndustry(e.target.value)} />
            </div>
            <div className="input-field">
              <label>Target Market (optional)</label>
              <input type="text" placeholder="e.g., India, USA, Southeast Asia"
                value={targetMarket} onChange={e => setTargetMarket(e.target.value)} />
            </div>
          </div>

          <button
            className="generate-btn"
            onClick={handleGenerate}
            disabled={loading || idea.trim().length < 20}
          >
            {loading
              ? <><span className="btn-spinner" /> Generating Blueprint…</>
              : <>⚡ Generate Startup Blueprint with IBM Granite</>
            }
          </button>
        </div>

        {/* ── Loading ── */}
        {loading && <LoadingState step={loadingStep} />}

        {/* ── Error ── */}
        {error && (
          <div className="error-card">
            <div className="error-title">❌ Generation Failed</div>
            <div className="error-message">{error}</div>
          </div>
        )}

        {/* ── Result ── */}
        {blueprint && !loading && (
          <div ref={resultRef}>
            <div className="blueprint-header">
              <div>
                <div className="blueprint-idea">
                  🎯 {blueprint.idea.substring(0, 160)}{blueprint.idea.length > 160 ? "…" : ""}
                </div>
                <div className="blueprint-meta">
                  <span className="blueprint-meta-item">⚡ Model: <span className="value">{blueprint.model_used}</span></span>
                  <span className="blueprint-meta-item">⏱ Time: <span className="value">{blueprint.generation_time_seconds}s</span></span>
                  <span className="blueprint-meta-item">📑 Sections: <span className="value">{availableSections.length}</span></span>
                </div>
              </div>
              <div className="action-buttons">
                <button className="action-btn secondary" onClick={() => setShowRaw(r => !r)}>
                  {showRaw ? "📊 Sectioned View" : "📄 Raw View"}
                </button>
                <button className="action-btn primary" onClick={handleDownload}>
                  ⬇️ Download
                </button>
              </div>
            </div>

            {!showRaw && availableSections.length > 0 && (
              <div className="section-tabs">
                {availableSections.map(s => (
                  <button key={s.key} className="section-tab"
                    onClick={() => document.getElementById(`section-${s.key}`)?.scrollIntoView({ behavior: "smooth", block: "start" })}>
                    {s.icon} {s.label}
                  </button>
                ))}
              </div>
            )}

            {showRaw
              ? <div className="raw-view">{blueprint.raw_blueprint}</div>
              : (
                <div className="sections-grid">
                  {availableSections.map(s => (
                    <SectionCard key={s.key} sectionKey={s.key}
                      title={s.label} icon={s.icon} content={blueprint.sections[s.key]} />
                  ))}
                </div>
              )
            }
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="footer">
        <div>
          Startup Blueprint Generator Agent — Built with{" "}
          <a href="https://www.ibm.com/products/watsonx-ai" target="_blank" rel="noreferrer">
            IBM Granite (watsonx.ai)
          </a>{" "}
          + RAG + FastAPI + React
        </div>
        <div style={{ marginTop: "0.25rem", color: "#334155" }}>
          Problem Statement #20 · IBM Startup Blueprint Generator
        </div>
      </footer>
    </div>
  );
}
