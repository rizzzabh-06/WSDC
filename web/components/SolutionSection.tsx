"use client";

const solutions = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-glow">
        <circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
      </svg>
    ),
    title: "Context-Aware AI Analysis",
    description: "Understands your protocol's architecture, trust boundaries, and economic invariants — not just syntax patterns.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-glow">
        <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
      </svg>
    ),
    title: "Smart Contract + Backend",
    description: "Native support for Solidity, Vyper, Rust, and backend APIs. One tool for your entire stack.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-glow">
        <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
      </svg>
    ),
    title: "PR-Based Workflow",
    description: "Reviews happen where developers already work — inline PR comments, not a separate dashboard to check.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-glow">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
    ),
    title: "Real-Time Feedback",
    description: "Results in 15-30 seconds per PR. Fast enough for background review without blocking developer flow.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-glow">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
      </svg>
    ),
    title: "Educational Explanations",
    description: "Teaches why a pattern is insecure with protocol-specific exploit scenarios. Developers level up — same bugs don't repeat.",
  },
];

export default function SolutionSection() {
  return (
    <section id="solution" className="section-padding relative">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent-green/20 bg-accent-green/5 text-xs font-medium text-accent-green mb-4">
            THE SOLUTION
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4">
            How WSDC <span className="gradient-text">Solves This</span>
          </h2>
          <p className="max-w-2xl mx-auto text-text-secondary">
            A developer-first security co-pilot that integrates into your existing workflow and gets smarter with every PR.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {solutions.map((s, i) => (
            <div
              key={i}
              className={`glass-card rounded-2xl p-6 group ${i === 4 ? "sm:col-span-2 lg:col-span-1" : ""}`}
            >
              <div className="w-12 h-12 rounded-xl bg-accent/5 border border-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/10 group-hover:border-accent/20 transition-colors">
                {s.icon}
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">{s.title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">{s.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
