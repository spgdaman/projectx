import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { subscriptionsApi } from '../lib/api';
import { colors } from '../theme';

const TYPE_ICON: Record<string, string> = { product: '📦', category: '🏷️', retailer: '🏪' };
const TYPE_LABEL: Record<string, string> = { product: 'Product', category: 'Category', retailer: 'Retailer' };

export default function MyAlertsScreen() {
  const qc = useQueryClient();
  const navigation = useNavigation<any>();

  const { data: subs, isLoading } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: () => subscriptionsApi.list().then((r) => r.data.results ?? r.data),
  });

  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      active ? subscriptionsApi.deactivate(id) : subscriptionsApi.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions'] }),
    onError: () => Alert.alert('Error', 'Could not update alert.'),
  });

  const remove = useMutation({
    mutationFn: (id: number) => subscriptionsApi.destroy(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions'] }),
    onError: () => Alert.alert('Error', 'Could not remove alert.'),
  });

  function confirmRemove(id: number) {
    Alert.alert('Remove Alert', 'Are you sure you want to remove this alert?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => remove.mutate(id) },
    ]);
  }

  if (isLoading) {
    return (
      <View style={s.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  const activeSubs = (subs ?? []).filter((s: any) => s.is_active).length;

  if (!subs || subs.length === 0) {
    return (
      <SafeAreaView style={s.safe} edges={['left', 'right', 'bottom']}>
        <View style={s.empty}>
          <Text style={s.emptyIcon}>🔔</Text>
          <Text style={s.emptyTitle}>No alerts yet</Text>
          <Text style={s.emptySubtitle}>Create an alert to get notified about deals you care about</Text>
          <TouchableOpacity style={s.emptyBtn} onPress={() => navigation.navigate('CreateAlert')} activeOpacity={0.8}>
            <Text style={s.emptyBtnText}>🔔 Create your first alert</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.safe} edges={['left', 'right', 'bottom']}>
      <FlatList
        data={subs}
        keyExtractor={(item: any) => String(item.id)}
        contentContainerStyle={s.list}
        ListHeaderComponent={
          <Text style={s.summary}>{activeSubs} active of {subs.length} alerts</Text>
        }
        renderItem={({ item: sub }) => {
          const label = sub.product?.name ?? sub.category?.name ?? sub.retailer?.name ?? '—';
          const subtitle = sub.product?.master_category?.name ?? sub.category?.parent?.name ?? null;
          const expiresAt = sub.expires_at ? new Date(sub.expires_at) : null;
          const isExpired = expiresAt ? expiresAt < new Date() : false;

          return (
            <View style={[s.card, !sub.is_active && s.cardDimmed]}>
              <View style={s.cardLeft}>
                <Text style={s.typeIcon}>{TYPE_ICON[sub.target_type]}</Text>
                <View style={s.cardInfo}>
                  <View style={s.nameRow}>
                    <Text style={s.name} numberOfLines={1}>{label}</Text>
                    <View style={s.typeBadge}>
                      <Text style={s.typeBadgeText}>{TYPE_LABEL[sub.target_type]}</Text>
                    </View>
                    {!sub.is_active && (
                      <View style={s.pausedBadge}>
                        <Text style={s.pausedText}>Paused</Text>
                      </View>
                    )}
                    {isExpired && (
                      <View style={s.expiredBadge}>
                        <Text style={s.expiredText}>Expired</Text>
                      </View>
                    )}
                  </View>
                  {subtitle && <Text style={s.subName}>{subtitle}</Text>}
                  {expiresAt && !isExpired && (
                    <Text style={s.expires}>Expires {expiresAt.toLocaleDateString()}</Text>
                  )}
                </View>
              </View>
              <View style={s.actions}>
                <TouchableOpacity
                  style={[s.toggleBtn, sub.is_active ? s.pauseBtn : s.resumeBtn]}
                  onPress={() => toggle.mutate({ id: sub.id, active: sub.is_active })}
                  disabled={toggle.isPending}
                  activeOpacity={0.8}
                >
                  <Text style={[s.toggleText, !sub.is_active && s.resumeText]}>
                    {sub.is_active ? 'Pause' : 'Resume'}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => confirmRemove(sub.id)} style={s.removeBtn}>
                  <Text style={s.removeText}>✕</Text>
                </TouchableOpacity>
              </View>
            </View>
          );
        }}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background },
  list: { padding: 12 },
  summary: { fontSize: 12, color: colors.textMuted, textAlign: 'center', marginBottom: 10 },
  card: { backgroundColor: colors.surface, borderRadius: 14, borderWidth: 1, borderColor: colors.border, padding: 14, marginBottom: 10, flexDirection: 'row', alignItems: 'center', gap: 10 },
  cardDimmed: { opacity: 0.65 },
  cardLeft: { flex: 1, flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  typeIcon: { fontSize: 24, marginTop: 2 },
  cardInfo: { flex: 1 },
  nameRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 5 },
  name: { fontSize: 14, fontWeight: '600', color: colors.textPrimary, flex: 1 },
  typeBadge: { backgroundColor: '#F3F4F6', borderRadius: 20, paddingHorizontal: 7, paddingVertical: 2 },
  typeBadgeText: { fontSize: 10, color: colors.textSecondary, fontWeight: '600' },
  pausedBadge: { backgroundColor: '#FEF9C3', borderRadius: 20, paddingHorizontal: 7, paddingVertical: 2 },
  pausedText: { fontSize: 10, color: '#92400E', fontWeight: '600' },
  expiredBadge: { backgroundColor: '#FEE2E2', borderRadius: 20, paddingHorizontal: 7, paddingVertical: 2 },
  expiredText: { fontSize: 10, color: '#991B1B', fontWeight: '600' },
  subName: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  expires: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  toggleBtn: { borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1 },
  pauseBtn: { borderColor: colors.border },
  resumeBtn: { borderColor: colors.primary, backgroundColor: colors.primaryLight },
  toggleText: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  resumeText: { color: colors.primary },
  removeBtn: { padding: 6 },
  removeText: { fontSize: 16, color: '#EF4444' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32, gap: 12 },
  emptyIcon: { fontSize: 52 },
  emptyTitle: { fontSize: 20, fontWeight: '700', color: colors.textPrimary },
  emptySubtitle: { fontSize: 14, color: colors.textSecondary, textAlign: 'center', lineHeight: 22 },
  emptyBtn: { backgroundColor: colors.primary, borderRadius: 12, paddingVertical: 14, paddingHorizontal: 24, marginTop: 8 },
  emptyBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
});
