"use client";

import { useEffect, useState } from "react";

type AnalysisResult = {
  score: number;
  risk_level: string;
  signals: string[];
  explanation: string;
  recommended_action: string;
};

export default function Home() {
  const [backendStatus, setBackendStatus] = useState<
    "checking" | "online" | "error" | "network-error"
  >("checking");
  const [text, setText] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState("");

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

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsAnalyzing(true);
    setAnalysis(null);
    setAnalysisError("");

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/analyze/text`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        },
      );

      if (!response.ok) {
        throw new Error(`Analysis request failed (${response.status})`);
      }

      setAnalysis((await response.json()) as AnalysisResult);
    } catch (error) {
      setAnalysisError(
        error instanceof Error ? error.message : "Could not analyze the text.",
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

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

        <form
          className="mt-12 border-t border-slate-800 pt-8 text-left"
          onSubmit={handleSubmit}
        >
          <h2 className="text-xl font-semibold">Check something suspicious</h2>
          <textarea
            className="mt-4 min-h-32 w-full resize-y rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-white outline-none placeholder:text-slate-500 focus:border-emerald-400"
            placeholder="Paste a suspicious message, email, or caller transcript..."
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <div className="mt-3 flex items-center gap-3">
            <button
              type="submit"
              disabled={!text.trim() || isAnalyzing}
              className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isAnalyzing ? "Analyzing..." : "Check for scam signs"}
            </button>
          </div>

          {analysisError && (
            <p className="mt-4 text-sm text-red-400" role="alert">
              {analysisError}
            </p>
          )}

          {analysis && (
            <div className="mt-6 rounded-lg border border-slate-700 bg-slate-900 p-5">
              <div className="flex gap-6">
                <p>
                  <span className="block text-xs uppercase text-slate-500">Risk score</span>
                  <span className="text-2xl font-semibold">{analysis.score}</span>
                </p>
                <p>
                  <span className="block text-xs uppercase text-slate-500">Risk level</span>
                  <span className="text-2xl font-semibold capitalize">{analysis.risk_level}</span>
                </p>
              </div>
              <h3 className="mt-5 font-semibold">Detected signals</h3>
              {analysis.signals.length > 0 ? (
                <ul className="mt-2 list-inside list-disc text-sm text-slate-300">
                  {analysis.signals.map((signal) => (
                    <li key={signal}>{signal}</li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-slate-300">None detected</p>
              )}
              <h3 className="mt-5 font-semibold">Explanation</h3>
              <p className="mt-2 text-sm leading-6 text-slate-300">{analysis.explanation}</p>
              <h3 className="mt-5 font-semibold">Recommended action</h3>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                {analysis.recommended_action}
              </p>
            </div>
          )}
        </form>
      </section>
    </main>
  );
}
