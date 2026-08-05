"use client";

import { useEffect, useState } from "react";

const MS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = 60 * SECONDS_PER_MINUTE;
const SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR;

export interface Countdown {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  /** True once the deadline has passed — callers hide the offer rather than
   * showing a frozen row of zeroes. */
  expired: boolean;
}

function remainingFrom(deadline: string): Countdown {
  const totalSeconds = Math.max(0, Math.floor((new Date(deadline).getTime() - Date.now()) / MS_PER_SECOND));
  return {
    days: Math.floor(totalSeconds / SECONDS_PER_DAY),
    hours: Math.floor((totalSeconds % SECONDS_PER_DAY) / SECONDS_PER_HOUR),
    minutes: Math.floor((totalSeconds % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE),
    seconds: totalSeconds % SECONDS_PER_MINUTE,
    expired: totalSeconds === 0,
  };
}

/**
 * Ticks down to `deadline` once a second.
 *
 * Returns null on the first render so the server and the client agree on the
 * markup — "now" differs between them, and hydrating a live clock would
 * otherwise mismatch. Callers render nothing until the first tick lands.
 */
export function useCountdown(deadline: string | undefined): Countdown | null {
  const [countdown, setCountdown] = useState<Countdown | null>(null);

  useEffect(() => {
    if (!deadline) {
      setCountdown(null);
      return;
    }
    setCountdown(remainingFrom(deadline));
    const timer = setInterval(() => setCountdown(remainingFrom(deadline)), MS_PER_SECOND);
    return () => clearInterval(timer);
  }, [deadline]);

  return countdown;
}

/** Two-digit display, so the clock doesn't jitter as digits drop. */
export function padUnit(value: number): string {
  return String(value).padStart(2, "0");
}
