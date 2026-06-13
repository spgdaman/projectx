import type { Metadata } from 'next'
import {
  LegalSection,
  LegalParagraph,
  LegalList,
} from '@/components/legal/LegalPage'

export const metadata: Metadata = {
  title: 'Terms of Service | Bargain Hunters Kenya',
  description:
    'Terms and conditions for using the Bargain Hunters deal aggregation platform.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.bargainhunters.co.ke/terms',
  },
}

export default function TermsPage() {
  return (
    <article>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Terms of Service</h1>
      <p className="text-sm text-gray-400 mb-8">Effective date: June 2026</p>

      <p className="text-gray-600 leading-relaxed mb-8 text-sm">
        Please read these Terms of Service carefully before using the Bargain Hunters Platform. By
        registering an account or using the Platform in any way, you agree to be bound by these
        Terms.
      </p>

      <LegalSection title="1. The Service">
        <LegalParagraph>
          Bargain Hunters provides an online and mobile platform that aggregates supermarket product
          prices and promotional deals from participating retailers in Kenya. We do not sell products
          directly. We provide information only.
        </LegalParagraph>
        <LegalParagraph>
          We scrape pricing data from retailer websites at regular intervals. Prices and
          availability may have changed by the time you visit a retailer. Always verify the current
          price at the point of sale.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="2. Accounts">
        <LegalParagraph>
          To access personalised features (deal alerts, shopping lists), you must register an
          account. You agree to:
        </LegalParagraph>
        <LegalList
          items={[
            'Provide accurate and complete registration information',
            'Keep your login credentials confidential',
            'Notify us immediately of any unauthorised access to your account',
            'Be responsible for all activity under your account',
          ]}
        />
        <LegalParagraph>
          We reserve the right to suspend or terminate accounts that violate these Terms or are used
          fraudulently.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="3. Free and Paid Tiers">
        <LegalParagraph>
          Bargain Hunters offers a free tier and a paid subscription tier. The free tier is limited
          to a maximum of 3 active deal alert subscriptions. The paid tier removes this limit and
          provides additional features as described on the Platform at the time of subscription.
        </LegalParagraph>
        <LegalParagraph>
          Paid subscriptions are billed in Kenyan Shillings via M-Pesa. All fees are
          non-refundable except where required by Kenyan consumer protection law.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="4. Acceptable Use">
        <LegalParagraph>You may not use the Platform to:</LegalParagraph>
        <LegalList
          items={[
            'Scrape, crawl, or systematically extract data from the Platform',
            'Reverse-engineer, decompile, or attempt to access source code',
            'Transmit spam, viruses, or malicious code',
            'Impersonate another person or entity',
            'Use the Platform for any unlawful purpose under Kenyan law',
          ]}
        />
      </LegalSection>

      <LegalSection title="5. Intellectual Property">
        <LegalParagraph>
          All content on the Platform — including the deal aggregation logic, category taxonomy,
          user interface, and brand — is owned by Bargain Hunters or licensed to us. Product names,
          prices, and images remain the property of their respective retailers.
        </LegalParagraph>
        <LegalParagraph>
          You may not reproduce, distribute, or create derivative works from our content without
          prior written consent.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="6. Disclaimers">
        <LegalParagraph>
          The Platform is provided &ldquo;as is.&rdquo; We do not warrant that:
        </LegalParagraph>
        <LegalList
          items={[
            'Prices displayed are current or accurate at the time you visit a retailer',
            'The Platform will be available uninterrupted or error-free',
            'Deal alerts will be delivered in real time',
          ]}
        />
        <LegalParagraph>
          Pricing information is collected from publicly available retailer websites. We are not
          responsible for discrepancies between prices displayed on the Platform and prices at the
          point of sale.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="7. Limitation of Liability">
        <LegalParagraph>
          To the fullest extent permitted by Kenyan law, Bargain Hunters shall not be liable for
          any indirect, incidental, or consequential damages arising from your use of the Platform,
          including but not limited to lost savings or purchasing decisions made in reliance on
          displayed prices.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="8. Governing Law">
        <LegalParagraph>
          These Terms are governed by the laws of Kenya. Any dispute arising from these Terms shall
          be subject to the exclusive jurisdiction of the courts of Nairobi, Kenya.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="9. Changes to These Terms">
        <LegalParagraph>
          We may update these Terms at any time. We will notify registered users by email at least
          14 days before material changes take effect. Continued use of the Platform constitutes
          acceptance.
        </LegalParagraph>
      </LegalSection>

      <LegalSection title="10. Contact">
        <LegalParagraph>
          Questions about these Terms:{' '}
          <a href="mailto:privacy@bargainhunters.co.ke" className="text-brand-600 hover:underline">
            privacy@bargainhunters.co.ke
          </a>
        </LegalParagraph>
      </LegalSection>
    </article>
  )
}
