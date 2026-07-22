"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { AccountApiError, getSupportTicket, replySupportTicket, type SupportTicketDetail } from "@/lib/accountApi";

import styles from "./SupportTickets.module.css";

function statusTone(status: SupportTicketDetail["status"]): "success" | "warning" | "neutral" {
  if (status === "resolved") return "success";
  if (status === "awaiting_customer") return "neutral";
  return "warning";
}

function statusLabel(status: SupportTicketDetail["status"]): string {
  if (status === "awaiting_customer") return "Awaiting you";
  return status[0].toUpperCase() + status.slice(1);
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export function SupportTicketThread({ ticketId }: { ticketId: string }) {
  const [ticket, setTicket] = useState<SupportTicketDetail | null | undefined>(undefined);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getSupportTicket(ticketId)
      .then(setTicket)
      .catch(() => setTicket(null));
  }, [ticketId]);

  async function onReply(e: React.FormEvent) {
    e.preventDefault();
    if (!reply.trim()) return;
    setError("");
    setSending(true);
    try {
      const updated = await replySupportTicket(ticketId, reply.trim());
      setTicket(updated);
      setReply("");
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Could not send your reply.");
    } finally {
      setSending(false);
    }
  }

  if (ticket === undefined) return <p className={styles.loading}>Loading ticket…</p>;
  if (ticket === null) return <p className={styles.error}>Ticket not found.</p>;

  return (
    <div className={styles.threadWrap}>
      <div className={styles.threadHead}>
        <h1 className={styles.threadSubject}>{ticket.subject}</h1>
        <Pill tone={statusTone(ticket.status)}>{statusLabel(ticket.status)}</Pill>
      </div>

      <div className={styles.thread}>
        {ticket.messages.map((m) => (
          <div key={m.id} className={`${styles.message} ${m.is_staff_reply ? styles.messageStaff : ""}`}>
            <div className={styles.messageHead}>
              <span className={styles.messageAuthor}>
                {m.is_staff_reply ? "BIMHIVE Support" : "You"}
              </span>
              <span className={styles.messageTime}>{formatDateTime(m.created_at)}</span>
            </div>
            <p className={styles.messageBody}>{m.body}</p>
          </div>
        ))}
      </div>

      <form className={styles.replyForm} onSubmit={onReply}>
        <textarea
          className={styles.textarea}
          placeholder="Write a reply…"
          value={reply}
          onChange={(e) => setReply(e.target.value)}
          rows={3}
          required
        />
        {error && <p className={styles.error}>{error}</p>}
        <button type="submit" className={styles.submitBtn} disabled={sending}>
          <Icon name="chevron-right" size={16} />
          {sending ? "Sending…" : "Send Reply"}
        </button>
      </form>
    </div>
  );
}
