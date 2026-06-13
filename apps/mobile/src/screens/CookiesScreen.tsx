import { ScrollView } from 'react-native';
import {
  LegalH1,
  LegalH2,
  LegalBody,
  LegalBullet,
  LegalNumbered,
  LegalDivider,
} from '../components/LegalContent';

export default function CookiesScreen() {
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: '#fff' }}
      contentContainerStyle={{ padding: 20, paddingBottom: 60 }}
    >
      <LegalBody text="Effective date: June 2026" />
      <LegalBody text="This notice explains what tracking technologies Bargain Hunters uses on our website and mobile application, what data is collected, and your choices." />

      <LegalDivider />
      <LegalH1 text="1. What We Use" />
      <LegalH2 text="1.1 Session cookie (strictly necessary)" />
      <LegalBody text="We use a single session cookie (Django's sessionid) to keep you logged in while you browse. This cookie:" />
      <LegalBullet text="Is deleted when you close your browser" />
      <LegalBullet text="Contains only an anonymous session identifier — not your personal data" />
      <LegalBullet text="Cannot be disabled without breaking account functionality" />
      <LegalH2 text="1.2 PostHog Analytics (functional/analytical)" />
      <LegalBody text="We use PostHog (EU Cloud, Frankfurt Germany) to understand how users interact with the Platform. PostHog collects:" />
      <LegalBullet text="Pages visited and time spent on each page" />
      <LegalBullet text="Clicks on deals, categories, search queries, and navigation elements" />
      <LegalBullet text="Shopping list and alert subscription actions" />
      <LegalBullet text="Device type, browser, and approximate location (country/city)" />
      <LegalBullet text="Session recordings (screen activity — all text inputs are masked)" />
      <LegalBody text="PostHog operates in cookie-free mode on our Platform. It uses a temporary in-memory identifier rather than a persistent cookie. This means it does not require a cookie consent banner under the Kenya DPA or EU ePrivacy Directive." />
      <LegalBody text="PostHog data is retained for 24 months (events) and 90 days (session recordings)." />

      <LegalDivider />
      <LegalH1 text="2. What We Do NOT Use" />
      <LegalBullet text="Google Analytics or Google Ads pixels" />
      <LegalBullet text="Facebook Pixel or Meta tracking" />
      <LegalBullet text="Advertising or retargeting cookies" />
      <LegalBullet text="Cross-site tracking technologies" />

      <LegalDivider />
      <LegalH1 text="3. Your Choices" />
      <LegalBody text="You can opt out of PostHog analytics by:" />
      <LegalNumbered n={1} text='Enabling "Do Not Track" in your browser settings — PostHog respects this signal' />
      <LegalNumbered n={2} text="Disabling JavaScript for bargainhunters.co.ke in your browser" />
      <LegalNumbered n={3} text="Emailing privacy@bargainhunters.co.ke to request exclusion from analytics" />
      <LegalBody text="Opting out of analytics does not affect your ability to use the Platform or receive deal alerts." />

      <LegalDivider />
      <LegalH1 text="4. Cross-Border Transfer" />
      <LegalBody text="PostHog analytics data is processed in Frankfurt, Germany (EU). The transfer is covered by Standard Contractual Clauses and PostHog's data processing agreement. See our Privacy Policy for full details." />

      <LegalDivider />
      <LegalH1 text="5. Contact" />
      <LegalBody text="For questions about tracking: privacy@bargainhunters.co.ke" />
    </ScrollView>
  );
}
