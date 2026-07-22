"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { type AccountSession, getSessions, revokeSession } from "@/lib/auth";

import styles from "./ActiveSessions.module.css";

function describeDevice(userAgent: string): string {
  if (!userAgent) return "Unknown device";
  const browser = /Edg\//.test(userAgent)
    ? "Edge"
    : /Chrome\//.test(userAgent)
      ? "Chrome"
      : /Firefox\//.test(userAgent)
        ? "Firefox"
        : /Safari\//.test(userAgent) && !/Chrome\//.test(userAgent)
          ? "Safari"
          : "a browser";
  const os = /Windows/.test(userAgent)
    ? "Windows"
    : /Mac OS X/.test(userAgent)
      ? "macOS"
      : /Android/.test(userAgent)
        ? "Android"
        : /iPhone|iPad/.test(userAgent)
          ? "iOS"
          : /Linux/.test(userAgent)
            ? "Linux"
            : "an unknown OS";
  return `${browser} on ${os}`;
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export function ActiveSessions() {
  const [sessions, setSessions] = useState<AccountSession[] | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getSessions()
      .then(setSessions)
      .catch(() => setSessions([]));
  }, []);

  async function onRevoke(id: string) {
    setError("");
    setBusyId(id);
    try {
      await revokeSession(id);
      setSessions((list) => list?.filter((s) => s.id !== id) ?? null);
    } catch {
      setError("Could not sign out that device. Please try again.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className={styles.card}>
      <h2 className={styles.title}>Active Sessions</h2>
      <p className={styles.sub}>Devices currently signed in to your account.</p>

      {error && <p className={styles.error}>{error}</p>}

      {sessions === null ? (
        <p className={styles.loading}>Loading sessions…</p>
      ) : (
        <div className={styles.list}>
          {sessions.map((session) => (
            <div key={session.id} className={styles.row}>
              <Icon name="windows" size={18} className={styles.icon} />
              <div className={styles.info}>
                <span className={styles.device}>
                  {describeDevice(session.user_agent)}
                  {session.is_current && <Pill tone="success">This device</Pill>}
                </span>
                <span className={styles.meta}>
                  {session.ip_address || "Unknown IP"} · Expires {formatDateTime(session.expires_at)}
                </span>
              </div>
              {!session.is_current && (
                <button
                  className={styles.revokeBtn}
                  disabled={busyId === session.id}
                  onClick={() => onRevoke(session.id)}
                >
                  {busyId === session.id ? "Signing out…" : "Sign out"}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
