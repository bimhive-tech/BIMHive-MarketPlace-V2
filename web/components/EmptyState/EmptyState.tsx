import { Button } from "@/components/Button/Button";
import { Icon, type IconName } from "@/components/Icon/Icon";

import styles from "./EmptyState.module.css";

interface EmptyStateProps {
  icon: IconName;
  title: string;
  text: string;
  actionLabel?: string;
  actionHref?: string;
}

export function EmptyState({ icon, title, text, actionLabel, actionHref }: EmptyStateProps) {
  return (
    <div className={styles.empty}>
      <Icon name={icon} size={30} className={styles.icon} />
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.text}>{text}</p>
      {actionLabel && actionHref && (
        <Button href={actionHref} variant="secondary">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
