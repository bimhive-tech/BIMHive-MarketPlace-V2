"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Field } from "@/components/Field/Field";
import { SelectField } from "@/components/Field/SelectField";
import { SelectWithOther } from "@/components/Field/SelectWithOther";
import {
  AuthError,
  getSignupOptions,
  register,
  type CountryOption,
  type SignupOption,
} from "@/lib/auth";

import styles from "./AuthForm.module.css";

export function SignUpForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);
  const [professions, setProfessions] = useState<SignupOption[]>([]);
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const [universities, setUniversities] = useState<string[]>([]);
  // Controlled, unlike the rest of this form: which follow-up shows depends on
  // the answer, and SelectWithOther needs its value back to know when to
  // reveal the free-text input.
  const [isStudent, setIsStudent] = useState(false);
  const [university, setUniversity] = useState("");
  const [company, setCompany] = useState("");

  useEffect(() => {
    getSignupOptions().then(({ professions, countries, universities }) => {
      setProfessions(professions);
      setCountries(countries);
      setUniversities(universities);
    });
  }, []);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    setPending(true);
    const form = new FormData(e.currentTarget);
    try {
      await register({
        email: String(form.get("email")),
        password: String(form.get("password")),
        fullName: String(form.get("full_name")),
        profession: String(form.get("profession") || ""),
        country: String(form.get("country") || ""),
        isStudent,
        university: isStudent ? university : "",
        company: isStudent ? "" : company,
      });
      router.push("/account");
      router.refresh();
    } catch (err) {
      if (err instanceof AuthError) {
        setError(err.detail);
        const fe: Record<string, string> = {};
        for (const key of ["email", "password", "country"]) {
          if (Array.isArray(err.fields[key])) fe[key] = err.fields[key][0];
        }
        setFieldErrors(fe);
      } else {
        setError("Sign up failed.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      {error && !Object.keys(fieldErrors).length && <div className={styles.alert}>{error}</div>}
      <Field label="Full name" name="full_name" placeholder="Jane Doe" autoComplete="name" />
      <Field
        label="Email"
        name="email"
        type="email"
        placeholder="name@company.com"
        required
        autoComplete="email"
        error={fieldErrors.email}
      />
      <Field
        label="Password"
        name="password"
        type="password"
        placeholder="At least 8 characters"
        required
        autoComplete="new-password"
        error={fieldErrors.password}
        hint="Use 8+ characters with a mix of letters and numbers."
      />
      <SelectField label="Profession" name="profession" defaultValue="">
        <option value="">Prefer not to say</option>
        {professions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </SelectField>
      <SelectField
        label="Country"
        name="country"
        required
        defaultValue=""
        error={fieldErrors.country}
        hint={fieldErrors.country ? undefined : "Used for regional pricing where it's available."}
      >
        <option value="" disabled>
          Select your country
        </option>
        {countries.map((country) => (
          <option key={country.code} value={country.code}>
            {country.name}
          </option>
        ))}
      </SelectField>
      <SelectField
        label="Are you a student?"
        name="is_student"
        value={isStudent ? "yes" : "no"}
        onChange={(e) => setIsStudent(e.target.value === "yes")}
      >
        <option value="no">No — I'm working</option>
        <option value="yes">Yes, I'm a student</option>
      </SelectField>
      {isStudent ? (
        <SelectWithOther
          label="University or college (optional)"
          name="university"
          options={universities}
          value={university}
          onChange={setUniversity}
          placeholder="Select your university"
          otherPlaceholder="Your university's name"
        />
      ) : (
        <Field
          label="Company (optional)"
          name="company"
          placeholder="Where you work"
          autoComplete="organization"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
        />
      )}
      <Button type="submit" size="lg" fullWidth>
        {pending ? "Creating account…" : "Create account"}
      </Button>
    </form>
  );
}
