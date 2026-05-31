import { useState, useRef, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TextInput, TouchableOpacity,
  ActivityIndicator, Modal, Image, Alert, Dimensions,
} from 'react-native';
import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SafeAreaView } from 'react-native-safe-area-context';
import { dealsApi, retailersApi, categoriesApi, subscriptionsApi } from '../lib/api';
import { colors } from '../theme';

const { width } = Dimensions.get('window');
const CARD_WIDTH = (width - 48) / 2;

const CATEGORY_ICONS: Record<string, string> = {
  electronics: '📱', appliances: '🏠', food: '🛒', beverages: '🥤',
  fresh: '🥬', 'personal care': '🧴', beauty: '💄', 'home care': '🧹',
  household: '🏠', kitchen: '🍳', liquor: '🍷', fashion: '👗', textile: '👕', pet: '🐾',
};

function categoryIcon(name?: string | null) {
  if (!name) return '🏷️';
  const lower = name.toLowerCase();
  for (const [k, v] of Object.entries(CATEGORY_ICONS)) {
    if (lower.includes(k)) return v;
  }
  return '🏷️';
}

function DealCard({ deal, onAlert }: { deal: any; onAlert: (deal: any) => void }) {
  const price = Number(deal.current_price);
  const oldPrice = deal.old_price != null ? Number(deal.old_price) : null;
  const icon = categoryIcon(deal.product?.master_category?.name);
  const [imgFailed, setImgFailed] = useState(false);
  const hasImage = !!deal.product?.image_url && !imgFailed;

  return (
    <View style={[dc.card, { width: CARD_WIDTH }]}>
      <View style={dc.imgBox}>
        {hasImage ? (
          <Image source={{ uri: deal.product.image_url }} style={dc.img} onError={() => setImgFailed(true)} />
        ) : (
          <Text style={dc.imgIcon}>{icon}</Text>
        )}
        {deal.discount_pct != null && deal.discount_pct > 0 && (
          <View style={dc.badge}>
            <Text style={dc.badgeText}>-{Math.round(deal.discount_pct)}%</Text>
          </View>
        )}
      </View>
      <View style={dc.body}>
        <View style={dc.retailerBadge}>
          <Text style={dc.retailerText}>{deal.retailer?.name}</Text>
        </View>
        <Text style={dc.name} numberOfLines={2}>{deal.product?.name}</Text>
        {deal.product?.master_category && (
          <Text style={dc.category} numberOfLines={1}>{deal.product.master_category.name}</Text>
        )}
        <View style={dc.priceRow}>
          <Text style={dc.price}>KES {price.toLocaleString()}</Text>
          {oldPrice != null && oldPrice > price && (
            <Text style={dc.oldPrice}>{oldPrice.toLocaleString()}</Text>
          )}
        </View>
        <TouchableOpacity style={dc.alertBtn} onPress={() => onAlert(deal)} activeOpacity={0.8}>
          <Text style={dc.alertBtnText}>🔔 Alert</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const dc = StyleSheet.create({
  card: { backgroundColor: colors.surface, borderRadius: 14, borderWidth: 1, borderColor: colors.border, overflow: 'hidden', marginBottom: 12 },
  imgBox: { height: 110, backgroundColor: colors.primaryLight, justifyContent: 'center', alignItems: 'center' },
  img: { width: '100%', height: '100%', resizeMode: 'contain' },
  imgIcon: { fontSize: 44, opacity: 0.6 },
  badge: { position: 'absolute', top: 6, right: 6, backgroundColor: '#EF4444', borderRadius: 20, paddingHorizontal: 6, paddingVertical: 2 },
  badgeText: { color: '#fff', fontSize: 10, fontWeight: '800' },
  body: { padding: 10, gap: 4 },
  retailerBadge: { backgroundColor: colors.primaryAccent, borderRadius: 20, paddingHorizontal: 8, paddingVertical: 2, alignSelf: 'flex-start' },
  retailerText: { color: colors.primaryDark, fontSize: 10, fontWeight: '700' },
  name: { fontSize: 12, fontWeight: '600', color: colors.textPrimary, lineHeight: 17 },
  category: { fontSize: 11, color: colors.textMuted },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: 5, marginTop: 2 },
  price: { fontSize: 14, fontWeight: '800', color: colors.primary },
  oldPrice: { fontSize: 11, color: colors.textMuted, textDecorationLine: 'line-through' },
  alertBtn: { backgroundColor: colors.primary, borderRadius: 8, paddingVertical: 7, alignItems: 'center', marginTop: 4 },
  alertBtnText: { color: '#fff', fontSize: 11, fontWeight: '700' },
});

type Filter = { id: number; name: string } | null;

function FilterModal({ visible, items, selected, onSelect, onClose, title }: {
  visible: boolean; items: { id: number; name: string }[]; selected: Filter;
  onSelect: (f: Filter) => void; onClose: () => void; title: string;
}) {
  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <SafeAreaView style={fm.safe}>
        <View style={fm.header}>
          <Text style={fm.title}>{title}</Text>
          <TouchableOpacity onPress={onClose}><Text style={fm.close}>Done</Text></TouchableOpacity>
        </View>
        <TouchableOpacity style={fm.item} onPress={() => { onSelect(null); onClose(); }}>
          <Text style={[fm.itemText, !selected && fm.itemSelected]}>All</Text>
          {!selected && <Text style={fm.check}>✓</Text>}
        </TouchableOpacity>
        <FlatList
          data={items}
          keyExtractor={(i) => String(i.id)}
          renderItem={({ item }) => (
            <TouchableOpacity style={fm.item} onPress={() => { onSelect(item); onClose(); }}>
              <Text style={[fm.itemText, selected?.id === item.id && fm.itemSelected]}>{item.name}</Text>
              {selected?.id === item.id && <Text style={fm.check}>✓</Text>}
            </TouchableOpacity>
          )}
        />
      </SafeAreaView>
    </Modal>
  );
}

const fm = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderColor: colors.border },
  title: { fontSize: 18, fontWeight: '700', color: colors.textPrimary },
  close: { fontSize: 16, color: colors.primary, fontWeight: '600' },
  item: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 14, borderBottomWidth: 1, borderColor: colors.border },
  itemText: { fontSize: 15, color: colors.textPrimary },
  itemSelected: { color: colors.primary, fontWeight: '600' },
  check: { color: colors.primary, fontWeight: '700', fontSize: 16 },
});

export default function DealsScreen() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [retailer, setRetailer] = useState<Filter>(null);
  const [category, setCategory] = useState<Filter>(null);
  const [showRetailerModal, setShowRetailerModal] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [alertingId, setAlertingId] = useState<number | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleSearch(val: string) {
    setSearch(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(val), 350);
  }

  const dealsQuery = useInfiniteQuery({
    queryKey: ['deals', debouncedSearch, retailer?.id, category?.id],
    queryFn: ({ pageParam = 1 }) =>
      dealsApi.list({ search: debouncedSearch || undefined, retailer: retailer?.id, category: category?.id, page: pageParam as number })
        .then((r) => r.data),
    getNextPageParam: (lastPage: any) => lastPage.next ? true : undefined,
    initialPageParam: 1,
  });

  const deals = dealsQuery.data?.pages.flatMap((p: any) => p.results ?? []) ?? [];

  const { data: retailers } = useQuery({
    queryKey: ['retailers'],
    queryFn: () => retailersApi.list().then((r) => r.data.results ?? r.data ?? []),
  });

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list().then((r) => r.data.results ?? r.data ?? []),
  });

  const subscribe = useMutation({
    mutationFn: (deal: any) => {
      if (!deal.product?.id) throw new Error('no_product');
      return subscriptionsApi.create({ target_type: 'product', product_id: deal.product.id });
    },
    onMutate: (deal) => setAlertingId(deal.id),
    onSuccess: () => {
      Alert.alert('✅ Alert created', "We'll notify you when this deal improves.");
      qc.invalidateQueries({ queryKey: ['subscriptions'] });
    },
    onError: (e: any) => {
      const msg = e?.message === 'no_product'
        ? 'Cannot create alert for this deal directly. Use Create Alert tab.'
        : (e?.response?.data?.detail ?? 'Could not create alert.');
      Alert.alert('Error', msg);
    },
    onSettled: () => setAlertingId(null),
  });

  function loadMore() {
    if (dealsQuery.hasNextPage && !dealsQuery.isFetchingNextPage) {
      dealsQuery.fetchNextPage();
    }
  }

  const total = dealsQuery.data?.pages[0]?.count ?? 0;

  return (
    <SafeAreaView style={s.safe} edges={['left', 'right', 'bottom']}>
      <View style={s.searchRow}>
        <TextInput
          style={s.searchInput}
          placeholder="Search deals…"
          placeholderTextColor={colors.textMuted}
          value={search}
          onChangeText={handleSearch}
        />
      </View>

      <View style={s.filterRow}>
        <TouchableOpacity
          style={[s.filterBtn, retailer && s.filterBtnActive]}
          onPress={() => setShowRetailerModal(true)}
        >
          <Text style={[s.filterBtnText, retailer && s.filterBtnTextActive]}>
            {retailer ? retailer.name : 'Retailer ▾'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[s.filterBtn, category && s.filterBtnActive]}
          onPress={() => setShowCategoryModal(true)}
        >
          <Text style={[s.filterBtnText, category && s.filterBtnTextActive]}>
            {category ? category.name : 'Category ▾'}
          </Text>
        </TouchableOpacity>
        {(retailer || category) && (
          <TouchableOpacity onPress={() => { setRetailer(null); setCategory(null); }} style={s.clearBtn}>
            <Text style={s.clearText}>Clear</Text>
          </TouchableOpacity>
        )}
      </View>

      {total > 0 && (
        <Text style={s.countText}>{total.toLocaleString()} deals found</Text>
      )}

      {dealsQuery.isLoading ? (
        <View style={s.center}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : deals.length === 0 ? (
        <View style={s.empty}>
          <Text style={s.emptyIcon}>🏷️</Text>
          <Text style={s.emptyTitle}>No deals found</Text>
          <Text style={s.emptySubtitle}>Try adjusting your filters</Text>
        </View>
      ) : (
        <FlatList
          data={deals}
          keyExtractor={(item: any) => String(item.id)}
          numColumns={2}
          columnWrapperStyle={s.row}
          contentContainerStyle={s.list}
          renderItem={({ item }) => (
            <View style={{ opacity: alertingId === item.id ? 0.6 : 1 }}>
              <DealCard deal={item} onAlert={(d) => subscribe.mutate(d)} />
            </View>
          )}
          onEndReached={loadMore}
          onEndReachedThreshold={0.3}
          ListFooterComponent={
            dealsQuery.isFetchingNextPage
              ? <ActivityIndicator style={{ marginVertical: 16 }} color={colors.primary} />
              : null
          }
        />
      )}

      <FilterModal
        visible={showRetailerModal}
        title="Select Retailer"
        items={retailers ?? []}
        selected={retailer}
        onSelect={setRetailer}
        onClose={() => setShowRetailerModal(false)}
      />
      <FilterModal
        visible={showCategoryModal}
        title="Select Category"
        items={categories ?? []}
        selected={category}
        onSelect={setCategory}
        onClose={() => setShowCategoryModal(false)}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  searchRow: { paddingHorizontal: 12, paddingTop: 10, paddingBottom: 8 },
  searchInput: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, fontSize: 14, color: colors.textPrimary },
  filterRow: { flexDirection: 'row', paddingHorizontal: 12, gap: 8, marginBottom: 8, alignItems: 'center' },
  filterBtn: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6, backgroundColor: colors.surface },
  filterBtnActive: { borderColor: colors.primary, backgroundColor: colors.primaryLight },
  filterBtnText: { fontSize: 13, color: colors.textSecondary, fontWeight: '600' },
  filterBtnTextActive: { color: colors.primary },
  clearBtn: { paddingHorizontal: 8 },
  clearText: { color: colors.textMuted, fontSize: 13, fontWeight: '600' },
  countText: { paddingHorizontal: 12, fontSize: 12, color: colors.textMuted, marginBottom: 4 },
  list: { paddingHorizontal: 12, paddingBottom: 20 },
  row: { gap: 12, justifyContent: 'space-between' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 8 },
  emptyIcon: { fontSize: 48, marginBottom: 8 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: colors.textSecondary },
  emptySubtitle: { fontSize: 14, color: colors.textMuted },
});
