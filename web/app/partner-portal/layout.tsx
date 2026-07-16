"use client";

import { usePathname } from "next/navigation";

import { ApplicationStatus } from "@/features/partner/ApplicationStatus/ApplicationStatus";
import { PartnerShell } from "@/features/partner/PartnerShell/PartnerShell";
import { RequireAuth } from "@/features/auth/RequireAuth/RequireAuth";

export default function PartnerPortalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <RequireAuth partnerOnly>
      {(user) => {
        const approved = user.partner?.status === "approved";
        // Partner Profile stays reachable regardless of status — everywhere
        // else, an unapproved applicant sees their status instead of content
        // that the backend would 403 on anyway (see catalog.permissions).
        const showStatusScreen = !approved && pathname !== "/partner-portal/profile";
        return (
          <PartnerShell user={user}>
            {showStatusScreen ? <ApplicationStatus partner={user.partner!} /> : children}
          </PartnerShell>
        );
      }}
    </RequireAuth>
  );
}
