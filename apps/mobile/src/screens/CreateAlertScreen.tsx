import { useState, useRef } from 'react';
import {
  View, Text, StyleSheet, FlatList, TextInput, TouchableOpacity,
  ActivityIndicator, Alert,
} from 'react-native';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { productsApi, categoriesApi, retailersApi, subscriptionsApi } from '../lib/api';
import { colors } from '../theme';

type TargetType = 'product' | 'category' | 'retailer';

const TABS: { key: TargetType; label: string; icon: string; desc: string }[] = [
  { key: 'product', label: 'Product', icon: '📦', desc: 'Track a specific product price' },
  { key: 'category', label: 'Category', icon: '🏷️', desc: 'All deals in a category' },
  { key: 'retailer', label: 'Retailer', icon: '🏪', desc: 'Deals from a retailer' },
];

export default function CreateAlertScreen() {
  const qc = useQueryClient();
  const navigation = useNavigation<any>();
  const [type, setType] = useState<TargetType>('product');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedName, setSelectedName] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleSearch(val: string) {
    setSearch(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(val), 350);
  }

  function switchTab(t: TargetType) {
    setType(t);
    setSearch('');
    setDebouncedSearch('');
    setSelectedId(null);
    setSelectedName('');
  }

  const productsQ = useQuery({
    queryKey: ['products', debouncedSearch],
    queryFn: () => productsApi.list({ search: debouncedSearch || undefined }).then((r) => r.data?.results ?? r.data ?? []),
    enabled: type === 'product',
  });

  const categoriesQ = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list().then((r) => r.data?.results ?? r.data ?? []),
    enabled: type === 'category',
  });

  const retailersQ = useQuery({
    queryKey: ['retailers'],
    queryFn: () => retailersApi.list().then((r) => r.data?.results ?? r.data ?? []),
    enabled: type === 'retailer',
  });

  const rawItems: any[] =
    type === 'product' ? (productsQ.data ?? []) :
    type === 'category' ? (categoriesQ.data ?? []) :
    (retailersQ.data ?? []);

  const items: any[] = type !== 'product' && search
    ? rawItems.filter((i: any) => i.name.toLowerCase().includes(search.toLowerCase()))
    : rawItems;

  const isLoading = productsQ.isLoading || categoriesQ.isLoading || retailersQ.isLoading;

  const createMutation = useMutation({
    mutationFn: () => {
      if (!selectedId) throw new Error('Nothing selected');
      return subscriptionsApi.create({
        target_type: type,
        product_id: type === 'product' ? selectedId : undefined,
        category_id: type === 'category' ? selectedId : undefined,
        retailer_id: type === 'retailer' ? selectedId : undefined,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscriptions'] });
      Alert.alert('🔔 Alert created!', `You'll be notified when new deals appear.`, [
        { text: 'View Alerts', onPress: () => navigation.navigate('MyAlerts') },
        { text: 'OK' },
      ]);
      setSelectedId(null);
      setSelectedName('');
    },
    onError: (e: any) => {
      const data = e?.response?.data;
      Alert.alert('Error', data?.detail ?? data?.non_field_errors?.[0] ?? 'Could not create alert.');
    },
  });

  return (
    <SafeAreaView style={s.safe} edges={['left', 'right', 'bottom']}>
      <View style={s.tabs}>
        {TABS.map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[s.tab, type === tab.key && s.tabActive]}
            onPress={() => switchTab(tab.key)}
            activeOpacity={0.8}
          >
            <Text style={s.tabIcon}>{tab.icon}</Text>
            <Text style={[s.tabLabel, type === tab.key && s.tabLabelActive]}>{tab.label}</Text>
            <Text style={s.tabDesc} numberOfLines={2}>{tab.desc}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={s.searchWrap}>
        <TextInput
          style={s.searchInput}
          placeholder={`Search ${type}s…`}
          placeholderTextColor={colors.textMuted}
          value={search}
          onChangeText={handleSearch}
        />
      </View>

      {isLoading ? (
        <View style={s.center}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : items.length === 0 ? (
        <View style={s.empty}>
          <Text style={s.emptyText}>No {type}s found{search ? ` for "${search}"` : ''}</Text>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item: any) => String(item.id)}
          contentContainerStyle={s.list}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[s.listItem, selectedId === item.id && s.listItemSelected]}
              onPress={() => { setSelectedId(item.id); setSelectedName(item.name); }}
              activeOpacity={0.7}
            >
              <View style={{ flex: 1 }}>
                <Text style={[s.itemName, selectedId === item.id && s.itemNameSelected]}>{item.name}</Text>
                {item.retailer && <Text style={s.itemSub}>{item.retailer.name}</Text>}
                {item.master_category && <Text style={s.itemSub}>{item.master_category.name}</Text>}
              </View>
              {selectedId === item.id && <Text style={s.check}>✓</Text>}
            </TouchableOpacity>
          )}
        />
      )}

      {selectedId && (
        <View style={s.footer}>
          <View style={s.footerInfo}>
            <Text style={s.footerLabel}>{type.toUpperCase()} SELECTED</Text>
            <Text style={s.footerName} numberOfLines={1}>{selectedName}</Text>
          </View>
          <TouchableOpacity
            style={[s.createBtn, createMutation.isPending && s.createBtnDisabled]}
            onPress={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            activeOpacity={0.8}
          >
            {createMutation.isPending
              ? <ActivityIndicator color="#fff" size="small" />
              : <Text style={s.createBtnText}>🔔 Create Alert</Text>}
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  tabs: { flexDirection: 'row', gap: 8, padding: 12 },
  tab: { flex: 1, alignItems: 'center', padding: 10, borderRadius: 12, borderWidth: 2, borderColor: colors.border, backgroundColor: colors.surface },
  tabActive: { borderColor: colors.primary, backgroundColor: colors.primaryLight },
  tabIcon: { fontSize: 22, marginBottom: 4 },
  tabLabel: { fontSize: 12, fontWeight: '700', color: colors.textSecondary },
  tabLabelActive: { color: colors.primary },
  tabDesc: { fontSize: 10, color: colors.textMuted, textAlign: 'center', marginTop: 2 },
  searchWrap: { paddingHorizontal: 12, paddingBottom: 8 },
  searchInput: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, fontSize: 14, color: colors.textPrimary },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyText: { color: colors.textMuted, fontSize: 14 },
  list: { paddingHorizontal: 12 },
  listItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 16, backgroundColor: colors.surface, borderRadius: 12, marginBottom: 8, borderWidth: 1, borderColor: colors.border },
  listItemSelected: { borderColor: colors.primary, backgroundColor: colors.primaryLight },
  itemName: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  itemNameSelected: { color: colors.primary },
  itemSub: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  check: { fontSize: 18, color: colors.primary, fontWeight: '700', marginLeft: 8 },
  footer: { flexDirection: 'row', alignItems: 'center', padding: 12, backgroundColor: colors.primaryLight, borderTopWidth: 1, borderColor: colors.primaryAccent, gap: 12 },
  footerInfo: { flex: 1 },
  footerLabel: { fontSize: 10, fontWeight: '700', color: colors.primary, letterSpacing: 0.5 },
  footerName: { fontSize: 14, fontWeight: '700', color: colors.primaryDark },
  createBtn: { backgroundColor: colors.primary, borderRadius: 10, paddingVertical: 12, paddingHorizontal: 16, alignItems: 'center', minWidth: 130 },
  createBtnDisabled: { opacity: 0.6 },
  createBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
});
