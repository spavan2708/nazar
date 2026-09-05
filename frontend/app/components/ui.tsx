"use client";

import { useId, useRef, useState, type ButtonHTMLAttributes, type HTMLAttributes, type ReactNode } from "react";

export function Icon({ name = "arrow", className = "" }: { name?: "arrow" | "eye" | "message" | "link" | "image" | "audio" | "plus"; className?: string }) {
  const paths = {
    arrow: <path d="M4 12h15m-6-6 6 6-6 6" />,
    eye: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>,
    message: <path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 3V6a2 2 0 0 1 2-2Zm2 5h10M7 13h6" />,
    link: <><path d="m10 13 4-4m-6 7-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 10a4 4 0 0 0 6 0l4-4a4 4 0 0 0-6-6l-1 1" transform="translate(1 -1) scale(.9)" /></>,
    image: <><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8" cy="8" r="1" /><path d="m3 17 6-6 4 4 3-3 5 5" /></>,
    audio: <><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11v1a7 7 0 0 0 14 0v-1m-7 8v3m-3 0h6" /></>,
    plus: <path d="M12 4v16M4 12h16" />,
  };
  return <svg className={`n-icon ${className}`} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
export function PrimaryButton({ className = "", children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className={`n-button n-button-primary ${className}`}>{children}</button>;
}
export function SecondaryButton({ className = "", children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className={`n-button n-button-secondary ${className}`}>{children}</button>;
}
export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`n-card ${className}`} />;
}
export function SectionHeading({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return <div className="section-heading">{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2>{children && <p className="section-copy">{children}</p>}</div>;
}
export function StatusPill({ children }: { children: ReactNode }) {
  return <span className="status-pill">{children}</span>;
}
export function RiskBadge({ level }: { level?: string | null }) {
  const normalized = level?.toLowerCase() ?? "";
  const labels: Record<string, string> = { low: "Low risk", medium: "Medium risk", high: "High risk", critical: "Critical risk" };
  return <span className={`risk-badge risk-${labels[normalized] ? normalized : "unknown"}`}>{labels[normalized] ?? "Risk unavailable"}</span>;
}
export function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return <div className={`n-notice ${error ? "n-notice-error" : ""}`} role={error ? "alert" : "status"}>{error && <strong>Unable to complete this check. </strong>}{children}</div>;
}
export function LoadingStatus({ children }: { children: ReactNode }) {
  return <p className="loading-status" role="status"><span className="spinner" aria-hidden="true" />{children}</p>;
}
export function ExpandablePanel({ title, children, className = "" }: { title: string; children: ReactNode; className?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return <div className={`expandable ${className}`}><button type="button" className="expandable-trigger" aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}><span>{title}</span><span aria-hidden="true">{open ? "−" : "+"}</span></button><div id={id} hidden={!open} className="expandable-content">{children}</div></div>;
}
export function SignalChips({ items, empty = "No explicit signals detected." }: { items?: string[] | null; empty?: string }) {
  return items?.length ? <ul className="chip-list">{items.map((item, index) => <li className="chip" key={`${item}-${index}`}>{readableLabel(item)}</li>)}</ul> : <p className="supporting muted">{empty}</p>;
}
export function readableLabel(value: string) {
  const label = value.toLowerCase().replaceAll("_", " ").replace(/\botp\b/g, "OTP").replace(/\burl\b/g, "URL").replace(/\bkyc\b/g, "KYC").replace(/\bupi\b/g, "UPI");
  return label.charAt(0).toUpperCase() + label.slice(1);
}
export type TabOption<T extends string> = { value: T; label: string; icon?: "message" | "link" | "image" | "audio" };
export function AnalyzerTabs<T extends string>({ id, label, options, value, onChange, disabled = false }: { id: string; label: string; options: TabOption<T>[]; value: T; onChange: (value: T) => void; disabled?: boolean }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  return <div role="tablist" aria-label={label} className="analyzer-tabs">{options.map((option, index) => <button key={option.value} ref={node => { refs.current[index] = node; }} id={`${id}-tab-${option.value}`} type="button" role="tab" aria-selected={value === option.value} aria-controls={`${id}-panel-${option.value}`} tabIndex={value === option.value ? 0 : -1} disabled={disabled} onClick={() => onChange(option.value)} onKeyDown={event => {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % options.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + options.length) % options.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = options.length - 1;
    else return;
    event.preventDefault(); onChange(options[next].value); refs.current[next]?.focus();
  }}>{option.icon && <Icon name={option.icon} />}<span>{option.label}</span></button>)}</div>;
}
export function NazarInputShell({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <div className="input-shell"><h3>{title}</h3><p className="supporting muted">{description}</p>{children}</div>;
}
export function FileDropzone({ id, label, help, accept, disabled, file, onSelect }: { id: string; label: string; help: string; accept: string; disabled?: boolean; file: File | null; onSelect: (file?: File) => void }) {
  const [dragging, setDragging] = useState(false);
  return <div className={`file-dropzone ${dragging && !disabled ? "is-dragging" : ""}`} onDragOver={event => { event.preventDefault(); if (!disabled) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); if (!disabled) onSelect(event.dataTransfer.files[0]); }}>
    <label htmlFor={id}>{label}</label><p id={`${id}-help`} className="caption muted">{help}</p>
    <input id={id} type="file" accept={accept} aria-describedby={`${id}-help`} disabled={disabled} onChange={event => { onSelect(event.target.files?.[0]); event.target.value = ""; }} />
    {file && <p className="selected-file">Selected: {file.name} · {(file.size / (1024 * 1024)).toFixed(2)} MiB</p>}
  </div>;
}
