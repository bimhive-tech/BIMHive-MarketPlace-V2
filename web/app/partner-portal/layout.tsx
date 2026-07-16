"use client";

import { ForcePasswordChange } from "@/features/partner/ForcePasswordChange/ForcePasswordChange";
import { PartnerShell } from "@/features/partner/PartnerShell/PartnerShell";
import { RequireAuth } from "@/features/auth/RequireAuth/RequireAuth";

export default function PartnerPortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth partnerOnly>
      {(user) =>
        user.must_change_password ? (
          <ForcePasswordChange />
        ) : (
          <PartnerShell user={user}>{children}</PartnerShell>
        )
      }
    </RequireAuth>
  );
}
