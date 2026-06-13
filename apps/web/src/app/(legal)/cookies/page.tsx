import type { Metadata } from 'next'
import {
  LegalSection,
  LegalSubSection,
  LegalParagraph,
  LegalList,
  LegalOrderedList,
} from '@/components/legal/LegalPage'

export const metadata: Metadata = {
  title: 'Cookie & Analytics Notice | Bargain Hunters',
  description: 'Information about cookies and analytics used on Bargain Hunters.',
  robots: { index: false, follow: false },
}

export default function CookiesPage() {
  return (
    <article>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Cookie &amp; Analytics Notice</h1>
      <p className="text-sm text-gray-400 mb-8">Effective date: June 2026</p>

      <p className="text-gray-600 leading-relaxed mb-8 text-sm">
        This notice explains what tracking technologies Bargain Hunters uses on our website and
        mobile application, what data is collected, and your choices.
      </p>

      <LegalSection title="1. What We Use">
        <LegalSubSection title="1.1 Session cookie (strictly necessary)">
          <LegalParagraph>
            We use a single session cookie (Django&apos;s <code className="bg-gray-100 px-1 rounded text-xs">sessionid</code>) to keep you logged in while you browse.
            This cookie:
          </LegalParagraph>
          <LegalList
            items={[
              'Is deleted when you close your browser',
              'Contains only an anonymous session identifier — not your personal data',
              'Cannot be disabled without breaking account functionality',
            ]}
          />
        </LegalSubSection>

        <LegalSubSection title="1.2 PostHog Analytics (functional/analytical)">
          <LegalParagraph>
            We use PostHog (EU Cloud, Frankfurt Germany) to understand how users interact with the
            Platform. PostHog collects:
          </LegalParagraph>
          <LegalList
            items={[
              'Pages visited and time spent on each page',
              'Clicks on deals, categories, search queries, and navigation elements',
              'Shopping list and alert subscription actions',
              'Device type, browser, and approximate location (country/city)',
              'Session recordings (screen activity — all text inputs are masked)',
            ]}
          />
          <LegalParagraph>
            PostHog operates in cookie-free mode on our Platform. It uses a temporary in-memory
            identifier rather than a persistent cookie. This means it does not require a cookie
            consent banner under the Kenya DPA or EU ePrivacy Directive.
          </LegalParagraph>
          <LegalParagraph>
            PostHog data is retained for 24 months (events) and 90 days (session recordings).
          </LegalParagraph>
        </LegalSubSection>
      </LegalSection>

      <LegalSection title="2. What We Do NOT Use">
        <LegalList
          items={[
            'Google Analytics or Google Ads pixels',
            'Facebook Pixel or Meta tracking',
            'Advertising or retargeting cookies',
            'Cross-site tracking technologies',
          ]}
        />
      </LegalSection>

      <LegalSection title="3. Your Choices">
        <LegalParagraph>You can opt out of PostHog analytics by:</LegalParagraph>
        <LegalOrderedList
          items={[
            'Enabling "Do Not Track" in your browser settings — PostHog respects this signal',
            'Disabling JavaScript for bargainhunters.co.ke in your browser',
            'Emailing privacy@bargainhunters.co.ke to request exclusion from analytics',
          ]}
        />
        <LegalParagraph>
          Opting out of analytics does not affect your ability to use the Platform or receive deal
          alerts.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="4. Cross-Border Transfer">
        <LegalParagraph>
          PostHog analytics data is processed in Frankfurt, Germany (EU). The transfer is covered
          by Standard Contractual Clauses and PostHog&apos;s data processing agreement. See our{' '}
          <a href="/privacy" className="text-brand-600 hover:underline">
            Privacy Policy
          </a>{' '}
          for full details.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="5. Contact">
        <LegalParagraph>
          For questions about tracking:{' '}
          <a href="mailto:privacy@bargainhunters.co.ke" className="text-brand-600 hover:underline">
            privacy@bargainhunters.co.ke
          </a>
        </LegalParagraph>
      </LegalSection>
    </article>
  )
}
