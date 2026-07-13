import { Icon, type IconName } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import type { User } from "@/lib/types";

import styles from "./AccountSummaryCard.module.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function AccountSummaryCard({ user }: { user: User }) {
  const rows: { icon: IconName; label: string; value: React.ReactNode }[] = [
    { icon: "help", label: "Member Since", value: formatDate(user.date_joined) },
    {
      icon: "users",
      label: "Account Type",
      value: <Pill tone="neutral">{user.profile?.account_type === "team" ? "Team" : "Individual"}</Pill>,
    },
    { icon: "check-circle", label: "Account Status", value: <Pill tone="success">Active</Pill> },
  ];

  return (
    <div className={styles.card}>
      <h2 className={styles.title}>Account Summary</h2>
      {rows.map((row) => (
        <div key={row.label} className={styles.row}>
          <Icon name={row.icon} size={18} className={styles.icon} />
          <span className={styles.label}>{row.label}</span>
          <span className={styles.value}>{row.value}</span>
        </div>
      ))}
    </div>
  );
}
