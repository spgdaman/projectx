import { Text, View, StyleSheet } from 'react-native';
import { colors } from '../theme';

export function LegalH1({ text }: { text: string }) {
  return <Text style={s.h1}>{text}</Text>;
}

export function LegalH2({ text }: { text: string }) {
  return <Text style={s.h2}>{text}</Text>;
}

export function LegalBody({ text }: { text: string }) {
  return <Text style={s.body}>{text}</Text>;
}

export function LegalBullet({ text }: { text: string }) {
  return (
    <View style={s.bulletRow}>
      <Text style={s.bulletDot}>•</Text>
      <Text style={[s.body, s.bulletText]}>{text}</Text>
    </View>
  );
}

export function LegalNumbered({ n, text }: { n: number; text: string }) {
  return (
    <View style={s.bulletRow}>
      <Text style={s.bulletDot}>{n}.</Text>
      <Text style={[s.body, s.bulletText]}>{text}</Text>
    </View>
  );
}

export function LegalInfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={s.infoRow}>
      <Text style={s.infoLabel}>{label}:</Text>
      <Text style={s.infoValue}>{value}</Text>
    </View>
  );
}

export function LegalDivider() {
  return <View style={s.divider} />;
}

const s = StyleSheet.create({
  h1: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: 6,
    marginTop: 16,
  },
  h2: {
    fontSize: 17,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: 4,
    marginTop: 14,
  },
  body: {
    fontSize: 14,
    color: '#333333',
    lineHeight: 22,
    marginBottom: 8,
  },
  bulletRow: {
    flexDirection: 'row',
    marginBottom: 5,
    paddingRight: 4,
  },
  bulletDot: {
    fontSize: 14,
    color: colors.textSecondary,
    marginRight: 8,
    lineHeight: 22,
    minWidth: 16,
  },
  bulletText: {
    flex: 1,
    marginBottom: 0,
  },
  infoRow: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 4,
  },
  infoLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textPrimary,
    minWidth: 70,
  },
  infoValue: {
    fontSize: 13,
    color: colors.textSecondary,
    flex: 1,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: 12,
  },
});
