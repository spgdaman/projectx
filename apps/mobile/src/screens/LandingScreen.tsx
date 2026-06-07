import { View, Text, StyleSheet, TouchableOpacity, Dimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { AuthStackParams } from '../navigation/AuthStack';
import { colors } from '../theme';

type Props = NativeStackScreenProps<AuthStackParams, 'Landing'>;

const { height } = Dimensions.get('window');

const FEATURES = [
  { icon: '🔔', title: 'WhatsApp deal alerts', desc: 'Get notified the moment prices drop' },
  { icon: '🏪', title: 'Top Nairobi retailers', desc: 'Naivas, Quickmart & Chandarana' },
  { icon: '💰', title: 'Save up to 60%', desc: 'On groceries, electronics & more' },
];

export default function LandingScreen({ navigation }: Props) {
  return (
    <View style={s.root}>
      <StatusBar style="light" />

      {/* ── Hero ── */}
      <SafeAreaView style={s.hero} edges={['top', 'left', 'right']}>
        <View style={s.logoMark}>
          <Text style={s.logoMarkText}>BH</Text>
        </View>
        <Text style={s.brand}>Bargain{'\n'}Hunters</Text>
        <Text style={s.tagline}>Kenya's smartest deal tracker.{'\n'}Find bargains before they're gone.</Text>
      </SafeAreaView>

      {/* ── Bottom sheet ── */}
      <View style={s.sheet}>
        {/* Feature list */}
        <View style={s.features}>
          {FEATURES.map((f) => (
            <View key={f.title} style={s.featureRow}>
              <View style={s.featureIconBox}>
                <Text style={s.featureIcon}>{f.icon}</Text>
              </View>
              <View style={s.featureText}>
                <Text style={s.featureTitle}>{f.title}</Text>
                <Text style={s.featureDesc}>{f.desc}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* CTAs */}
        <View style={s.actions}>
          <TouchableOpacity
            style={s.btnPrimary}
            onPress={() => navigation.push('Register')}
            activeOpacity={0.85}
          >
            <Text style={s.btnPrimaryText}>Get Started — It's Free</Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => navigation.push('Login')}
            activeOpacity={0.7}
            style={s.signInRow}
          >
            <Text style={s.signInText}>
              Already have an account?{'  '}
              <Text style={s.signInLink}>Sign In</Text>
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.primary },

  // Hero (orange top section)
  hero: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 28,
    paddingBottom: 32,
    minHeight: height * 0.44,
  },
  logoMark: {
    width: 72,
    height: 72,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.22)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 18,
  },
  logoMarkText: {
    fontSize: 30,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 1,
  },
  brand: {
    fontSize: 42,
    fontWeight: '900',
    color: '#fff',
    textAlign: 'center',
    lineHeight: 46,
    letterSpacing: -1,
  },
  tagline: {
    marginTop: 14,
    fontSize: 15,
    color: 'rgba(255,255,255,0.80)',
    textAlign: 'center',
    lineHeight: 22,
  },

  // Bottom sheet (white)
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    paddingHorizontal: 24,
    paddingTop: 28,
    paddingBottom: 40,
    gap: 24,
  },

  // Features
  features: { gap: 16 },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  featureIconBox: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  featureIcon: { fontSize: 22 },
  featureText: { flex: 1 },
  featureTitle: { fontSize: 14, fontWeight: '700', color: colors.textPrimary },
  featureDesc: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },

  // Actions
  actions: { gap: 12 },
  btnPrimary: {
    backgroundColor: colors.primary,
    borderRadius: 16,
    paddingVertical: 17,
    alignItems: 'center',
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  btnPrimaryText: { color: '#fff', fontSize: 17, fontWeight: '800', letterSpacing: 0.2 },
  signInRow: { alignItems: 'center', paddingVertical: 6 },
  signInText: { fontSize: 14, color: colors.textSecondary },
  signInLink: { color: colors.primary, fontWeight: '700' },
});
