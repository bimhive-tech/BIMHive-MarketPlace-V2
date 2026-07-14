import Link from "next/link";
import type { ReactNode } from "react";

import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "text";
type Size = "md" | "lg";

interface BaseProps {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
  className?: string;
  fullWidth?: boolean;
}

interface ButtonAsButton extends BaseProps {
  href?: undefined;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
}

interface ButtonAsLink extends BaseProps {
  href: string;
  // Plain <a> instead of next/link — required for anything that isn't a Next
  // page (e.g. a redirect-then-file-download endpoint): Link's client-side
  // routing would try to soft-navigate to it as if it were a page and never
  // let the browser follow the actual redirect/download.
  external?: boolean;
}

type ButtonProps = ButtonAsButton | ButtonAsLink;

function classes(variant: Variant, size: Size, fullWidth?: boolean, extra?: string) {
  return [
    styles.btn,
    styles[variant],
    styles[size],
    fullWidth ? styles.fullWidth : "",
    extra ?? "",
  ]
    .filter(Boolean)
    .join(" ");
}

export function Button(props: ButtonProps) {
  const { variant = "primary", size = "md", children, className, fullWidth } = props;
  const cls = classes(variant, size, fullWidth, className);

  if ("href" in props && props.href) {
    if (props.external) {
      return (
        <a href={props.href} className={cls}>
          {children}
        </a>
      );
    }
    return (
      <Link href={props.href} className={cls}>
        {children}
      </Link>
    );
  }
  const { onClick, type = "button", disabled } = props as ButtonAsButton;
  return (
    <button className={cls} onClick={onClick} type={type} disabled={disabled}>
      {children}
    </button>
  );
}
