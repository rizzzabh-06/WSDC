"use client";

import { useState, useCallback } from "react";

const SOLIDITY_CODE = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract VaultProtocol {
    mapping(address => uint256) public balances;
    mapping(address => uint256) public lastDeposit;
    uint256 public totalDeposits;

    event Deposit(address indexed user, uint256 amount);
    event Withdrawal(address indexed user, uint256 amount);

    function deposit() external payable {
        require(msg.value > 0, "Must deposit > 0");
        balances[msg.sender] += msg.value;
        lastDeposit[msg.sender] = block.timestamp;
        totalDeposits += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");

        // ⚠️ External call BEFORE state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        // State updated AFTER external call
        balances[msg.sender] -= amount;
        totalDeposits -= amount;

        emit Withdrawal(msg.sender, amount);
    }

    function getBalance() external view returns (uint256) {
        return balances[msg.sender];
    }
}`;

const FIXED_CODE = `    function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient");

        // ✅ State updated BEFORE external call (CEI pattern)
        balances[msg.sender] -= amount;
        totalDeposits -= amount;

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        emit Withdrawal(msg.sender, amount);
    }`;

const vulnLines = [25, 26, 27, 28, 29, 30, 31, 32, 33];

interface Finding {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium";
  location: string;
  lines: string;
  explanation: string;
  exploit: string;
  owasp: string;
}

const findings: Finding[] = [
  {
    id: "WSDC-001",
    title: "Reentrancy Vulnerability — CEI Violation",
    severity: "critical",
    location: "VaultProtocol.sol → withdraw()",
    lines: "Lines 25-33",
    explanation:
      "The withdraw() function sends ETH to msg.sender via a low-level call before updating the sender's balance. A malicious contract can implement a fallback function that re-enters withdraw() before balances[msg.sender] is decremented, draining the entire vault.",
    exploit:
      "An attacker deploys a contract that calls withdraw(), and in its receive() function, calls withdraw() again. Since the balance hasn't been decremented yet, each re-entrant call passes the require check — repeating until the vault is empty.",
    owasp: "SWC-107 · SC-01 (Reentrancy)",
  },
  {
    id: "WSDC-002",
    title: "Missing ReentrancyGuard Usage",
    severity: "high",
    location: "VaultProtocol.sol → contract",
    lines: "Line 4, 25",
    explanation:
      "The contract imports OpenZeppelin's ReentrancyGuard but never inherits from it or applies the nonReentrant modifier to state-changing external functions. This is a common oversight — the import alone provides no protection.",
    exploit: "N/A — this is a defense gap that enables WSDC-001.",
    owasp: "SWC-107 · Best Practice",
  },
];

const severityConfig = {
  critical: { color: "bg-accent-red", text: "text-accent-red", label: "CRITICAL", border: "border-accent-red/30" },
  high: { color: "bg-accent-amber", text: "text-accent-amber", label: "HIGH", border: "border-accent-amber/30" },
  medium: { color: "bg-yellow-500", text: "text-yellow-500", label: "MEDIUM", border: "border-yellow-500/30" },
};

function SeverityBadge({ severity }: { severity: "critical" | "high" | "medium" }) {
  const cfg = severityConfig[severity];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold ${cfg.text} bg-opacity-10 border ${cfg.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.color}`} />
      {cfg.label}
    </span>
  );
}

interface Token {
  text: string;
  className?: string;
}

const KEYWORDS = new Set([
  "pragma", "solidity", "import", "contract", "function", "mapping",
  "address", "uint256", "bool", "external", "payable", "public",
  "view", "returns", "require", "emit", "event", "indexed",
]);

const BUILTINS = new Set(["msg.sender", "msg.value", "block.timestamp"]);

function tokenizeLine(line: string): Token[] {
  // Handle comments
  const commentIdx = line.indexOf("//");
  if (commentIdx === 0) return [{ text: line, className: "token-comment" }];

  const tokens: Token[] = [];
  let codePart = line;
  let commentPart = "";

  if (commentIdx > 0) {
    codePart = line.slice(0, commentIdx);
    commentPart = line.slice(commentIdx);
  }

  // Tokenize the code part
  let i = 0;
  let buffer = "";

  const flushBuffer = () => {
    if (buffer) {
      tokens.push({ text: buffer });
      buffer = "";
    }
  };

  while (i < codePart.length) {
    // Check for builtins
    let foundBuiltin = false;
    for (const b of BUILTINS) {
      if (codePart.startsWith(b, i)) {
        flushBuffer();
        tokens.push({ text: b, className: "token-variable" });
        i += b.length;
        foundBuiltin = true;
        break;
      }
    }
    if (foundBuiltin) continue;

    // Check for strings
    if (codePart[i] === '"') {
      flushBuffer();
      let j = i + 1;
      while (j < codePart.length && codePart[j] !== '"') j++;
      const str = codePart.slice(i, j + 1);
      tokens.push({ text: str, className: "token-string" });
      i = j + 1;
      continue;
    }

    // Check for word boundaries (keywords and numbers)
    if (/[a-zA-Z_]/.test(codePart[i])) {
      flushBuffer();
      let j = i;
      while (j < codePart.length && /[a-zA-Z0-9_]/.test(codePart[j])) j++;
      const word = codePart.slice(i, j);
      if (KEYWORDS.has(word)) {
        tokens.push({ text: word, className: "token-keyword" });
      } else {
        tokens.push({ text: word });
      }
      i = j;
      continue;
    }

    // Check for numbers
    if (/\d/.test(codePart[i])) {
      flushBuffer();
      let j = i;
      while (j < codePart.length && /[0-9.]/.test(codePart[j])) j++;
      tokens.push({ text: codePart.slice(i, j), className: "token-number" });
      i = j;
      continue;
    }

    buffer += codePart[i];
    i++;
  }
  flushBuffer();

  // Add comment part
  if (commentPart) {
    tokens.push({ text: commentPart, className: "token-comment" });
  }

  return tokens;
}

function CodeLine({ num, code, isVuln, scanned }: { num: number; code: string; isVuln: boolean; scanned: boolean }) {
  const tokens = tokenizeLine(code);
  return (
    <div className={`flex ${isVuln && scanned ? "vuln-line" : ""}`}>
      <span className="w-10 shrink-0 text-right pr-4 select-none text-text-muted/50 text-xs leading-[1.7]">
        {num}
      </span>
      <span className="flex-1 whitespace-pre leading-[1.7]">
        {tokens.map((t, i) => (
          t.className
            ? <span key={i} className={t.className}>{t.text}</span>
            : <span key={i}>{t.text}</span>
        ))}
      </span>
    </div>
  );
}

export default function DemoSection() {
  const [scanState, setScanState] = useState<"idle" | "scanning" | "done">("idle");
  const [progress, setProgress] = useState(0);
  const [showFix, setShowFix] = useState(false);
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);

  const runScan = useCallback(() => {
    if (scanState === "scanning") return;
    setScanState("scanning");
    setProgress(0);
    setShowFix(false);
    setExpandedFinding(null);

    const duration = 2800;
    const steps = 60;
    const interval = duration / steps;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      const p = Math.min(100, Math.round((step / steps) * 100));
      setProgress(p);
      if (step >= steps) {
        clearInterval(timer);
        setScanState("done");
        setExpandedFinding("WSDC-001");
      }
    }, interval);
  }, [scanState]);

  const reset = () => {
    setScanState("idle");
    setProgress(0);
    setShowFix(false);
    setExpandedFinding(null);
  };

  const codeLines = SOLIDITY_CODE.split("\n");

  return (
    <section id="demo" className="section-padding relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/20 bg-accent/5 text-xs font-medium text-accent-glow mb-4">
            INTERACTIVE DEMO
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4">
            See WSDC in Action
          </h2>
          <p className="max-w-2xl mx-auto text-text-secondary">
            Click &quot;Run Security Scan&quot; to analyze a vulnerable Solidity smart contract and see how WSDC identifies issues with context-aware explanations.
          </p>
        </div>

        {/* Demo panel */}
        <div className="grid lg:grid-cols-2 gap-0 rounded-2xl overflow-hidden border border-border glass-card" style={{ animation: "none" }}>
          {/* Code Editor Panel */}
          <div className="bg-[#0d1117] border-r border-border">
            {/* Editor header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-[#0d1117]">
              <div className="flex items-center gap-3">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-accent-red/70" />
                  <div className="w-3 h-3 rounded-full bg-accent-amber/70" />
                  <div className="w-3 h-3 rounded-full bg-accent-green/70" />
                </div>
                <span className="text-xs text-text-muted font-mono">VaultProtocol.sol</span>
              </div>
              <div className="flex items-center gap-2">
                {scanState === "done" && (
                  <span className="text-xs text-accent-red flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    2 issues found
                  </span>
                )}
              </div>
            </div>
            {/* Code content */}
            <div className="code-editor p-4 overflow-x-auto max-h-[520px] overflow-y-auto">
              {codeLines.map((line, i) => (
                <CodeLine
                  key={i}
                  num={i + 1}
                  code={line}
                  isVuln={vulnLines.includes(i + 1)}
                  scanned={scanState === "done"}
                />
              ))}
            </div>
          </div>

          {/* Results Panel */}
          <div className="bg-bg-card flex flex-col">
            {/* Results header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <span className="text-sm font-semibold text-text-primary">Security Analysis</span>
              {scanState === "done" && (
                <button onClick={reset} className="text-xs text-text-muted hover:text-text-secondary transition-colors">
                  Reset
                </button>
              )}
            </div>

            <div className="flex-1 p-4 overflow-y-auto max-h-[520px]">
              {/* Idle state */}
              {scanState === "idle" && (
                <div className="flex flex-col items-center justify-center h-full text-center py-12">
                  <div className="w-16 h-16 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-4">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-glow">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-text-primary mb-2">Ready to Scan</h3>
                  <p className="text-sm text-text-secondary mb-6 max-w-xs">
                    Analyze the smart contract for security vulnerabilities using WSDC&apos;s AI engine.
                  </p>
                  <button
                    onClick={runScan}
                    className="px-6 py-3 rounded-xl bg-accent hover:bg-accent-glow text-white font-semibold transition-all duration-300 hover:shadow-lg hover:shadow-accent/25 flex items-center gap-2"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    Run Security Scan
                  </button>
                </div>
              )}

              {/* Scanning state */}
              {scanState === "scanning" && (
                <div className="flex flex-col items-center justify-center h-full text-center py-12">
                  <div className="w-16 h-16 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-4 animate-pulse">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-glow animate-spin" style={{ animationDuration: "3s" }}>
                      <circle cx="12" cy="12" r="10" strokeDasharray="31.4" strokeDashoffset="10"/>
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-text-primary mb-2">Scanning...</h3>
                  <p className="text-sm text-text-secondary mb-6">Analyzing AST, checking patterns, running AI context engine</p>
                  {/* Progress bar */}
                  <div className="w-full max-w-xs">
                    <div className="flex justify-between text-xs text-text-muted mb-2">
                      <span>{progress < 30 ? "Parsing AST..." : progress < 60 ? "Static analysis..." : progress < 90 ? "AI context layer..." : "Generating report..."}</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="h-1.5 bg-border rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-accent to-accent-glow rounded-full transition-all duration-200"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Results state */}
              {scanState === "done" && (
                <div className="space-y-3" style={{ animation: "fade-in 0.4s ease-out" }}>
                  {/* Summary */}
                  <div className="flex items-center gap-3 p-3 rounded-xl bg-accent-red/5 border border-accent-red/20">
                    <div className="w-8 h-8 rounded-lg bg-accent-red/10 flex items-center justify-center shrink-0">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-red"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-text-primary">2 vulnerabilities detected</p>
                      <p className="text-xs text-text-secondary">1 Critical · 1 High · Scan completed in 2.8s</p>
                    </div>
                  </div>

                  {/* Findings */}
                  {findings.map((f) => (
                    <div key={f.id} className={`rounded-xl border transition-all duration-300 ${expandedFinding === f.id ? `${severityConfig[f.severity].border} bg-white/[0.02]` : "border-border hover:border-border"}`}>
                      <button
                        onClick={() => setExpandedFinding(expandedFinding === f.id ? null : f.id)}
                        className="w-full p-4 text-left flex items-start gap-3"
                      >
                        <div className="shrink-0 mt-0.5">
                          <SeverityBadge severity={f.severity} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-text-primary">{f.title}</p>
                          <p className="text-xs text-text-muted mt-1">{f.location} · {f.lines}</p>
                        </div>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`text-text-muted shrink-0 transition-transform ${expandedFinding === f.id ? "rotate-180" : ""}`}>
                          <polyline points="6 9 12 15 18 9"/>
                        </svg>
                      </button>

                      {expandedFinding === f.id && (
                        <div className="px-4 pb-4 space-y-3" style={{ animation: "fade-in 0.3s ease-out" }}>
                          <div>
                            <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1">Explanation</p>
                            <p className="text-sm text-text-secondary leading-relaxed">{f.explanation}</p>
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1">Exploit Scenario</p>
                            <p className="text-sm text-text-secondary leading-relaxed">{f.exploit}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-text-muted">OWASP:</span>
                            <span className="text-xs px-2 py-0.5 rounded bg-accent/10 text-accent-glow border border-accent/20">{f.owasp}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Fix suggestion */}
                  <div className="pt-2">
                    <button
                      onClick={() => setShowFix(!showFix)}
                      className="w-full px-4 py-3 rounded-xl border border-accent-green/20 bg-accent-green/5 text-sm font-semibold text-accent-green hover:bg-accent-green/10 transition-colors flex items-center justify-center gap-2"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                      {showFix ? "Hide" : "View"} Fix Suggestion
                    </button>
                  </div>

                  {showFix && (
                    <div className="rounded-xl border border-accent-green/20 overflow-hidden" style={{ animation: "fade-in 0.3s ease-out" }}>
                      <div className="px-4 py-2 bg-accent-green/5 border-b border-accent-green/20 flex items-center gap-2">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-green"><polyline points="20 6 9 17 4 12"/></svg>
                        <span className="text-xs font-semibold text-accent-green">Suggested Fix — Apply CEI Pattern + nonReentrant</span>
                      </div>
                      <pre className="code-editor p-4 bg-[#0d1117] text-xs overflow-x-auto">
                        <code>{FIXED_CODE}</code>
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
