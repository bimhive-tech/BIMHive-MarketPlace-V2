"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";

import styles from "./ExpandableText.module.css";

interface ExpandableTextProps {
  text: string;
  /** Lines shown before truncating. The toggle only appears if the text actually overflows this. */
  maxLines?: number;
  className?: string;
}

/** Clamps long text to `maxLines` with a "Read more"/"Show less" toggle — only rendered when the text actually overflows. */
export function ExpandableText({ text, maxLines = 4, className = "" }: ExpandableTextProps) {
  const textRef = useRef<HTMLParagraphElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [overflowing, setOverflowing] = useState(false);

  useEffect(() => {
    const el = textRef.current;
    if (!el) return;
    const checkOverflow = () => setOverflowing(el.scrollHeight > el.clientHeight + 1);
    checkOverflow();
    const observer = new ResizeObserver(checkOverflow);
    observer.observe(el);
    return () => observer.disconnect();
  }, [text, expanded]);

  return (
    <div className={styles.wrap}>
      <p
        ref={textRef}
        className={`${className} ${styles.text} ${expanded ? styles.expanded : ""}`}
        style={{ "--max-lines": maxLines } as CSSProperties}
      >
        {text}
      </p>
      {(overflowing || expanded) && (
        <button type="button" className={styles.toggle} onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Show less" : "Read more"}
        </button>
      )}
    </div>
  );
}
