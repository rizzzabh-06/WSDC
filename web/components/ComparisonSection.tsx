"use client";

const rows = [
  { feature: "False Positive Rate", sast: "High (60-80%)", wsdc: "Low (<15%)", sastBad: true, wsdcGood: true },
  { feature: "Context Awareness", sast: "None — rule-based", wsdc: "Protocol-aware AI", sastBad: true, wsdcGood: true },
  { feature: "Web3 / DeFi Support", sast: "Limited bolt-on", wsdc: "Native, built-in", sastBad: false, wsdcGood: true },
  { feature: "Developer Feedback", sast: "Generic error codes", wsdc: "Actionable explanations", sastBad: true, wsdcGood: true },
  { feature: "Workflow Integration", sast: "External dashboard", wsdc: "Embedded in PR", sastBad: true, wsdcGood: true },
  { feature: "Learning Feedback", sast: "None", wsdc: "Educational + exploit scenarios", sastBad: true, wsdcGood: true },
  { feature: "Setup Time", sast: "Days / weeks", wsdc: "5 minutes", sastBad: false, wsdcGood: true },
  { feature: "Review Speed", sast: "Minutes to hours", wsdc: "15-30 seconds", sastBad: false, wsdcGood: true },
];

export default function ComparisonSection() {
  return (
    <section id="compare" className="section-padding relative">
      <div className="absolute inset-0 grid-pattern opacity-30" />
      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/20 bg-accent/5 text-xs font-medium text-accent-glow mb-4">
            COMPARISON
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4">
            WSDC vs Traditional SAST
          </h2>
          <p className="max-w-2xl mx-auto text-text-secondary">
            A side-by-side comparison showing why context-aware AI outperforms rule-based static analysis.
          </p>
        </div>

        <div className="glass-card rounded-2xl overflow-hidden" style={{ animation: "none" }}>
          {/* Table header */}
          <div className="grid grid-cols-3 border-b border-border">
            <div className="px-6 py-4">
              <span className="text-sm font-semibold text-text-muted">Feature</span>
            </div>
            <div className="px-6 py-4 border-l border-border">
              <span className="text-sm font-semibold text-text-muted">Traditional SAST</span>
            </div>
            <div className="px-6 py-4 border-l border-accent/20 bg-accent/[0.03]">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded bg-accent/20 flex items-center justify-center">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" className="text-accent-glow">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                  </svg>
                </div>
                <span className="text-sm font-semibold text-accent-glow">WSDC</span>
              </div>
            </div>
          </div>

          {/* Table rows */}
          {rows.map((row, i) => (
            <div
              key={i}
              className={`grid grid-cols-3 ${i !== rows.length - 1 ? "border-b border-border/50" : ""} hover:bg-white/[0.01] transition-colors`}
            >
              <div className="px-6 py-4 flex items-center">
                <span className="text-sm font-medium text-text-primary">{row.feature}</span>
              </div>
              <div className="px-6 py-4 border-l border-border flex items-center gap-2">
                <span className={`text-xs ${row.sastBad ? "text-accent-red" : "text-accent-amber"}`}>
                  {row.sastBad ? "●" : "◐"}
                </span>
                <span className="text-sm text-text-secondary">{row.sast}</span>
              </div>
              <div className="px-6 py-4 border-l border-accent/20 bg-accent/[0.03] flex items-center gap-2">
                <span className="text-xs text-accent-green">●</span>
                <span className="text-sm text-text-primary font-medium">{row.wsdc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
