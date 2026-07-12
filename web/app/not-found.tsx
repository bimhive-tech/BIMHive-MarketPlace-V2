import { Button } from "@/components/Button/Button";

import styles from "./not-found.module.css";

export default function NotFound() {
  return (
    <div className={`container ${styles.wrap}`}>
      <p className={styles.code}>404</p>
      <h1 className={styles.title}>Page not found</h1>
      <p className={styles.text}>The page you&apos;re looking for doesn&apos;t exist or has moved.</p>
      <Button href="/">Back to home</Button>
    </div>
  );
}
