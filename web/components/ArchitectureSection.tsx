"use client";

const steps = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
    ),
    label: "Developer",
    description: "Pushes code & opens a PR",
    color: "text-text-primary",
    bg: "bg-white/5",
    border: "border-border",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>
    ),
    label: "PR Created",
    description: "Webhook triggers WSDC",
    color: "text-text-primary",
    bg: "bg-white/5",
    border: "border-border",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
    ),
    label: "WSDC AI Scan",
    description: "AST diff + static analysis + AI context",
    color: "text-accent-glow",
    bg: "bg-accent/10",
    border: "border-accent/30",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
    ),
    label: "Feedback Posted",
    description: "Inline PR comments with explanations",
    color: "text-accent-glow",
    bg: "bg-accent/10",
    border: "border-accent/30",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
    ),
    label: "Fix Applied",
    description: "One-click code suggestions",
    color: "text-text-primary",
    bg: "bg-white/5",
    border: "border-border",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polyline points="20 6 9 17 4 12"/></svg>
    ),
    label: "Merge ✓",
    description: "Ship with confidence",
    color: "text-accent-green",
    bg: "bg-accent-green/10",
    border: "border-accent-green/30",
  },
];

export default function ArchitectureSection() {
  return (
    <section id="architecture" className="section-padding relative overflow-hidden">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/20 bg-accent/5 text-xs font-medium text-accent-glow mb-4">
            WORKFLOW
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4">
            How It Works
          </h2>
          <p className="max-w-2xl mx-auto text-text-secondary">
            WSDC integrates seamlessly into your existing PR workflow — no context switching required.
          </p>
        </div>

        {/* Desktop flow */}
        <div className="hidden lg:flex items-start justify-between relative">
          {/* Connection line */}
          <div className="absolute top-10 left-[8%] right-[8%] h-0.5 bg-gradient-to-r from-border via-accent/30 to-accent-green/30" />

          {steps.map((step, i) => (
            <div key={i} className="relative flex flex-col items-center w-1/6 px-2">
              {/* Node */}
              <div className={`relative z-10 w-[52px] h-[52px] rounded-xl ${step.bg} border ${step.border} flex items-center justify-center mb-4 ${step.color}`}>
                {step.icon}
              </div>
              <h3 className={`text-sm font-semibold ${step.color} text-center mb-1`}>{step.label}</h3>
              <p className="text-xs text-text-muted text-center leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>

        {/* Mobile flow — vertical */}
        <div className="lg:hidden space-y-0">
          {steps.map((step, i) => (
            <div key={i} className="relative flex items-start gap-4 pb-8 last:pb-0">
              {/* Vertical line */}
              {i < steps.length - 1 && (
                <div className="absolute left-[25px] top-[52px] w-0.5 h-[calc(100%-52px)] bg-border" />
              )}
              <div className={`relative z-10 w-[50px] h-[50px] rounded-xl ${step.bg} border ${step.border} flex items-center justify-center shrink-0 ${step.color}`}>
                {step.icon}
              </div>
              <div className="pt-2">
                <h3 className={`text-sm font-semibold ${step.color} mb-1`}>{step.label}</h3>
                <p className="text-xs text-text-muted leading-relaxed">{step.description}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Speed callout */}
        <div className="mt-12 flex justify-center">
          <div className="inline-flex items-center gap-3 px-6 py-3 rounded-full glass-card" style={{ animation: "none" }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-glow">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
            <span className="text-sm text-text-secondary">
              Total review time: <span className="font-semibold text-accent-glow">15–30 seconds</span> per PR
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
