"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { AccountApiError, createSupportTicket, getSupportTickets, type SupportTicketSummary } from "@/lib/accountApi";

import styles from "./SupportTickets.module.css";

function statusTone(status: SupportTicketSummary["status"]): "success" | "warning" | "neutral" {
  if (status === "resolved") return "success";
  if (status === "awaiting_customer") return "neutral";
  return "warning";
}

function statusLabel(status: SupportTicketSummary["status"]): string {
  if (status === "awaiting_customer") return "Awaiting you";
  return status[0].toUpperCase() + status.slice(1);
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function SupportTicketsList() {
  const [tickets, setTickets] = useState<SupportTicketSummary[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getSupportTickets()
      .then(setTickets)
      .catch(() => setTickets([]));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!subject.trim() || !body.trim()) return;
    setError("");
    setSubmitting(true);
    try {
      const ticket = await createSupportTicket(subject.trim(), body.trim());
      setTickets((list) => [
        { id: ticket.id, subject: ticket.subject, status: ticket.status, message_count: 1, created_at: ticket.created_at, updated_at: ticket.updated_at },
        ...(list ?? []),
      ]);
      setSubject("");
      setBody("");
      setShowForm(false);
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Could not create the ticket.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.newCard}>
        {!showForm ? (
          <button className={styles.newBtn} onClick={() => setShowForm(true)}>
            <Icon name="plus" size={16} /> New Ticket
          </button>
        ) : (
          <form className={styles.form} onSubmit={onSubmit}>
            <input
              className={styles.input}
              placeholder="Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
              maxLength={200}
            />
            <textarea
              className={styles.textarea}
              placeholder="Describe your issue…"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
              rows={4}
            />
            {error && <p className={styles.error}>{error}</p>}
            <div className={styles.formActions}>
              <button type="submit" className={styles.submitBtn} disabled={submitting}>
                {submitting ? "Submitting…" : "Submit Ticket"}
              </button>
              <button type="button" className={styles.cancelBtn} onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      {tickets === null ? (
        <p className={styles.loading}>Loading your tickets…</p>
      ) : tickets.length === 0 ? (
        <EmptyState icon="help" title="No support tickets yet" text="Questions or issues you submit will show up here." />
      ) : (
        <div className={styles.list}>
          {tickets.map((t) => (
            <a key={t.id} href={`/account/support/${t.id}`} className={styles.row}>
              <div className={styles.rowInfo}>
                <span className={styles.subject}>{t.subject}</span>
                <span className={styles.meta}>
                  {t.message_count} message{t.message_count === 1 ? "" : "s"} · opened {formatDate(t.created_at)}
                </span>
              </div>
              <Pill tone={statusTone(t.status)}>{statusLabel(t.status)}</Pill>
              <Icon name="chevron-right" size={16} className={styles.chevron} />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
