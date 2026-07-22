"use client";

import { use } from "react";

import { SupportTicketThread } from "@/features/account/SupportTickets/SupportTicketThread";

import styles from "../../section.module.css";

export default function SupportTicketPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <div className={styles.section}>
      <SupportTicketThread ticketId={id} />
    </div>
  );
}
