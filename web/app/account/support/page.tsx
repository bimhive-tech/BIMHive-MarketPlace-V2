import { SupportTicketsList } from "@/features/account/SupportTickets/SupportTicketsList";

import styles from "../section.module.css";

export default function SupportPage() {
  return (
    <div className={styles.section}>
      <h1 className={styles.title}>Support Tickets</h1>
      <p className={styles.sub}>Get help with an order, license, or download.</p>
      <SupportTicketsList />
    </div>
  );
}
