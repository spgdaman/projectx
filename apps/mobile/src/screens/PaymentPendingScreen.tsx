import { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { paymentsApi } from '../lib/api';
import { colors } from '../theme';

export default function PaymentPendingScreen() {
  const navigation = useNavigation<any>();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    intervalRef.current = setInterval(async () => {
      try {
        const { data } = await paymentsApi.status();
        if (data.status === 'success' || data.payment_status === true) {
          clearInterval(intervalRef.current!);
          Alert.alert('✅ Payment Successful', 'Welcome to Premium! Your alerts are now unlimited.', [
            { text: 'Great!', onPress: () => navigation.reset({ index: 0, routes: [{ name: 'MainTabs' }] }) },
          ]);
        } else if (data.status === 'failed' || data.status === 'cancelled') {
          clearInterval(intervalRef.current!);
          Alert.alert('Payment Failed', 'Your payment did not go through. Please try again.', [
            { text: 'Try Again', onPress: () => navigation.goBack() },
          ]);
        }
      } catch {
        // keep polling
      }
    }, 3000);

    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [navigation]);

  return (
    <SafeAreaView style={s.safe} edges={['left', 'right', 'bottom']}>
      <View style={s.container}>
        <ActivityIndicator size="large" color={colors.primary} style={s.spinner} />
        <Text style={s.title}>Waiting for M-Pesa…</Text>
        <Text style={s.subtitle}>Check your phone and enter your M-Pesa PIN to complete the payment.</Text>
        <Text style={s.hint}>Do not close this screen</Text>
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.primaryLight },
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32, gap: 16 },
  spinner: { marginBottom: 8 },
  title: { fontSize: 22, fontWeight: '700', color: colors.textPrimary, textAlign: 'center' },
  subtitle: { fontSize: 15, color: colors.textSecondary, textAlign: 'center', lineHeight: 23 },
  hint: { fontSize: 12, color: colors.textMuted, marginTop: 8 },
});
