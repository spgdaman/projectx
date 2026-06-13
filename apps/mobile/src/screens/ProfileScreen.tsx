import { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { useAuth } from '../store/auth';
import { subscriptionsApi } from '../lib/api';
import { colors } from '../theme';

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={s.row}>
      <Text style={s.rowLabel}>{label}</Text>
      <Text style={s.rowValue}>{value}</Text>
    </View>
  );
}

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const navigation = useNavigation<any>();

  const { data: subs } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: () => subscriptionsApi.list().then((r) => r.data.results ?? r.data),
  });

  if (!user) return null;

  const displayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username;
  const initials = ((user.first_name?.[0] ?? '') + (user.last_name?.[0] ?? '')).toUpperCase() || user.username?.[0]?.toUpperCase() || 'U';
  const activeSubs = (subs ?? []).filter((s: any) => s.is_active).length;
  const totalSubs = (subs ?? []).length;
  const dobFormatted = user.date_of_birth
    ? new Date(user.date_of_birth).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : null;

  function handleLogout() {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: () => logout() },
    ]);
  }

  return (
    <SafeAreaView style={s.safe} edges={['left', 'right', 'bottom']}>
      <ScrollView contentContainerStyle={s.container}>

        {/* Identity */}
        <View style={s.card}>
          <View style={s.identityRow}>
            <View style={s.avatar}>
              <Text style={s.avatarText}>{initials}</Text>
            </View>
            <View style={s.identityInfo}>
              <Text style={s.displayName}>{displayName}</Text>
              <Text style={s.phoneText}>{user.phone_number}</Text>
              {user.email ? <Text style={s.emailText}>{user.email}</Text> : null}
            </View>
          </View>
          <View style={s.badgeRow}>
            {user.is_staff && (
              <View style={s.adminBadge}><Text style={s.adminBadgeText}>Admin</Text></View>
            )}
            <View style={user.payment_status ? s.premiumBadge : s.freeBadge}>
              <Text style={user.payment_status ? s.premiumText : s.freeText}>
                {user.payment_status ? '⭐ Premium' : 'Free'}
              </Text>
            </View>
          </View>
        </View>

        {/* Plan */}
        <View style={s.card}>
          <Text style={s.sectionLabel}>SUBSCRIPTION</Text>
          <View style={s.planRow}>
            <View style={{ flex: 1 }}>
              <Text style={s.planName}>{user.payment_status ? '⭐ Premium' : 'Free Plan'}</Text>
              <Text style={s.planDesc}>
                {user.payment_status
                  ? 'Unlimited deal alerts and subscriptions'
                  : `Up to 3 active alerts · ${activeSubs} used`}
              </Text>
            </View>
            {!user.payment_status && (
              <TouchableOpacity
                style={s.upgradeBtn}
                onPress={() => navigation.navigate('Upgrade')}
                activeOpacity={0.8}
              >
                <Text style={s.upgradeBtnText}>Upgrade</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>

        {/* Alerts summary */}
        <View style={s.card}>
          <View style={s.sectionHeader}>
            <Text style={s.sectionLabel}>MY ALERTS</Text>
            <TouchableOpacity onPress={() => navigation.navigate('MyAlerts')}>
              <Text style={s.manageLink}>Manage →</Text>
            </TouchableOpacity>
          </View>
          <View style={s.statsRow}>
            <View style={[s.statBox, s.statBoxPrimary]}>
              <Text style={s.statNumber}>{activeSubs}</Text>
              <Text style={s.statLabel}>Active</Text>
            </View>
            <View style={[s.statBox, s.statBoxGray]}>
              <Text style={[s.statNumber, { color: colors.textPrimary }]}>{totalSubs}</Text>
              <Text style={s.statLabel}>Total</Text>
            </View>
          </View>
        </View>

        {/* Account details */}
        <View style={s.card}>
          <Text style={s.sectionLabel}>ACCOUNT DETAILS</Text>
          <Row label="Full name" value={displayName} />
          <Row label="Phone" value={user.phone_number} />
          <Row label="Email" value={user.email || '—'} />
          <Row label="Date of birth" value={dobFormatted ?? '—'} />
          <Row label="Username" value={user.username} />
          <Row label="Plan" value={user.payment_status ? 'Premium' : 'Free'} />
        </View>

        {/* Sign out */}
        <View style={s.card}>
          <Text style={s.sectionLabel}>ACCOUNT ACTIONS</Text>
          <TouchableOpacity style={s.signOutBtn} onPress={handleLogout} activeOpacity={0.8}>
            <Text style={s.signOutText}>Sign Out</Text>
          </TouchableOpacity>
        </View>

        {/* Legal */}
        <View style={s.card}>
          <Text style={s.sectionLabel}>LEGAL</Text>
          <TouchableOpacity
            style={s.legalItem}
            onPress={() => navigation.navigate('Privacy')}
            activeOpacity={0.7}
          >
            <Text style={s.legalItemText}>Privacy Policy</Text>
            <Text style={s.chevron}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={s.legalItem}
            onPress={() => navigation.navigate('Terms')}
            activeOpacity={0.7}
          >
            <Text style={s.legalItemText}>Terms of Service</Text>
            <Text style={s.chevron}>›</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[s.legalItem, { borderBottomWidth: 0 }]}
            onPress={() => navigation.navigate('Cookies')}
            activeOpacity={0.7}
          >
            <Text style={s.legalItemText}>Cookie &amp; Analytics Notice</Text>
            <Text style={s.chevron}>›</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  container: { padding: 12, gap: 10, paddingBottom: 32 },
  card: { backgroundColor: colors.surface, borderRadius: 16, borderWidth: 1, borderColor: colors.border, padding: 16 },
  identityRow: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 12 },
  avatar: { width: 60, height: 60, borderRadius: 30, backgroundColor: colors.primary, justifyContent: 'center', alignItems: 'center' },
  avatarText: { color: '#fff', fontSize: 22, fontWeight: '700' },
  identityInfo: { flex: 1 },
  displayName: { fontSize: 18, fontWeight: '700', color: colors.textPrimary },
  phoneText: { fontSize: 14, color: colors.textSecondary, marginTop: 2 },
  emailText: { fontSize: 12, color: colors.textMuted, marginTop: 1 },
  badgeRow: { flexDirection: 'row', gap: 8 },
  adminBadge: { backgroundColor: '#FEE2E2', borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4 },
  adminBadgeText: { fontSize: 12, color: '#991B1B', fontWeight: '700' },
  premiumBadge: { backgroundColor: '#FEF9C3', borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4 },
  premiumText: { fontSize: 12, color: '#92400E', fontWeight: '700' },
  freeBadge: { backgroundColor: '#F3F4F6', borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4 },
  freeText: { fontSize: 12, color: colors.textSecondary, fontWeight: '700' },
  sectionLabel: { fontSize: 11, fontWeight: '700', color: colors.textMuted, letterSpacing: 0.8, marginBottom: 10 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  manageLink: { fontSize: 13, color: colors.primary, fontWeight: '600' },
  planRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  planName: { fontSize: 17, fontWeight: '700', color: colors.textPrimary },
  planDesc: { fontSize: 13, color: colors.textSecondary, marginTop: 3 },
  upgradeBtn: { backgroundColor: colors.primary, borderRadius: 10, paddingVertical: 10, paddingHorizontal: 16 },
  upgradeBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  statsRow: { flexDirection: 'row', gap: 10 },
  statBox: { flex: 1, borderRadius: 12, padding: 14, alignItems: 'center' },
  statBoxPrimary: { backgroundColor: colors.primaryLight },
  statBoxGray: { backgroundColor: colors.background },
  statNumber: { fontSize: 28, fontWeight: '700', color: colors.primary },
  statLabel: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderColor: colors.background },
  rowLabel: { fontSize: 13, color: colors.textSecondary },
  rowValue: { fontSize: 13, fontWeight: '600', color: colors.textPrimary, maxWidth: '60%', textAlign: 'right' },
  signOutBtn: { borderWidth: 1.5, borderColor: '#FCA5A5', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  signOutText: { color: '#DC2626', fontSize: 14, fontWeight: '700' },
  legalItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderColor: colors.background },
  legalItemText: { fontSize: 14, color: colors.textPrimary },
  chevron: { fontSize: 20, color: colors.textMuted },
});
