import { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { useMutation } from '@tanstack/react-query';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { paymentsApi } from '../lib/api';
import { colors } from '../theme';

const FEATURES = [
  'Unlimited deal alert subscriptions',
  'Unlimited notifications',
  'Priority deal updates',
  '30-day subscription',
];

export default function UpgradeScreen() {
  const navigation = useNavigation<any>();
  const [phone, setPhone] = useState('');
  const [error, setError] = useState('');

  const initiate = useMutation({
    mutationFn: () => paymentsApi.initiate(phone.trim()),
    onSuccess: () => navigation.replace('PaymentPending'),
    onError: (e: any) => setError(e?.response?.data?.detail ?? 'Payment failed. Try again.'),
  });

  return (
    <SafeAreaView style={s.safe} edges={['left', 'right', 'bottom']}>
      <ScrollView contentContainerStyle={s.container}>
        <View style={s.pricingCard}>
          <View style={s.priceRow}>
            <Text style={s.amount}>KES 299</Text>
            <Text style={s.period}>/ month</Text>
          </View>

          <View style={s.features}>
            {FEATURES.map((f) => (
              <View key={f} style={s.featureRow}>
                <Text style={s.check}>✓</Text>
                <Text style={s.featureText}>{f}</Text>
              </View>
            ))}
          </View>

          <View style={s.paySection}>
            <Text style={s.fieldLabel}>M-Pesa phone number</Text>
            <TextInput
              style={s.input}
              placeholder="+254700000000"
              placeholderTextColor={colors.textMuted}
              value={phone}
              onChangeText={(v) => { setPhone(v); setError(''); }}
              keyboardType="phone-pad"
            />

            {error ? (
              <View style={s.errorBox}>
                <Text style={s.errorText}>{error}</Text>
              </View>
            ) : null}

            <TouchableOpacity
              style={[s.payBtn, (!phone.trim() || initiate.isPending) && s.payBtnDisabled]}
              onPress={() => initiate.mutate()}
              disabled={!phone.trim() || initiate.isPending}
              activeOpacity={0.8}
            >
              {initiate.isPending
                ? <ActivityIndicator color="#fff" />
                : <Text style={s.payBtnText}>Pay via M-Pesa</Text>}
            </TouchableOpacity>

            <Text style={s.hint}>You'll receive a prompt on your phone. Enter your M-Pesa PIN to complete.</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  container: { padding: 16, paddingBottom: 40 },
  pricingCard: { backgroundColor: colors.surface, borderRadius: 20, borderWidth: 1, borderColor: colors.border, padding: 24, gap: 20 },
  priceRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 4 },
  amount: { fontSize: 38, fontWeight: '800', color: colors.primary },
  period: { fontSize: 14, color: colors.textMuted, marginBottom: 6 },
  features: { gap: 10 },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  check: { fontSize: 16, color: colors.primaryMedium, fontWeight: '700' },
  featureText: { fontSize: 14, color: colors.textPrimary },
  paySection: { gap: 12 },
  fieldLabel: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  input: { backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 13, fontSize: 15, color: colors.textPrimary },
  errorBox: { backgroundColor: '#FEF2F2', borderRadius: 10, padding: 12 },
  errorText: { color: '#DC2626', fontSize: 13 },
  payBtn: { backgroundColor: colors.primary, borderRadius: 12, paddingVertical: 16, alignItems: 'center' },
  payBtnDisabled: { opacity: 0.5 },
  payBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  hint: { fontSize: 12, color: colors.textMuted, textAlign: 'center', lineHeight: 18 },
});
