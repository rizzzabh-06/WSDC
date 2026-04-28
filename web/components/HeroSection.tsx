"use client";

import { useEffect, useRef } from "react";

export default function HeroSection() {
  const heroRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const hero = heroRef.current;
    if (!hero) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = hero.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      hero.style.setProperty("--mouse-x", `${x}%`);
      hero.style.setProperty("--mouse-y", `${y}%`);
    };

    hero.addEventListener("mousemove", handleMouseMove);
    return () => hero.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <section
      id="hero"
      ref={heroRef}
      className="relative min-h-screen flex items-center justify-center overflow-hidden"
      style={
        {
          "--mouse-x": "50%",
          "--mouse-y": "50%",
        } as React.CSSProperties
      }
    >
      {/* Animated gradient background */}
      <div className="absolute inset-0 animated-gradient" />

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 grid-pattern" />

      {/* Radial glow following mouse */}
      <div
        className="absolute inset-0 opacity-40 pointer-events-none"
        style={{
          background:
            "radial-gradient(600px circle at var(--mouse-x) var(--mouse-y), rgba(99, 102, 241, 0.08), transparent 60%)",
        }}
      />

      {/* Floating orbs */}
      <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-accent/5 rounded-full blur-3xl" style={{ animation: "float 8s ease-in-out infinite" }} />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl" style={{ animation: "float 10s ease-in-out infinite 2s" }} />
      <div className="absolute top-1/2 right-1/3 w-48 h-48 bg-indigo-400/5 rounded-full blur-3xl" style={{ animation: "float 6s ease-in-out infinite 4s" }} />

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Badge */}
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent/20 bg-accent/5 text-sm text-accent-glow mb-8"
          style={{ animation: "fade-in 0.6s ease-out both" }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
          AI-Powered Security for Web3 Development
        </div>

        {/* Title */}
        <h1
          className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1] mb-6"
          style={{ animation: "fade-in 0.8s ease-out 0.2s both" }}
        >
          <span className="text-text-primary">Web3 Secure</span>
          <br />
          <span className="gradient-text-hero">Development Co-Pilot</span>
        </h1>

        {/* Subtitle */}
        <p
          className="max-w-2xl mx-auto text-lg sm:text-xl text-text-secondary leading-relaxed mb-10"
          style={{ animation: "fade-in 0.8s ease-out 0.4s both" }}
        >
          AI-powered security review for Web3 & backend systems —{" "}
          <span className="text-text-primary font-medium">
            catch vulnerabilities before they ship.
          </span>
        </p>

        {/* CTAs */}
        <div
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
          style={{ animation: "fade-in 0.8s ease-out 0.6s both" }}
        >
          <a
            href="#demo"
            className="group px-8 py-3.5 rounded-xl bg-accent hover:bg-accent-glow text-white font-semibold text-base transition-all duration-300 hover:shadow-xl hover:shadow-accent/25 hover:-translate-y-0.5 flex items-center gap-2"
          >
            View Demo
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="group-hover:translate-x-0.5 transition-transform"
            >
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
          <a
            href="#architecture"
            className="px-8 py-3.5 rounded-xl border border-border hover:border-accent/40 text-text-secondary hover:text-text-primary font-semibold text-base transition-all duration-300 hover:bg-white/5"
          >
            How it Works
          </a>
        </div>

        {/* Trust signals */}
        <div
          className="mt-16 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-text-muted"
          style={{ animation: "fade-in 0.8s ease-out 0.8s both" }}
        >
          <div className="flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-glow"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Shift-Left Security
          </div>
          <div className="flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-glow"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            Developer-First
          </div>
          <div className="flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-glow"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
            AI-Assisted Coding
          </div>
        </div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent" />
    </section>
  );
}
