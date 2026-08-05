"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { getSignupOptions, updateProfile, type CountryOption, type SignupOption } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./ProfileForm.module.css";

const BIO_MAX = 200;

export function ProfileForm({ user, onSaved }: { user: User; onSaved: (user: User) => void }) {
  const [fullName, setFullName] = useState(user.full_name === user.username ? "" : user.full_name);
  const [company, setCompany] = useState(user.profile?.company ?? "");
  const [jobTitle, setJobTitle] = useState(user.profile?.job_title ?? "");
  const [bio, setBio] = useState(user.profile?.bio ?? "");
  const [profession, setProfession] = useState(user.profile?.profession ?? "");
  const [country, setCountry] = useState(user.profile?.country ?? "");
  const [professions, setProfessions] = useState<SignupOption[]>([]);
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [avatarNote, setAvatarNote] = useState(false);

  useEffect(() => {
    getSignupOptions().then(({ professions, countries }) => {
      setProfessions(professions);
      setCountries(countries);
    });
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    const [first, ...rest] = fullName.trim().split(" ");
    try {
      const updated = await updateProfile({
        first_name: first || "",
        last_name: rest.join(" "),
        profile: { company, job_title: jobTitle, bio, profession, country },
      });
      onSaved(updated);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2200);
    } catch {
      setError("Could not save your changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  function onAvatarClick() {
    setAvatarNote(true);
    window.setTimeout(() => setAvatarNote(false), 2200);
  }

  return (
    <form className={styles.card} onSubmit={onSubmit}>
      <h2 className={styles.title}>Profile Information</h2>

      <div className={styles.avatarRow}>
        <div className={styles.avatarWrap}>
          <span className={styles.avatar}>
            <Icon name="users" size={32} />
          </span>
          <button type="button" className={styles.avatarBtn} onClick={onAvatarClick} aria-label="Change avatar">
            <Icon name="camera" size={14} />
          </button>
        </div>
        <div className={styles.avatarText}>
          <p className={styles.avatarHint}>JPG, PNG or GIF. Max size 2MB.</p>
          {avatarNote && <p className={styles.avatarNote}>Avatar uploads are coming soon.</p>}
        </div>
      </div>

      <label className={styles.field}>
        Full Name
        <input
          className={styles.input}
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Your name"
        />
      </label>

      <label className={styles.field}>
        Email Address
        <input className={styles.input} value={user.email} disabled />
        <span className={styles.hint}>Update your email from the Email Address section below.</span>
      </label>

      <div className={styles.row}>
        <label className={styles.field}>
          Company <span className={styles.optional}>(Optional)</span>
          <input className={styles.input} value={company} onChange={(e) => setCompany(e.target.value)} />
        </label>
        <label className={styles.field}>
          Job Title <span className={styles.optional}>(Optional)</span>
          <input className={styles.input} value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} />
        </label>
      </div>

      <div className={styles.row}>
        <label className={styles.field}>
          Profession <span className={styles.optional}>(Optional)</span>
          <select className={styles.input} value={profession} onChange={(e) => setProfession(e.target.value)}>
            <option value="">Prefer not to say</option>
            {professions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          Country
          <select className={styles.input} value={country} onChange={(e) => setCountry(e.target.value)}>
            <option value="">Select your country</option>
            {countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
          </select>
          <span className={styles.hint}>Used for regional pricing where it's available.</span>
        </label>
      </div>

      <label className={styles.field}>
        Bio <span className={styles.optional}>(Optional)</span>
        <div className={styles.textareaWrap}>
          <textarea
            className={styles.textarea}
            rows={3}
            maxLength={BIO_MAX}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="Tell other AEC professionals a bit about yourself."
          />
          <span className={styles.counter}>
            {bio.length}/{BIO_MAX}
          </span>
        </div>
      </label>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.actions}>
        <button type="submit" className={styles.saveBtn} disabled={saving}>
          {saving ? "Saving…" : "Save Changes"}
        </button>
        {saved && <span className={styles.saved}><Icon name="check-circle" size={16} /> Saved</span>}
      </div>
    </form>
  );
}
