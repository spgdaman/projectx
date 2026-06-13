import { ScrollView } from 'react-native';
import {
  LegalH1,
  LegalBody,
  LegalBullet,
  LegalDivider,
} from '../components/LegalContent';

export default function TermsScreen() {
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: '#fff' }}
      contentContainerStyle={{ padding: 20, paddingBottom: 60 }}
    >
      <LegalBody text="Effective date: June 2026" />
      <LegalBody text="Please read these Terms of Service carefully before using the Bargain Hunters Platform. By registering an account or using the Platform in any way, you agree to be bound by these Terms." />

      <LegalDivider />
      <LegalH1 text="1. The Service" />
      <LegalBody text="Bargain Hunters provides an online and mobile platform that aggregates supermarket product prices and promotional deals from participating retailers in Kenya. We do not sell products directly. We provide information only." />
      <LegalBody text="We scrape pricing data from retailer websites at regular intervals. Prices and availability may have changed by the time you visit a retailer. Always verify the current price at the point of sale." />

      <LegalDivider />
      <LegalH1 text="2. Accounts" />
      <LegalBody text="To access personalised features (deal alerts, shopping lists), you must register an account. You agree to:" />
      <LegalBullet text="Provide accurate and complete registration information" />
      <LegalBullet text="Keep your login credentials confidential" />
      <LegalBullet text="Notify us immediately of any unauthorised access to your account" />
      <LegalBullet text="Be responsible for all activity under your account" />
      <LegalBody text="We reserve the right to suspend or terminate accounts that violate these Terms or are used fraudulently." />

      <LegalDivider />
      <LegalH1 text="3. Free and Paid Tiers" />
      <LegalBody text="Bargain Hunters offers a free tier and a paid subscription tier. The free tier is limited to a maximum of 3 active deal alert subscriptions. The paid tier removes this limit and provides additional features as described on the Platform at the time of subscription." />
      <LegalBody text="Paid subscriptions are billed in Kenyan Shillings via M-Pesa. All fees are non-refundable except where required by Kenyan consumer protection law." />

      <LegalDivider />
      <LegalH1 text="4. Acceptable Use" />
      <LegalBody text="You may not use the Platform to:" />
      <LegalBullet text="Scrape, crawl, or systematically extract data from the Platform" />
      <LegalBullet text="Reverse-engineer, decompile, or attempt to access source code" />
      <LegalBullet text="Transmit spam, viruses, or malicious code" />
      <LegalBullet text="Impersonate another person or entity" />
      <LegalBullet text="Use the Platform for any unlawful purpose under Kenyan law" />

      <LegalDivider />
      <LegalH1 text="5. Intellectual Property" />
      <LegalBody text="All content on the Platform — including the deal aggregation logic, category taxonomy, user interface, and brand — is owned by Bargain Hunters or licensed to us. Product names, prices, and images remain the property of their respective retailers." />
      <LegalBody text="You may not reproduce, distribute, or create derivative works from our content without prior written consent." />

      <LegalDivider />
      <LegalH1 text="6. Disclaimers" />
      <LegalBody text='The Platform is provided "as is." We do not warrant that:' />
      <LegalBullet text="Prices displayed are current or accurate at the time you visit a retailer" />
      <LegalBullet text="The Platform will be available uninterrupted or error-free" />
      <LegalBullet text="Deal alerts will be delivered in real time" />
      <LegalBody text="Pricing information is collected from publicly available retailer websites. We are not responsible for discrepancies between prices displayed on the Platform and prices at the point of sale." />

      <LegalDivider />
      <LegalH1 text="7. Limitation of Liability" />
      <LegalBody text="To the fullest extent permitted by Kenyan law, Bargain Hunters shall not be liable for any indirect, incidental, or consequential damages arising from your use of the Platform, including but not limited to lost savings or purchasing decisions made in reliance on displayed prices." />

      <LegalDivider />
      <LegalH1 text="8. Governing Law" />
      <LegalBody text="These Terms are governed by the laws of Kenya. Any dispute arising from these Terms shall be subject to the exclusive jurisdiction of the courts of Nairobi, Kenya." />

      <LegalDivider />
      <LegalH1 text="9. Changes to These Terms" />
      <LegalBody text="We may update these Terms at any time. We will notify registered users by email at least 14 days before material changes take effect. Continued use of the Platform constitutes acceptance." />

      <LegalDivider />
      <LegalH1 text="10. Contact" />
      <LegalBody text="Questions about these Terms: privacy@bargainhunters.co.ke" />
    </ScrollView>
  );
}
