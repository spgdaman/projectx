import type { Metadata } from 'next'
import {
  LegalSection,
  LegalSubSection,
  LegalParagraph,
  LegalList,
  LegalOrderedList,
  InfoBox,
  LegalNote,
  RetentionTable,
} from '@/components/legal/LegalPage'

export const metadata: Metadata = {
  title: 'Privacy Policy | Bargain Hunters Kenya',
  description:
    'How Bargain Hunters collects, uses, and protects your personal data under the Kenya Data Protection Act 2019.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.bargainhunters.co.ke/privacy',
  },
}

export default function PrivacyPage() {
  return (
    <article>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
      <p className="text-sm text-gray-400 mb-8">Effective date: June 2026</p>

      <LegalParagraph>
        This Privacy Policy explains how Bargain Hunters (&ldquo;we&rdquo;, &ldquo;us&rdquo;, or
        &ldquo;our&rdquo;) collects, uses, stores, and protects your personal data when you use our
        website, mobile application, and WhatsApp service (collectively, the &ldquo;Platform&rdquo;).
        We are committed to complying with the Kenya Data Protection Act, 2019 (&ldquo;DPA&rdquo;)
        and applicable regulations.
      </LegalParagraph>

      <LegalSection title="1. Who We Are">
        <LegalParagraph>
          Bargain Hunters is a Kenyan deal aggregation platform that collects and displays product
          pricing and discount information from Naivas, Quickmart, Carrefour, and Chandarana
          supermarkets. We operate at www.bargainhunters.co.ke.
        </LegalParagraph>
        <LegalParagraph>Data Controller contact:</LegalParagraph>
        <div className="bg-gray-50 rounded-lg px-4 py-3 mb-4">
          <InfoBox label="Name" value="Bargain Hunters" />
          <InfoBox label="Email" value="privacy@bargainhunters.co.ke" />
          <InfoBox label="Website" value="www.bargainhunters.co.ke" />
        </div>
      </LegalSection>

      <LegalSection title="2. What Personal Data We Collect">
        <LegalSubSection title="2.1 Data you provide directly">
          <LegalList
            items={[
              'Full name and email address (when you register an account)',
              'Phone number (for WhatsApp alerts)',
              'Date of birth (optional, for age verification)',
              'Payment information (M-Pesa transaction reference — we do not store card numbers)',
            ]}
          />
        </LegalSubSection>

        <LegalSubSection title="2.2 Data collected automatically">
          <LegalList
            items={[
              'Pages visited, links clicked, search queries entered, and deals viewed',
              'Device type, operating system, and browser',
              'IP address and approximate location (city/country level)',
              'Session duration and navigation path through the Platform',
              'Shopping lists created and alert subscriptions configured',
            ]}
          />
        </LegalSubSection>

        <LegalSubSection title="2.3 Data from third-party analytics">
          <LegalParagraph>
            We use PostHog (PostHog Inc., EU Cloud hosted in Frankfurt, Germany) to collect
            behavioural analytics data including page views, clicks, and session recordings. PostHog
            processes data under Standard Contractual Clauses approved by the European Commission.
            See Section 7 for details on cross-border transfers.
          </LegalParagraph>
        </LegalSubSection>
      </LegalSection>

      <LegalSection title="3. How We Use Your Data">
        <LegalSubSection title="3.1 To provide the service">
          <LegalList
            items={[
              'Creating and managing your account',
              'Sending deal alerts via WhatsApp or in-app notifications based on your subscriptions',
              'Generating personalised shopping lists and price comparisons',
              'Processing payments for premium subscriptions',
            ]}
          />
        </LegalSubSection>

        <LegalSubSection title="3.2 To improve the Platform">
          <LegalList
            items={[
              'Understanding which product categories and retailers are most useful',
              'Identifying pages or features where users experience difficulty',
              'Improving search accuracy and deal recommendations',
            ]}
          />
        </LegalSubSection>

        <LegalSubSection title="3.3 Legal compliance">
          <LegalList
            items={[
              'Responding to lawful requests from the Office of the Data Protection Commissioner (ODPC) or other authorities',
              'Resolving disputes and enforcing our Terms of Service',
            ]}
          />
        </LegalSubSection>
      </LegalSection>

      <LegalSection title="4. Legal Basis for Processing">
        <LegalParagraph>
          Under Section 30 of the DPA, we process your personal data on the following lawful
          grounds:
        </LegalParagraph>
        <LegalParagraph>
          <strong>Consent</strong> — for analytics tracking, marketing communications, and optional
          profile data. You may withdraw consent at any time.
        </LegalParagraph>
        <LegalParagraph>
          <strong>Contractual necessity</strong> — to create your account and deliver deal alerts
          and shopping list features you have requested.
        </LegalParagraph>
        <LegalParagraph>
          <strong>Legitimate interests</strong> — for fraud prevention, platform security, and
          aggregate analytics that do not override your rights.
        </LegalParagraph>
        <LegalParagraph>
          <strong>Legal obligation</strong> — where Kenyan law requires us to retain or disclose
          data.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="5. How Long We Keep Your Data">
        <RetentionTable
          rows={[
            { label: 'Account data', value: 'Until you delete your account, plus 90 days' },
            {
              label: 'Deal alert history',
              value: '12 months from the date the alert was sent',
            },
            { label: 'Payment records', value: '7 years (Kenya tax law requirement)' },
            { label: 'Analytics data', value: '24 months (PostHog EU Cloud)' },
            { label: 'Session recordings', value: '90 days (PostHog EU Cloud)' },
          ]}
        />
      </LegalSection>

      <LegalSection title="6. Who We Share Your Data With">
        <LegalParagraph>
          We do not sell your personal data. We share data only with:
        </LegalParagraph>

        <LegalSubSection title="6.1 Service providers">
          <LegalList
            items={[
              'PostHog Inc. (EU) — product analytics and session recording',
              'Twilio / Meta — WhatsApp Business API for alert delivery',
              'Contabo GmbH (Germany) — server hosting for our backend, database, and application',
              'Payment processors — M-Pesa (Safaricom) for subscription payments',
            ]}
          />
        </LegalSubSection>

        <LegalSubSection title="6.2 Legal disclosure">
          <LegalParagraph>
            We may disclose your data if required by law, court order, or to protect the rights and
            safety of our users or the public.
          </LegalParagraph>
        </LegalSubSection>
      </LegalSection>

      <LegalSection title="7. Cross-Border Data Transfers">
        <LegalParagraph>
          Some of the service providers listed above process data outside Kenya, primarily in
          Germany (EU). Under Section 48 of the DPA, we ensure that appropriate safeguards are in
          place before transferring personal data outside Kenya:
        </LegalParagraph>
        <LegalList
          items={[
            "PostHog EU Cloud: covered by Standard Contractual Clauses (SCCs) between PostHog and its sub-processors, and by the EU's GDPR which provides a level of protection comparable to Kenya's DPA.",
            'Contabo GmbH: our primary server is in Frankfurt, Germany, a jurisdiction with strong data protection law (GDPR).',
            'Meta/Twilio: covered by their respective data processing agreements and applicable international transfer mechanisms.',
          ]}
        />
        <LegalNote>
          <strong>Note on data localisation:</strong> Section 48(2) of the DPA requires that at
          least one serving copy of personal data on Kenyan residents be maintained on a server
          physically located in Kenya. We are working toward establishing a Kenya-based data replica
          and will update this policy when that is in place.
        </LegalNote>
      </LegalSection>

      <LegalSection title="8. Your Rights Under the DPA">
        <LegalParagraph>
          Under Sections 26–34 of the Kenya Data Protection Act, you have the following rights:
        </LegalParagraph>
        <LegalOrderedList
          items={[
            'Right to be informed — to know what data we hold about you and how we use it.',
            'Right of access — to request a copy of your personal data.',
            'Right to rectification — to correct inaccurate or incomplete data.',
            'Right to erasure — to request deletion of your data (subject to legal retention obligations).',
            'Right to restrict processing — to limit how we use your data in certain circumstances.',
            'Right to data portability — to receive your data in a structured, machine-readable format.',
            'Right to object — to object to processing based on legitimate interests.',
            'Right to withdraw consent — at any time, without affecting prior lawful processing.',
          ]}
        />
        <LegalParagraph>
          To exercise any of these rights, email us at{' '}
          <a href="mailto:privacy@bargainhunters.co.ke" className="text-brand-600 hover:underline">
            privacy@bargainhunters.co.ke
          </a>
          . We will respond within 21 days as required by the DPA.
        </LegalParagraph>
        <LegalParagraph>
          If you are not satisfied with our response, you have the right to lodge a complaint with
          the Office of the Data Protection Commissioner (ODPC) at{' '}
          <a
            href="https://www.odpc.go.ke"
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-600 hover:underline"
          >
            www.odpc.go.ke
          </a>
          .
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="9. Cookies and Tracking">
        <LegalParagraph>
          Our website uses PostHog analytics which operates in cookie-free mode. We do not use
          advertising cookies, retargeting pixels, or third-party tracking cookies. We use a single
          functional session cookie to keep you logged in across pages.
        </LegalParagraph>
        <LegalParagraph>
          You can disable JavaScript in your browser to prevent all analytics tracking. This will
          not affect core Platform functionality.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="10. Children's Privacy">
        <LegalParagraph>
          The Platform is not directed at children under 18. We do not knowingly collect personal
          data from minors. If you believe a minor has provided us with personal data, please
          contact us at{' '}
          <a href="mailto:privacy@bargainhunters.co.ke" className="text-brand-600 hover:underline">
            privacy@bargainhunters.co.ke
          </a>{' '}
          and we will delete it promptly.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="11. Security">
        <LegalList
          items={[
            'HTTPS encryption for all data in transit (TLS 1.2+)',
            "Encrypted passwords (Django's PBKDF2 hashing)",
            'Role-based access controls limiting who can access production data',
            'Regular dependency updates and security patching',
          ]}
        />
        <LegalParagraph>
          In the event of a data breach that is likely to result in risk to your rights, we will
          notify you and the ODPC within 72 hours of becoming aware of it, as required by Section
          43 of the DPA.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="12. Changes to This Policy">
        <LegalParagraph>
          We may update this Privacy Policy from time to time. We will notify registered users by
          email and display a prominent notice on the Platform at least 14 days before material
          changes take effect. Continued use of the Platform after changes take effect constitutes
          acceptance of the updated policy.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="13. Contact">
        <LegalParagraph>
          For any questions about this Privacy Policy or your personal data, contact us at:{' '}
          <a href="mailto:privacy@bargainhunters.co.ke" className="text-brand-600 hover:underline">
            privacy@bargainhunters.co.ke
          </a>
        </LegalParagraph>
        <LegalParagraph>Bargain Hunters | www.bargainhunters.co.ke</LegalParagraph>
      </LegalSection>
    </article>
  )
}
