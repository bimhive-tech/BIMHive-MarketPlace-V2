"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { getPartnerProfile, updatePartnerProfile, type PartnerProfile } from "@/lib/partnerApi";

import styles from "./page.module.css";

export default function PartnerProfilePage() {
  const [profile, setProfile] = useState<PartnerProfile | null>(null);
  const [tagline, setTagline] = useState("");
  const [bio, setBio] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [website, setWebsite] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getPartnerProfile()
      .then((p) => {
        setProfile(p);
        setTagline(p.tagline);
        setBio(p.bio);
        setLogoUrl(p.logo_url);
        setWebsite(p.website);
      })
      .catch(() => setError("Could not load your partner profile."));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const updated = await updatePartnerProfile({ tagline, bio, logo_url: logoUrl, website });
      setProfile(updated);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2200);
    } catch {
      setError("Could not save your changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (!profile) return <div className={styles.loading}>Loading your partner profile…</div>;

  const STATUS_TONE = { pending: "warning", approved: "success", rejected: "error" } as const;
  const STATUS_LABEL = { pending: "Pending Review", approved: "Approved", rejected: "Rejected" } as const;

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Partner Profile</h1>
          <p className={styles.sub}>This is what customers see on your public partner page.</p>
        </div>
        <div className={styles.badges}>
          <Pill tone={STATUS_TONE[profile.status]}>{STATUS_LABEL[profile.status]}</Pill>
          {profile.is_verified && <Pill tone="success">Verified</Pill>}
        </div>
      </header>

      {profile.status !== "approved" && (
        <div className={profile.status === "pending" ? styles.noticeInfo : styles.noticeError}>
          <p>
            {profile.status === "pending"
              ? "Your application is under review — BIMHive staff will approve or reject it soon."
              : profile.rejection_note || "Your application was rejected. No reason was given."}
          </p>
        </div>
      )}

      <form className={styles.card} onSubmit={onSubmit}>
        <label className={styles.field}>
          Partner Name
          <input className={styles.input} value={profile.name} disabled />
          <span className={styles.hint}>Contact BIMHIVE to change your partner name.</span>
        </label>

        <label className={styles.field}>
          Tagline
          <input
            className={styles.input}
            value={tagline}
            maxLength={180}
            onChange={(e) => setTagline(e.target.value)}
            placeholder="A short line describing what you make"
          />
        </label>

        <label className={styles.field}>
          Bio
          <textarea
            className={styles.textarea}
            rows={4}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="Tell customers about your team and your products."
          />
        </label>

        <label className={styles.field}>
          Logo URL
          <input
            className={styles.input}
            value={logoUrl}
            onChange={(e) => setLogoUrl(e.target.value)}
            placeholder="https://…"
          />
        </label>

        <label className={styles.field}>
          Website
          <input
            className={styles.input}
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder="https://…"
          />
        </label>

        {error && <p className={styles.error}>{error}</p>}

        <div className={styles.actions}>
          <button type="submit" className={styles.saveBtn} disabled={saving}>
            {saving ? "Saving…" : "Save Changes"}
          </button>
          {saved && (
            <span className={styles.saved}>
              <Icon name="check-circle" size={16} /> Saved
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
