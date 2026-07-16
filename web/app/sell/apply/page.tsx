"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, type ChangeEvent, type FormEvent } from "react";

import { Button } from "@/components/Button/Button";
import { Field } from "@/components/Field/Field";
import { Icon } from "@/components/Icon/Icon";
import { RequireAuth } from "@/features/auth/RequireAuth/RequireAuth";
import { applyToBecomeSeller, PartnerApiError } from "@/lib/partnerApi";

import styles from "./page.module.css";

export default function SellApplyPage() {
  return (
    <RequireAuth blockStaff>{() => <ApplyForm />}</RequireAuth>
  );
}

function ApplyForm() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [companyName, setCompanyName] = useState("");
  const [logo, setLogo] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function onPickLogo(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setLogo(file);
    setLogoPreview(URL.createObjectURL(file));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!companyName.trim()) {
      setError("A company name is required.");
      return;
    }
    setSubmitting(true);
    try {
      await applyToBecomeSeller(companyName.trim(), logo);
      router.push("/partner-portal");
      router.refresh();
    } catch (err) {
      setError(err instanceof PartnerApiError ? err.detail : "Could not submit your application.");
      setSubmitting(false);
    }
  }

  return (
    <div className={`container ${styles.page}`}>
      <header className={styles.head}>
        <h1 className={styles.title}>Become a Seller</h1>
        <p className={styles.sub}>
          Tell us about your company — BIMHive staff will review your application before you get
          access to the partner dashboard.
        </p>
      </header>

      <form className={styles.form} onSubmit={onSubmit} noValidate>
        <Field
          label="Company Name"
          name="company_name"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          placeholder="Your company or studio name"
          required
        />

        <div className={styles.logoField}>
          <p className={styles.logoLabel}>Logo (optional)</p>
          <div className={styles.logoRow}>
            <span className={styles.logoPreview}>
              {logoPreview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={logoPreview} alt="" />
              ) : (
                <Icon name="camera" size={22} />
              )}
            </span>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className={styles.hiddenFileInput}
              onChange={onPickLogo}
            />
            <button type="button" className={styles.uploadBtn} onClick={() => fileInputRef.current?.click()}>
              <Icon name="upload" size={14} /> {logo ? "Change Logo" : "Upload Logo"}
            </button>
          </div>
        </div>

        {error && <p className={styles.error}>{error}</p>}

        <Button type="submit" size="lg" disabled={submitting}>
          {submitting ? "Submitting…" : "Submit Application"}
        </Button>
      </form>
    </div>
  );
}
