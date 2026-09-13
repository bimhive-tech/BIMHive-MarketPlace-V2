"use client";

import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Field } from "@/components/Field/Field";
import { TextareaField } from "@/components/Field/TextareaField";
import { Modal } from "@/components/Modal/Modal";
import { AccountApiError, createSupportTicket } from "@/lib/accountApi";
import type { MembershipPlan } from "@/lib/types";

import styles from "./PlanRequestModal.module.css";

interface PlanRequestModalProps {
  plan: MembershipPlan;
  open: boolean;
  onClose: () => void;
}

/**
 * The "Contact us" form for a by-request plan such as Enterprise.
 *
 * Deliberately a support ticket rather than a new sales-lead system: tickets
 * already have a staff inbox and a reply thread the customer can follow from
 * /account/support, so a request gets answered through something that exists.
 */
export function PlanRequestModal({ plan, open, onClose }: PlanRequestModalProps) {
  const [team, setTeam] = useState("");
  const [needs, setNeeds] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!needs.trim()) {
      setError("Tell us what you need so we can reply properly.");
      return;
    }
    setError("");
    setSending(true);
    try {
      const body = [team.trim() && `Team / company: ${team.trim()}`, needs.trim()].filter(Boolean).join("\n\n");
      await createSupportTicket(`${plan.name} plan request`, body);
      setSent(true);
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Couldn't send your request. Please try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="md"
      title={sent ? "Request sent" : `Request ${plan.name}`}
      description={
        sent
          ? "We'll reply in your support tickets."
          : "Tell us about your team and the tools you'd like. We'll get back to you."
      }
    >
      {sent ? (
        <div className={styles.sent}>
          <p className={styles.sentText}>
            Your request is in. You can follow the conversation any time from your account.
          </p>
          <Button href="/account/support" fullWidth>
            View my support tickets
          </Button>
        </div>
      ) : (
        <form className={styles.form} onSubmit={onSubmit} noValidate>
          <Field
            label="Team or company (optional)"
            name="plan_request_team"
            placeholder="e.g. 12 architects at Hive Design"
            value={team}
            onChange={(e) => setTeam(e.target.value)}
          />
          <TextareaField
            label="What do you need?"
            name="plan_request_needs"
            placeholder="Tools you'd like built, how many seats, support hours…"
            value={needs}
            onChange={(e) => setNeeds(e.target.value)}
            error={error}
          />
          <Button type="submit" fullWidth disabled={sending}>
            {sending ? "Sending…" : "Send request"}
          </Button>
        </form>
      )}
    </Modal>
  );
}
