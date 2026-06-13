import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { AuthStackParams } from '../navigation/AuthStack';
import { useAuth } from '../store/auth';
import { colors } from '../theme';

type Props = NativeStackScreenProps<AuthStackParams, 'Register'>;

export default function RegisterScreen({ navigation }: Props) {
  const { register } = useAuth();
  const [form, setForm] = useState({ firstName: '', lastName: '', phone: '', email: '', dob: '', password: '', confirmPassword: '' });
  const [errors, setErrors] = useState<Partial<typeof form>>({});
  const [apiError, setApiError] = useState('');
  const [consentGiven, setConsentGiven] = useState(false);
  const [consentError, setConsentError] = useState(false);
  const [loading, setLoading] = useState(false);

  function set(key: keyof typeof form, val: string) {
    setForm((f) => ({ ...f, [key]: val }));
    setErrors((e) => ({ ...e, [key]: '' }));
  }

  function validate() {
    const e: Partial<typeof form> = {};
    if (!form.phone.trim()) e.phone = 'Phone is required';
    if (!form.email.trim()) e.email = 'Email is required';
    if (!form.dob.trim()) e.dob = 'Date of birth is required (YYYY-MM-DD)';
    if (form.password.length < 6) e.password = 'Password must be at least 6 characters';
    if (form.password !== form.confirmPassword) e.confirmPassword = 'Passwords do not match';
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleRegister() {
    if (!validate()) return;
    if (!consentGiven) {
      setConsentError(true);
      return;
    }
    setApiError('');
    setLoading(true);
    try {
      await register(form.phone.trim(), form.password, form.email.trim(), form.dob.trim(), form.firstName.trim(), form.lastName.trim());
    } catch (e: any) {
      const data = e?.response?.data;
      setApiError(data?.detail ?? data?.phone?.[0] ?? data?.email?.[0] ?? 'Registration failed.');
    } finally {
      setLoading(false);
    }
  }

  const Field = ({ field, label, placeholder, keyboardType = 'default', secure = false }: {
    field: keyof typeof form; label: string; placeholder: string;
    keyboardType?: 'default' | 'email-address' | 'phone-pad'; secure?: boolean;
  }) => (
    <View style={s.field}>
      <Text style={s.label}>{label}</Text>
      <TextInput
        style={[s.input, errors[field] ? s.inputError : null]}
        placeholder={placeholder}
        placeholderTextColor={colors.textMuted}
        value={form[field]}
        onChangeText={(v) => set(field, v)}
        keyboardType={keyboardType}
        secureTextEntry={secure}
        autoCapitalize={field === 'email' ? 'none' : 'words'}
      />
      {errors[field] ? <Text style={s.fieldError}>{errors[field]}</Text> : null}
    </View>
  );

  return (
    <SafeAreaView style={s.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={s.container} keyboardShouldPersistTaps="handled">
          <TouchableOpacity onPress={() => navigation.goBack()} style={s.back}>
            <Text style={s.backText}>← Back</Text>
          </TouchableOpacity>

          <Text style={s.title}>Create account</Text>
          <Text style={s.subtitle}>Start hunting deals in minutes</Text>

          <View style={s.form}>
            <View style={s.row}>
              <View style={{ flex: 1 }}>
                <Field field="firstName" label="First name" placeholder="Jane" />
              </View>
              <View style={{ flex: 1 }}>
                <Field field="lastName" label="Last name" placeholder="Doe" />
              </View>
            </View>
            <Field field="phone" label="Phone number *" placeholder="+254700000000" keyboardType="phone-pad" />
            <Field field="email" label="Email *" placeholder="you@example.com" keyboardType="email-address" />
            <Field field="dob" label="Date of birth *" placeholder="YYYY-MM-DD" />
            <Field field="password" label="Password *" placeholder="Min 6 characters" secure />
            <Field field="confirmPassword" label="Confirm password *" placeholder="Repeat password" secure />

            {apiError ? <View style={s.errorBox}><Text style={s.errorText}>{apiError}</Text></View> : null}

            <TouchableOpacity
              style={s.checkboxRow}
              onPress={() => { setConsentGiven(!consentGiven); setConsentError(false); }}
              activeOpacity={0.7}
            >
              <View style={[s.checkbox, consentGiven && s.checkboxChecked]}>
                {consentGiven && <Text style={s.checkmark}>✓</Text>}
              </View>
              <Text style={s.consentText}>
                I agree to the{' '}
                <Text style={s.consentLink} onPress={() => navigation.navigate('Privacy')}>
                  Privacy Policy
                </Text>
                {' '}and{' '}
                <Text style={s.consentLink} onPress={() => navigation.navigate('Terms')}>
                  Terms of Service
                </Text>
              </Text>
            </TouchableOpacity>
            {consentError && (
              <Text style={s.consentError}>
                Please accept the Privacy Policy and Terms to continue.
              </Text>
            )}

            <TouchableOpacity
              style={[s.btnPrimary, loading && s.btnDisabled]}
              onPress={handleRegister}
              disabled={loading}
              activeOpacity={0.8}
            >
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Create Account</Text>}
            </TouchableOpacity>
          </View>

          <TouchableOpacity onPress={() => navigation.push('Login')} style={s.switchRow}>
            <Text style={s.switchText}>Already have an account? </Text>
            <Text style={s.switchLink}>Sign In</Text>
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
  form: { gap: 14 },
  row: { flexDirection: 'row', gap: 12 },
  field: { gap: 5 },
  label: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  input: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 12, fontSize: 15, color: colors.textPrimary },
  inputError: { borderColor: '#DC2626' },
  fieldError: { color: '#DC2626', fontSize: 12, marginTop: 2 },
  errorBox: { backgroundColor: '#FEF2F2', borderRadius: 10, padding: 12 },
  errorText: { color: '#DC2626', fontSize: 13 },
  btnPrimary: { backgroundColor: colors.primary, borderRadius: 12, paddingVertical: 16, alignItems: 'center', marginTop: 4 },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  switchRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 24 },
  switchText: { color: colors.textSecondary, fontSize: 14 },
  switchLink: { color: colors.primary, fontSize: 14, fontWeight: '700' },
  checkboxRow: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  checkbox: { width: 20, height: 20, borderRadius: 4, borderWidth: 1.5, borderColor: '#d1d5db', alignItems: 'center', justifyContent: 'center', marginTop: 1 },
  checkboxChecked: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkmark: { color: '#fff', fontSize: 12, fontWeight: '700' },
  consentText: { flex: 1, fontSize: 13, color: colors.textSecondary, lineHeight: 20 },
  consentLink: { color: colors.primary, textDecorationLine: 'underline' },
  consentError: { color: '#dc2626', fontSize: 12, marginTop: -4 },
});
