import { ScrollView } from 'react-native';
import {
  LegalH1,
  LegalH2,
  LegalBody,
  LegalBullet,
  LegalNumbered,
  LegalInfoRow,
  LegalDivider,
} from '../components/LegalContent';

export default function PrivacyScreen() {
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: '#fff' }}
      contentContainerStyle={{ padding: 20, paddingBottom: 60 }}
    >
      <LegalBody text="Effective date: June 2026" />
      <LegalBody text='This Privacy Policy explains how Bargain Hunters ("we", "us", or "our") collects, uses, stores, and protects your personal data when you use our website, mobile application, and WhatsApp service (collectively, the "Platform"). We are committed to complying with the Kenya Data Protection Act, 2019 ("DPA") and applicable regulations.' />

      <LegalDivider />
      <LegalH1 text="1. Who We Are" />
      <LegalBody text="Bargain Hunters is a Kenyan deal aggregation platform that collects and displays product pricing and discount information from Naivas, Quickmart, Carrefour, and Chandarana supermarkets. We operate at www.bargainhunters.co.ke." />
      <LegalBody text="Data Controller contact:" />
      <LegalInfoRow label="Name" value="Bargain Hunters" />
      <LegalInfoRow label="Email" value="privacy@bargainhunters.co.ke" />
      <LegalInfoRow label="Website" value="www.bargainhunters.co.ke" />

      <LegalDivider />
      <LegalH1 text="2. What Personal Data We Collect" />
      <LegalH2 text="2.1 Data you provide directly" />
      <LegalBullet text="Full name and email address (when you register an account)" />
      <LegalBullet text="Phone number (for WhatsApp alerts)" />
      <LegalBullet text="Date of birth (optional, for age verification)" />
      <LegalBullet text="Payment information (M-Pesa transaction reference — we do not store card numbers)" />
      <LegalH2 text="2.2 Data collected automatically" />
      <LegalBullet text="Pages visited, links clicked, search queries entered, and deals viewed" />
      <LegalBullet text="Device type, operating system, and browser" />
      <LegalBullet text="IP address and approximate location (city/country level)" />
      <LegalBullet text="Session duration and navigation path through the Platform" />
      <LegalBullet text="Shopping lists created and alert subscriptions configured" />
      <LegalH2 text="2.3 Data from third-party analytics" />
      <LegalBody text="We use PostHog (PostHog Inc., EU Cloud hosted in Frankfurt, Germany) to collect behavioural analytics data including page views, clicks, and session recordings. PostHog processes data under Standard Contractual Clauses approved by the European Commission. See Section 7 for details on cross-border transfers." />

      <LegalDivider />
      <LegalH1 text="3. How We Use Your Data" />
      <LegalH2 text="3.1 To provide the service" />
      <LegalBullet text="Creating and managing your account" />
      <LegalBullet text="Sending deal alerts via WhatsApp or in-app notifications based on your subscriptions" />
      <LegalBullet text="Generating personalised shopping lists and price comparisons" />
      <LegalBullet text="Processing payments for premium subscriptions" />
      <LegalH2 text="3.2 To improve the Platform" />
      <LegalBullet text="Understanding which product categories and retailers are most useful" />
      <LegalBullet text="Identifying pages or features where users experience difficulty" />
      <LegalBullet text="Improving search accuracy and deal recommendations" />
      <LegalH2 text="3.3 Legal compliance" />
      <LegalBullet text="Responding to lawful requests from the Office of the Data Protection Commissioner (ODPC) or other authorities" />
      <LegalBullet text="Resolving disputes and enforcing our Terms of Service" />

      <LegalDivider />
      <LegalH1 text="4. Legal Basis for Processing" />
      <LegalBody text="Under Section 30 of the DPA, we process your personal data on the following lawful grounds:" />
      <LegalBody text="Consent — for analytics tracking, marketing communications, and optional profile data. You may withdraw consent at any time." />
      <LegalBody text="Contractual necessity — to create your account and deliver deal alerts and shopping list features you have requested." />
      <LegalBody text="Legitimate interests — for fraud prevention, platform security, and aggregate analytics that do not override your rights." />
      <LegalBody text="Legal obligation — where Kenyan law requires us to retain or disclose data." />

      <LegalDivider />
      <LegalH1 text="5. How Long We Keep Your Data" />
      <LegalInfoRow label="Account data" value="Until you delete your account, plus 90 days" />
      <LegalInfoRow label="Deal alert history" value="12 months from the date the alert was sent" />
      <LegalInfoRow label="Payment records" value="7 years (Kenya tax law requirement)" />
      <LegalInfoRow label="Analytics data" value="24 months (PostHog EU Cloud)" />
      <LegalInfoRow label="Session recordings" value="90 days (PostHog EU Cloud)" />

      <LegalDivider />
      <LegalH1 text="6. Who We Share Your Data With" />
      <LegalBody text="We do not sell your personal data. We share data only with:" />
      <LegalH2 text="6.1 Service providers" />
      <LegalBullet text="PostHog Inc. (EU) — product analytics and session recording" />
      <LegalBullet text="Twilio / Meta — WhatsApp Business API for alert delivery" />
      <LegalBullet text="Contabo GmbH (Germany) — server hosting for our backend, database, and application" />
      <LegalBullet text="Payment processors — M-Pesa (Safaricom) for subscription payments" />
      <LegalH2 text="6.2 Legal disclosure" />
      <LegalBody text="We may disclose your data if required by law, court order, or to protect the rights and safety of our users or the public." />

      <LegalDivider />
      <LegalH1 text="7. Cross-Border Data Transfers" />
      <LegalBody text="Some of the service providers listed above process data outside Kenya, primarily in Germany (EU). Under Section 48 of the DPA, we ensure that appropriate safeguards are in place before transferring personal data outside Kenya:" />
      <LegalBullet text="PostHog EU Cloud: covered by Standard Contractual Clauses (SCCs) between PostHog and its sub-processors, and by the EU's GDPR which provides a level of protection comparable to Kenya's DPA." />
      <LegalBullet text="Contabo GmbH: our primary server is in Frankfurt, Germany, a jurisdiction with strong data protection law (GDPR)." />
      <LegalBullet text="Meta/Twilio: covered by their respective data processing agreements and applicable international transfer mechanisms." />
      <LegalBody text="Note on data localisation: Section 48(2) of the DPA requires that at least one serving copy of personal data on Kenyan residents be maintained on a server physically located in Kenya. We are working toward establishing a Kenya-based data replica and will update this policy when that is in place." />

      <LegalDivider />
      <LegalH1 text="8. Your Rights Under the DPA" />
      <LegalBody text="Under Sections 26–34 of the Kenya Data Protection Act, you have the following rights:" />
      <LegalNumbered n={1} text="Right to be informed — to know what data we hold about you and how we use it." />
      <LegalNumbered n={2} text="Right of access — to request a copy of your personal data." />
      <LegalNumbered n={3} text="Right to rectification — to correct inaccurate or incomplete data." />
      <LegalNumbered n={4} text="Right to erasure — to request deletion of your data (subject to legal retention obligations)." />
      <LegalNumbered n={5} text="Right to restrict processing — to limit how we use your data in certain circumstances." />
      <LegalNumbered n={6} text="Right to data portability — to receive your data in a structured, machine-readable format." />
      <LegalNumbered n={7} text="Right to object — to object to processing based on legitimate interests." />
      <LegalNumbered n={8} text="Right to withdraw consent — at any time, without affecting prior lawful processing." />
      <LegalBody text="To exercise any of these rights, email us at privacy@bargainhunters.co.ke. We will respond within 21 days as required by the DPA." />
      <LegalBody text="If you are not satisfied with our response, you have the right to lodge a complaint with the Office of the Data Protection Commissioner (ODPC) at www.odpc.go.ke." />

      <LegalDivider />
      <LegalH1 text="9. Cookies and Tracking" />
      <LegalBody text="Our website uses PostHog analytics which operates in cookie-free mode. We do not use advertising cookies, retargeting pixels, or third-party tracking cookies. We use a single functional session cookie to keep you logged in across pages." />
      <LegalBody text="You can disable JavaScript in your browser to prevent all analytics tracking. This will not affect core Platform functionality." />

      <LegalDivider />
      <LegalH1 text="10. Children's Privacy" />
      <LegalBody text="The Platform is not directed at children under 18. We do not knowingly collect personal data from minors. If you believe a minor has provided us with personal data, please contact us at privacy@bargainhunters.co.ke and we will delete it promptly." />

      <LegalDivider />
      <LegalH1 text="11. Security" />
      <LegalBullet text="HTTPS encryption for all data in transit (TLS 1.2+)" />
      <LegalBullet text="Encrypted passwords (Django's PBKDF2 hashing)" />
      <LegalBullet text="Role-based access controls limiting who can access production data" />
      <LegalBullet text="Regular dependency updates and security patching" />
      <LegalBody text="In the event of a data breach that is likely to result in risk to your rights, we will notify you and the ODPC within 72 hours of becoming aware of it, as required by Section 43 of the DPA." />

      <LegalDivider />
      <LegalH1 text="12. Changes to This Policy" />
      <LegalBody text="We may update this Privacy Policy from time to time. We will notify registered users by email and display a prominent notice on the Platform at least 14 days before material changes take effect. Continued use of the Platform after changes take effect constitutes acceptance of the updated policy." />

      <LegalDivider />
      <LegalH1 text="13. Contact" />
      <LegalBody text="For any questions about this Privacy Policy or your personal data, contact us at: privacy@bargainhunters.co.ke" />
      <LegalBody text="Bargain Hunters | www.bargainhunters.co.ke" />
    </ScrollView>
  );
}
