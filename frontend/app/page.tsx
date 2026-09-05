"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [backendStatus, setBackendStatus] = useState<
    "checking" | "online" | "error" | "network-error"
  >("checking");

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/health`,
        );
        if (!response.ok) {
          setBackendStatus("error");
          return;
        }

        const data = await response.json();
        setBackendStatus(data.status === "healthy" ? "online" : "error");
      } catch {
        setBackendStatus("network-error");
      }
    };

    checkBackend();
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
      <section className="max-w-2xl text-center">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.3em] text-emerald-400">
          Nazar
        </p>
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
          One warning before one wrong click.
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-base leading-7 text-slate-300 sm:text-lg">
          Nazar detects suspicious messages, calls, links, apps, and payment
          requests.
        </p>
        <p className="mt-8 text-sm text-slate-400" aria-live="polite">
          <span
            className={`mr-2 inline-block size-2 rounded-full ${
              backendStatus === "online"
                ? "bg-emerald-400"
                : backendStatus === "checking"
                  ? "bg-slate-500"
                  : "bg-amber-400"
            }`}
          />
          {backendStatus === "checking"
            ? "Checking backend..."
            : backendStatus === "online"
              ? "Backend online"
              : backendStatus === "error"
                ? "Backend reachable, but returned an error"
                : "Network or CORS failure"}
        </p>

        <div className="mt-12 border-t border-slate-800 pt-8 text-left">
          <h2 className="text-xl font-semibold">Check something suspicious</h2>
          <textarea
            className="mt-4 min-h-32 w-full resize-y rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-white outline-none placeholder:text-slate-500 focus:border-emerald-400"
            placeholder="Paste a suspicious message, email, or caller transcript..."
          />
          <div className="mt-3 flex items-center gap-3">
            <button
              type="button"
              disabled
              className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 opacity-50"
            >
              Check for scam signs
            </button>
            <span className="text-sm text-slate-500">Analysis coming next</span>
          </div>
        </div>
      </section>
    </main>
  );
}
