import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, Image } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { AuthStackParams } from '../navigation/AuthStack';
import { colors } from '../theme';

type Props = NativeStackScreenProps<AuthStackParams, 'Landing'>;

export default function LandingScreen({ navigation }: Props) {
  return (
    <SafeAreaView style={s.safe}>
      <View style={s.container}>
        <View style={s.hero}>
          <Text style={s.logo}>🛍️</Text>
          <Text style={s.brand}>Bargain Hunters</Text>
          <Text style={s.tagline}>Find the best deals near you</Text>
        </View>

        <View style={s.features}>
          {[
            { icon: '🔔', text: 'Smart deal alerts on WhatsApp' },
            { icon: '📍', text: 'Location-based bargain tracking' },
            { icon: '⚡', text: 'Real-time price drop notifications' },
          ].map((f) => (
            <View key={f.text} style={s.featureRow}>
              <Text style={s.featureIcon}>{f.icon}</Text>
              <Text style={s.featureText}>{f.text}</Text>
            </View>
          ))}
        </View>

        <View style={s.actions}>
          <TouchableOpacity style={s.btnPrimary} onPress={() => navigation.push('Register')} activeOpacity={0.8}>
            <Text style={s.btnPrimaryText}>Get Started</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.btnOutline} onPress={() => navigation.push('Login')} activeOpacity={0.8}>
            <Text style={s.btnOutlineText}>Sign In</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.primaryLight },
  container: { flex: 1, paddingHorizontal: 28, justifyContent: 'center', gap: 32 },
  hero: { alignItems: 'center', gap: 10 },
  logo: { fontSize: 64 },
  brand: { fontSize: 34, fontWeight: '700', color: colors.primary },
  tagline: { fontSize: 16, color: colors.textSecondary, textAlign: 'center' },
  features: { gap: 14, backgroundColor: colors.surface, borderRadius: 16, padding: 20, borderWidth: 1, borderColor: colors.border },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  featureIcon: { fontSize: 20 },
  featureText: { fontSize: 14, color: colors.textPrimary, flex: 1 },
  actions: { gap: 12 },
  btnPrimary: { backgroundColor: colors.primary, borderRadius: 14, paddingVertical: 16, alignItems: 'center' },
  btnPrimaryText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  btnOutline: { backgroundColor: colors.surface, borderRadius: 14, borderWidth: 2, borderColor: colors.primary, paddingVertical: 14, alignItems: 'center' },
  btnOutlineText: { color: colors.primary, fontSize: 16, fontWeight: '700' },
});
