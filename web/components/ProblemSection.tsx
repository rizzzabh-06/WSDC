"use client";

const problems = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-red">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
    ),
    title: "High False Positives",
    description: "SAST tools flag everything without context. Developers drown in noise, stop reading alerts, and real vulnerabilities slip through.",
    stat: "60-80%",
    statLabel: "false positive rate in traditional scanners",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-amber">
        <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
      </svg>
    ),
    title: "No Context Awareness",
    description: "Generic rules can't understand your protocol's trust model, economic invariants, or governance structure. Same rule, every codebase.",
    stat: "Zero",
    statLabel: "protocol-specific intelligence",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-amber">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
    ),
    title: "No Web3 Intelligence",
    description: "Traditional tools miss DeFi-specific bugs — reentrancy, flash loan attacks, oracle manipulation, governance exploits — entirely.",
    stat: "$3.8B",
    statLabel: "lost to DeFi exploits in 2023",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-red">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    ),
    title: "Security Comes Too Late",
    description: "Bugs found in audits cost 10× more to fix than in PRs. By the time an auditor sees your code, months of insecure patterns have accumulated.",
    stat: "10×",
    statLabel: "higher cost to fix post-audit",
  },
];

export default function ProblemSection() {
  return (
    <section id="problem" className="section-padding relative">
      <div className="absolute inset-0 grid-pattern opacity-50" />
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent-red/20 bg-accent-red/5 text-xs font-medium text-accent-red mb-4">
            THE PROBLEM
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4">
            Web3 Security is Fundamentally Broken
          </h2>
          <p className="max-w-2xl mx-auto text-text-secondary">
            Bugs are found too late, tools are too noisy, and security knowledge doesn&apos;t compound. The developer experience is broken.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-6">
          {problems.map((p, i) => (
            <div
              key={i}
              className="glass-card rounded-2xl p-6 group"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-accent-red/5 border border-accent-red/10 flex items-center justify-center shrink-0 group-hover:bg-accent-red/10 transition-colors">
                  {p.icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-text-primary mb-2">{p.title}</h3>
                  <p className="text-sm text-text-secondary leading-relaxed mb-4">{p.description}</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-accent-red">{p.stat}</span>
                    <span className="text-xs text-text-muted">{p.statLabel}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
