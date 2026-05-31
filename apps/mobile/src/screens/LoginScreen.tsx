import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, SafeAreaView, KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { AuthStackParams } from '../navigation/AuthStack';
import { useAuth } from '../store/auth';
import { colors } from '../theme';

type Props = NativeStackScreenProps<AuthStackParams, 'Login'>;

export default function LoginScreen({ navigation }: Props) {
  const { login } = useAuth();
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    if (!phone.trim() || !password) { setError('Enter phone and password.'); return; }
    setError('');
    setLoading(true);
    try {
      await login(phone.trim(), password);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Invalid credentials.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={s.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={s.container} keyboardShouldPersistTaps="handled">
          <TouchableOpacity onPress={() => navigation.goBack()} style={s.back}>
            <Text style={s.backText}>← Back</Text>
          </TouchableOpacity>

          <Text style={s.title}>Welcome back</Text>
          <Text style={s.subtitle}>Sign in to your account</Text>

          <View style={s.form}>
            <View style={s.field}>
              <Text style={s.label}>Phone number</Text>
              <TextInput
                style={s.input}
                placeholder="+254700000000"
                placeholderTextColor={colors.textMuted}
                value={phone}
                onChangeText={setPhone}
                keyboardType="phone-pad"
                autoCapitalize="none"
              />
            </View>
            <View style={s.field}>
              <Text style={s.label}>Password</Text>
              <TextInput
                style={s.input}
                placeholder="Your password"
                placeholderTextColor={colors.textMuted}
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />
            </View>

            {error ? <View style={s.errorBox}><Text style={s.errorText}>{error}</Text></View> : null}

            <TouchableOpacity
              style={[s.btnPrimary, (loading || !phone || !password) && s.btnDisabled]}
              onPress={handleLogin}
              disabled={loading || !phone.trim() || !password}
              activeOpacity={0.8}
            >
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Sign In</Text>}
            </TouchableOpacity>
          </View>

          <TouchableOpacity onPress={() => navigation.push('Register')} style={s.switchRow}>
            <Text style={s.switchText}>Don't have an account? </Text>
            <Text style={s.switchLink}>Register</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.primaryLight },
  container: { padding: 28, paddingTop: 16, flexGrow: 1 },
  back: { marginBottom: 24 },
  backText: { color: colors.textSecondary, fontSize: 14 },
  title: { fontSize: 30, fontWeight: '700', color: colors.textPrimary, marginBottom: 6 },
  subtitle: { fontSize: 15, color: colors.textSecondary, marginBottom: 28 },
  form: { gap: 16 },
  field: { gap: 6 },
  label: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  input: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 13, fontSize: 15, color: colors.textPrimary },
  errorBox: { backgroundColor: '#FEF2F2', borderRadius: 10, padding: 12 },
  errorText: { color: '#DC2626', fontSize: 13 },
  btnPrimary: { backgroundColor: colors.primary, borderRadius: 12, paddingVertical: 16, alignItems: 'center', marginTop: 4 },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  switchRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 28 },
  switchText: { color: colors.textSecondary, fontSize: 14 },
  switchLink: { color: colors.primary, fontSize: 14, fontWeight: '700' },
});
