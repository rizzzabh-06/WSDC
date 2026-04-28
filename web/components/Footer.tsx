export default function Footer() {
  return (
    <footer className="border-t border-border bg-bg-surface">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Logo + tagline */}
          <div className="flex flex-col items-center md:items-start gap-2">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-accent/20 border border-accent/30 flex items-center justify-center">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-accent-glow">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
              </div>
              <span className="text-base font-bold text-text-primary tracking-tight">WSDC</span>
            </div>
            <p className="text-sm text-text-muted">Built for secure-by-design development</p>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6">
            <a href="#" className="text-sm text-text-muted hover:text-text-secondary transition-colors">GitHub</a>
            <a href="#" className="text-sm text-text-muted hover:text-text-secondary transition-colors">Documentation</a>
            <a href="#" className="text-sm text-text-muted hover:text-text-secondary transition-colors">Contact</a>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-border/50 text-center">
          <p className="text-xs text-text-muted">
            © {new Date().getFullYear()} Web3 Secure Development Co-Pilot. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
