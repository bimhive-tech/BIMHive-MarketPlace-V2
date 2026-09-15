import { LEGAL_ARTICLE_SLUGS } from "@/config/site";
import { LegalPage, legalMetadata } from "@/features/legal/LegalPage/LegalPage";

// Rendered on demand: the API isn't reachable during the image build.
export const dynamic = "force-dynamic";

export const generateMetadata = () => legalMetadata(LEGAL_ARTICLE_SLUGS.privacy, "Privacy Policy");

export default function PrivacyPage() {
  return <LegalPage slug={LEGAL_ARTICLE_SLUGS.privacy} />;
}
