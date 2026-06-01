/**
 * Shopping list screens for the React Native (Expo) app.
 *
 * Screens exported:
 *   ShoppingListHomeScreen    — user's saved lists
 *   ShoppingListBuilderScreen — add items + branch picker + optimise
 *   ShoppingListResultScreen  — final deal plan grouped by branch
 *
 * Add to AppStack.tsx:
 *   import {
 *     ShoppingListHomeScreen,
 *     ShoppingListBuilderScreen,
 *     ShoppingListResultScreen,
 *   } from '../screens/ShoppingList'
 *
 *   <Stack.Screen name="ShoppingListHome"    component={ShoppingListHomeScreen} />
 *   <Stack.Screen name="ShoppingListBuilder" component={ShoppingListBuilderScreen} />
 *   <Stack.Screen name="ShoppingListResult"  component={ShoppingListResultScreen} />
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  ScrollView,
  ActivityIndicator,
  Alert,
  Share,
  StyleSheet,
  Platform,
  KeyboardAvoidingView,
  Pressable,
  SectionList,
} from 'react-native'
import { useNavigation, useRoute } from '@react-navigation/native'
import * as Location from 'expo-location'

import {
  shoppingListApi,
  ShoppingList,
  ShoppingListItem,
  ProductSearchResult,
  Branch,
  OptimisationResult,
} from '@bargain-hunters/api-client'

import { colors } from '../../theme'

// ── Design tokens ─────────────────────────────────────────────────────────── //

const T = {
  primary:     colors.primary,       // #E54416
  primaryDark: colors.primaryDark,   // #C73D0F
  primaryAccent: colors.primaryAccent, // #FDEBD0
  primaryLight: colors.primaryLight,  // #FFF9F1
  amber:       '#BA7517',
  amberLight:  '#FAEEDA',
  purple:      '#534AB7',
  purpleLight: '#EEEDFE',
  gray:        colors.textSecondary,
  grayLight:   '#F1EFE8',
  border:      colors.border,
  text:        colors.textPrimary,
  textSub:     colors.textSecondary,
  textHint:    colors.textMuted,
  bg:          colors.surface,
  bgSurface:   colors.background,
  danger:      '#E24B4A',
  dangerLight: '#FCEBEB',
  radius:      10,
  radiusSm:    6,
}

// ── Helpers ───────────────────────────────────────────────────────────────── //

function formatKES(amount: string | number | null): string {
  if (amount == null) return '—'
  const n = typeof amount === 'string' ? parseFloat(amount) : amount
  return `KES ${n.toLocaleString('en-KE', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

// ── Retailer badge ─────────────────────────────────────────────────────────── //

const RETAILER_BADGE: Record<string, { bg: string; text: string }> = {
  Naivas:    { bg: T.primaryAccent, text: T.primaryDark },
  Quickmart: { bg: T.amberLight,    text: T.amber },
  Carrefour: { bg: T.purpleLight,   text: T.purple },
}

function RetailerBadge({ name }: { name: string }) {
  const style = RETAILER_BADGE[name] ?? { bg: T.grayLight, text: T.gray }
  return (
    <View style={[s.badge, { backgroundColor: style.bg }]}>
      <Text style={[s.badgeText, { color: style.text }]}>{name}</Text>
    </View>
  )
}

// ════════════════════════════════════════════════════════════════════════════ //
// SCREEN 1 — Shopping list home
// ════════════════════════════════════════════════════════════════════════════ //

export function ShoppingListHomeScreen() {
  const navigation = useNavigation<any>()
  const [lists, setLists]     = useState<ShoppingList[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setLists(await shoppingListApi.getLists())
    } catch {
      Alert.alert('Error', 'Could not load your shopping lists.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const createNew = async () => {
    try {
      const list = await shoppingListApi.createList({ name: 'New list', mode: 'split' })
      navigation.navigate('ShoppingListBuilder', { listId: list.id })
    } catch {
      Alert.alert('Error', 'Could not create a new list.')
    }
  }

  const deleteList = (list: ShoppingList) => {
    Alert.alert('Delete list', `Delete "${list.name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          await shoppingListApi.deleteList(list.id)
          setLists(prev => prev.filter(l => l.id !== list.id))
        },
      },
    ])
  }

  if (loading) {
    return <View style={s.center}><ActivityIndicator size="large" color={T.primary} /></View>
  }

  return (
    <View style={s.screen}>
      <FlatList
        data={lists}
        keyExtractor={l => String(l.id)}
        contentContainerStyle={{ padding: 16, paddingBottom: 100 }}
        ListEmptyComponent={
          <View style={s.emptyState}>
            <Text style={s.emptyTitle}>No shopping lists yet</Text>
            <Text style={s.emptySub}>Create one to start finding the best deals</Text>
          </View>
        }
        renderItem={({ item: list }) => (
          <Pressable
            style={s.listCard}
            onPress={() => navigation.navigate('ShoppingListBuilder', { listId: list.id })}
            onLongPress={() => deleteList(list)}
          >
            <View style={s.listCardRow}>
              <View style={{ flex: 1 }}>
                <Text style={s.listCardName}>{list.name}</Text>
                <Text style={s.listCardSub}>
                  {list.item_count} item{list.item_count !== 1 ? 's' : ''}
                  {list.matched_count < list.item_count
                    ? ` · ${list.item_count - list.matched_count} unmatched`
                    : ''}
                  {' · '}{list.mode === 'single' ? 'One store'
                        : list.mode === 'split'  ? 'Best price'
                        : 'Budget fit'}
                </Text>
              </View>
              <View style={[
                s.statusPill,
                { backgroundColor: list.status === 'optimised' ? T.primaryAccent : T.grayLight },
              ]}>
                <Text style={[
                  s.statusPillText,
                  { color: list.status === 'optimised' ? T.primaryDark : T.gray },
                ]}>
                  {list.status}
                </Text>
              </View>
            </View>
          </Pressable>
        )}
      />
      <TouchableOpacity style={s.fab} onPress={createNew} activeOpacity={0.85}>
        <Text style={s.fabText}>+ New list</Text>
      </TouchableOpacity>
    </View>
  )
}

// ════════════════════════════════════════════════════════════════════════════ //
// SCREEN 2 — List builder
// ════════════════════════════════════════════════════════════════════════════ //

export function ShoppingListBuilderScreen() {
  const navigation            = useNavigation<any>()
  const route                 = useRoute<any>()
  const { listId }            = route.params as { listId: number }

  const [list, setList]       = useState<ShoppingList | null>(null)
  const [query, setQuery]     = useState('')
  const [suggestions, setSugg]  = useState<ProductSearchResult[]>([])
  const [showSugg, setShowSugg] = useState(false)
  const [searching, setSearching] = useState(false)

  const [branches, setBranches]       = useState<Branch[]>([])
  const [showBranches, setShowBranches] = useState(false)
  const [savingBranch, setSavingBranch] = useState<number | null>(null)
  const [locationLoading, setLocLoading] = useState(false)

  const [optimising, setOptimising] = useState(false)
  const [listMode, setListMode]     = useState<ShoppingList['mode']>('split')

  const debouncedQuery = useDebounce(query, 300)
  const inputRef       = useRef<TextInput>(null)

  useEffect(() => {
    shoppingListApi.getList(listId).then(l => { setList(l); setListMode(l.mode) })
  }, [listId])

  useEffect(() => {
    if (debouncedQuery.length < 2) { setSugg([]); setShowSugg(false); return }
    setSearching(true)
    shoppingListApi.searchProducts(debouncedQuery, 8)
      .then(res => { setSugg(res); setShowSugg(res.length > 0) })
      .catch(() => setSugg([]))
      .finally(() => setSearching(false))
  }, [debouncedQuery])

  const loadBranches = async () => {
    setLocLoading(true)
    let lat: number | undefined
    let lng: number | undefined
    try {
      const { status } = await Location.requestForegroundPermissionsAsync()
      if (status === 'granted') {
        const loc = await Location.getCurrentPositionAsync({})
        lat = loc.coords.latitude
        lng = loc.coords.longitude
      }
    } catch { /* GPS optional */ }
    try {
      setBranches(await shoppingListApi.getBranchesNearby({ lat, lng }))
      setShowBranches(true)
    } catch {
      Alert.alert('Error', 'Could not load branches.')
    } finally {
      setLocLoading(false)
    }
  }

  const toggleBranch = async (branch: Branch) => {
    setSavingBranch(branch.id)
    try {
      if (branch.is_preferred) {
        await shoppingListApi.removeBranchPreference(branch.id)
      } else {
        await shoppingListApi.addBranchPreference({ branch: branch.id, priority: 0 })
      }
      setBranches(prev =>
        prev.map(b => b.id === branch.id ? { ...b, is_preferred: !b.is_preferred } : b)
      )
    } catch {
      Alert.alert('Error', 'Could not update branch preference.')
    } finally {
      setSavingBranch(null)
    }
  }

  const selectSuggestion = async (suggestion: ProductSearchResult) => {
    setQuery(''); setShowSugg(false); inputRef.current?.blur()
    try {
      const item = await shoppingListApi.addItem(listId, {
        raw_query: suggestion.product_name, product_id: suggestion.product_id, qty: 1,
      })
      setList(prev => prev
        ? { ...prev, items: [...prev.items, item], item_count: prev.item_count + 1 }
        : prev
      )
    } catch { Alert.alert('Error', 'Could not add item.') }
  }

  const addByTyping = async () => {
    if (!query.trim()) return
    const raw = query.trim(); setQuery(''); setShowSugg(false)
    try {
      const item = await shoppingListApi.addItem(listId, { raw_query: raw })
      setList(prev => prev
        ? { ...prev, items: [...prev.items, item], item_count: prev.item_count + 1 }
        : prev
      )
    } catch { Alert.alert('Error', 'Could not add item.') }
  }

  const removeItem = async (itemId: number) => {
    try {
      await shoppingListApi.removeItem(listId, itemId)
      setList(prev => prev
        ? { ...prev, items: prev.items.filter(i => i.id !== itemId), item_count: prev.item_count - 1 }
        : prev
      )
    } catch { Alert.alert('Error', 'Could not remove item.') }
  }

  const updateQty = async (item: ShoppingListItem, delta: number) => {
    const newQty = Math.max(1, (item.qty || 1) + delta)
    try {
      const updated = await shoppingListApi.updateItem(listId, item.id, { qty: newQty })
      setList(prev => prev
        ? { ...prev, items: prev.items.map(i => i.id === updated.id ? updated : i) }
        : prev
      )
    } catch { /* silent */ }
  }

  const handleOptimise = async () => {
    if (!branches.some(b => b.is_preferred)) {
      Alert.alert('Select branches', 'Please select at least one branch first.')
      setShowBranches(true)
      return
    }
    setOptimising(true)
    try {
      const result = await shoppingListApi.optimiseList(listId, listMode)
      navigation.navigate('ShoppingListResult', { listId, result })
    } catch (e: unknown) {
      const err = e as { body?: string }
      Alert.alert('Error', err.body || 'Optimisation failed.')
    } finally {
      setOptimising(false)
    }
  }

  if (!list) {
    return <View style={s.center}><ActivityIndicator size="large" color={T.primary} /></View>
  }

  const unmatchedCount = list.items.filter(i => !i.is_matched).length

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: T.bg }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        style={{ flex: 1 }}
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={{ paddingBottom: 120 }}
      >
        {/* Mode selector */}
        <View style={s.modeRow}>
          {(['split', 'single', 'budget'] as const).map(m => (
            <TouchableOpacity
              key={m}
              style={[s.modeBtn, listMode === m && s.modeBtnActive]}
              onPress={() => { setListMode(m); shoppingListApi.updateList(listId, { mode: m }) }}
            >
              <Text style={[s.modeBtnText, listMode === m && s.modeBtnTextActive]}>
                {m === 'split' ? 'Best price' : m === 'single' ? 'One store' : 'Budget'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Search input */}
        <View style={s.searchWrap}>
          <View style={s.searchRow}>
            <TextInput
              ref={inputRef}
              style={s.searchInput}
              placeholder="Add item (e.g. fresh milk, diapers size 3)"
              placeholderTextColor={T.textHint}
              value={query}
              onChangeText={setQuery}
              onSubmitEditing={addByTyping}
              returnKeyType="done"
            />
            {searching
              ? <ActivityIndicator size="small" color={T.primary} style={{ marginRight: 10 }} />
              : query.length > 0 && (
                <TouchableOpacity onPress={addByTyping} style={s.addBtn}>
                  <Text style={s.addBtnText}>Add</Text>
                </TouchableOpacity>
              )
            }
          </View>

          {showSugg && (
            <View style={s.suggestions}>
              {suggestions.map(sug => (
                <TouchableOpacity key={sug.product_id} style={s.suggItem} onPress={() => selectSuggestion(sug)}>
                  <View style={{ flex: 1 }}>
                    <Text style={s.suggName}>{sug.product_name}</Text>
                    <View style={s.badgeRow}>
                      {sug.retailers.map(r => <RetailerBadge key={r} name={r} />)}
                      {sug.master_category && <Text style={s.suggCat}>{sug.master_category}</Text>}
                    </View>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    {sug.best_price != null && <Text style={s.suggPrice}>{formatKES(sug.best_price)}</Text>}
                    {sug.discount_pct != null && (
                      <View style={s.discountPill}>
                        <Text style={s.discountPillText}>{sug.discount_pct}% off</Text>
                      </View>
                    )}
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        {/* Items list */}
        <View style={{ paddingHorizontal: 16, marginTop: 8 }}>
          <View style={s.sectionHeader}>
            <Text style={s.sectionTitle}>
              Items ({list.item_count})
              {unmatchedCount > 0 && <Text style={{ color: T.amber }}> · {unmatchedCount} need review</Text>}
            </Text>
          </View>

          {list.items.length === 0 && (
            <Text style={s.emptyItems}>No items yet — type above to search</Text>
          )}

          {list.items.map(item => (
            <View key={item.id} style={[s.itemRow, !item.is_matched && s.itemRowUnmatched]}>
              <View style={{ flex: 1 }}>
                <Text style={s.itemName}>{item.product_name || item.raw_query}</Text>
                {!item.is_matched && <Text style={s.unmatchedLabel}>Tap to confirm product</Text>}
                {item.is_matched && item.best_price != null && (
                  <Text style={s.itemPrice}>{formatKES(item.best_price)}</Text>
                )}
              </View>
              <View style={s.qtyStepper}>
                <TouchableOpacity onPress={() => updateQty(item, -1)} style={s.qtyBtn}>
                  <Text style={s.qtyBtnText}>−</Text>
                </TouchableOpacity>
                <Text style={s.qtyValue}>{item.qty}</Text>
                <TouchableOpacity onPress={() => updateQty(item, +1)} style={s.qtyBtn}>
                  <Text style={s.qtyBtnText}>+</Text>
                </TouchableOpacity>
              </View>
              <TouchableOpacity onPress={() => removeItem(item.id)} style={s.removeBtn} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                <Text style={s.removeBtnText}>✕</Text>
              </TouchableOpacity>
            </View>
          ))}
        </View>

        {/* Branch selector */}
        <View style={{ paddingHorizontal: 16, marginTop: 20 }}>
          <TouchableOpacity
            style={s.sectionHeader}
            onPress={showBranches ? () => setShowBranches(false) : loadBranches}
          >
            <Text style={s.sectionTitle}>Select branches</Text>
            {locationLoading
              ? <ActivityIndicator size="small" color={T.primary} />
              : <Text style={s.chevron}>{showBranches ? '▲' : '▼'}</Text>
            }
          </TouchableOpacity>

          {showBranches && (
            <View style={s.branchList}>
              {(['Naivas', 'Quickmart', 'Carrefour'] as const).map(retailer => {
                const group = branches.filter(b => b.retailer === retailer)
                if (!group.length) return null
                return (
                  <View key={retailer}>
                    <View style={s.branchGroupHeader}>
                      <RetailerBadge name={retailer} />
                      <Text style={s.branchGroupCount}>
                        {group.filter(b => b.is_preferred).length}/{group.length} selected
                      </Text>
                    </View>
                    {group.map(branch => (
                      <TouchableOpacity
                        key={branch.id}
                        style={s.branchItem}
                        onPress={() => toggleBranch(branch)}
                        disabled={savingBranch === branch.id}
                      >
                        <View style={[s.checkbox, branch.is_preferred && s.checkboxChecked]}>
                          {branch.is_preferred && <Text style={s.checkmark}>✓</Text>}
                        </View>
                        <View style={{ flex: 1 }}>
                          <Text style={s.branchName}>{branch.name}</Text>
                          {branch.distance_km != null && (
                            <Text style={s.branchDist}>{branch.distance_km.toFixed(1)} km away</Text>
                          )}
                        </View>
                        {savingBranch === branch.id && <ActivityIndicator size="small" color={T.primary} />}
                      </TouchableOpacity>
                    ))}
                  </View>
                )
              })}
            </View>
          )}
        </View>
      </ScrollView>

      {/* Sticky optimise button */}
      <View style={s.stickyFooter}>
        <TouchableOpacity
          style={[s.optimiseBtn, optimising && { opacity: 0.7 }]}
          onPress={handleOptimise}
          disabled={optimising || list.item_count === 0}
          activeOpacity={0.85}
        >
          {optimising
            ? <ActivityIndicator color="#fff" />
            : <Text style={s.optimiseBtnText}>Find best deals →</Text>
          }
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  )
}

// ════════════════════════════════════════════════════════════════════════════ //
// SCREEN 3 — Optimisation result
// ════════════════════════════════════════════════════════════════════════════ //

export function ShoppingListResultScreen() {
  const navigation = useNavigation<any>()
  const route      = useRoute<any>()
  const { listId, result: initialResult } = route.params as {
    listId: number
    result: OptimisationResult
  }

  const [result, setResult]   = useState<OptimisationResult>(initialResult)
  const [removing, setRemoving] = useState<number | null>(null)

  const overBudget  = result.branch_plan.over_budget_items ?? []
  const totalSaving = parseFloat(result.branch_plan.total_saving)
  const grandTotal  = parseFloat(result.branch_plan.grand_total)
  const savingPct   = grandTotal + totalSaving > 0
    ? Math.round(totalSaving / (grandTotal + totalSaving) * 100)
    : 0

  const removeOverBudgetItem = async (itemId: number) => {
    setRemoving(itemId)
    try {
      await shoppingListApi.removeItem(listId, itemId)
      setResult(prev => ({
        ...prev,
        branch_plan: {
          ...prev.branch_plan,
          over_budget_items: prev.branch_plan.over_budget_items.filter(
            i => i.item_id !== itemId,
          ),
        },
      }))
    } catch {
      Alert.alert('Error', 'Could not remove item.')
    } finally {
      setRemoving(null)
    }
  }

  const handleShare = async () => {
    const lines: string[] = ['🛒 Bargain Hunters — Shopping List\n']
    for (const group of result.branch_plan.branches) {
      lines.push(`📍 ${group.branch_name} (${group.retailer})`)
      for (const item of group.items) {
        lines.push(
          `  • ${item.product_name} × ${item.qty}  KES ${item.price}`
          + (item.old_price ? ` (was KES ${item.old_price})` : '')
        )
      }
      lines.push(`  Subtotal: ${formatKES(group.branch_total)}`)
      lines.push('')
    }
    if (overBudget.length) {
      lines.push('⚠ Items beyond budget (not included):')
      overBudget.forEach(i => lines.push(`  • ${i.product_name}  KES ${i.line_total}`))
      lines.push('')
    }
    lines.push(`Grand total:  ${formatKES(result.branch_plan.grand_total)}`)
    lines.push(`You save:     ${formatKES(result.branch_plan.total_saving)} (${savingPct}% off)`)
    await Share.share({ message: lines.join('\n') })
  }

  const sections = result.branch_plan.branches.map(group => ({
    title:    `${group.branch_name}  ·  ${formatKES(group.branch_total)}`,
    saving:   group.branch_saving,
    retailer: group.retailer,
    data:     group.items,
  }))

  return (
    <View style={{ flex: 1, backgroundColor: T.bgSurface }}>
      <SectionList
        sections={sections}
        keyExtractor={item => String(item.item_id)}
        contentContainerStyle={{ paddingBottom: 120 }}

        renderSectionHeader={({ section }) => (
          <View style={s.resultSectionHeader}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <RetailerBadge name={section.retailer} />
              <Text style={s.resultSectionTitle} numberOfLines={1}>{section.title}</Text>
            </View>
            {parseFloat(section.saving) > 0 && (
              <Text style={s.resultSectionSaving}>Saves {formatKES(section.saving)}</Text>
            )}
          </View>
        )}

        renderItem={({ item }) => (
          <View style={s.resultItem}>
            <View style={{ flex: 1 }}>
              <Text style={s.resultItemName}>{item.product_name}</Text>
              {item.old_price && <Text style={s.resultItemWas}>was {formatKES(item.old_price)}</Text>}
            </View>
            <View style={{ alignItems: 'flex-end' }}>
              <Text style={s.resultItemPrice}>{formatKES(item.price)}</Text>
              {item.qty > 1 && <Text style={s.resultItemQty}>× {item.qty}</Text>}
            </View>
          </View>
        )}

        ListHeaderComponent={
          result.branch_plan.unmatched_items.length > 0 ? (
            <View style={s.unmatchedBanner}>
              <Text style={s.unmatchedBannerTitle}>
                {result.branch_plan.unmatched_items.length} item
                {result.branch_plan.unmatched_items.length !== 1 ? 's' : ''} not found
              </Text>
              <Text style={s.unmatchedBannerSub}>
                {result.branch_plan.unmatched_items.join(' · ')}
              </Text>
            </View>
          ) : null
        }

        ListFooterComponent={
          <>
            {/* Grand total card */}
            <View style={s.resultFooter}>
              {totalSaving > 0 && (
                <View style={s.totalRow}>
                  <Text style={s.totalLabel}>Total savings</Text>
                  <Text style={s.totalSaving}>
                    −{formatKES(result.branch_plan.total_saving)}
                    {savingPct > 0 && ` (${savingPct}% off)`}
                  </Text>
                </View>
              )}
              <View style={[s.totalRow, { borderTopWidth: 0.5, borderTopColor: T.border, marginTop: 6, paddingTop: 10 }]}>
                <Text style={s.grandTotalLabel}>Grand total</Text>
                <Text style={s.grandTotal}>{formatKES(result.branch_plan.grand_total)}</Text>
              </View>
            </View>

            {/* Over-budget section */}
            {overBudget.length > 0 && (
              <View style={s.overBudgetSection}>

                {/* Banner */}
                <View style={s.overBudgetBanner}>
                  <View style={{ flex: 1 }}>
                    <Text style={s.overBudgetBannerTitle}>
                      {overBudget.length} item{overBudget.length !== 1 ? 's' : ''} exceed{overBudget.length === 1 ? 's' : ''} your budget
                    </Text>
                    <Text style={s.overBudgetBannerSub}>
                      Remove them or go back to increase your budget.
                    </Text>
                  </View>
                  <TouchableOpacity
                    style={s.adjustBudgetBtn}
                    onPress={() => navigation.navigate('ShoppingListBuilder', { listId })}
                  >
                    <Text style={s.adjustBudgetBtnText}>Adjust budget</Text>
                  </TouchableOpacity>
                </View>

                {/* Over-budget line items */}
                {overBudget.map(item => (
                  <View key={item.item_id} style={s.overBudgetItem}>
                    <View style={{ flex: 1, marginRight: 8 }}>
                      <Text style={s.overBudgetName} numberOfLines={1}>
                        {item.product_name}
                      </Text>
                      <Text style={s.overBudgetLabel}>Doesn't fit your budget</Text>
                    </View>

                    <View style={{ alignItems: 'flex-end', marginRight: 10 }}>
                      <Text style={s.overBudgetPrice}>{formatKES(item.line_total)}</Text>
                      <Text style={s.overBudgetQty}>× {item.qty} @ {formatKES(item.price)}</Text>
                    </View>

                    <TouchableOpacity
                      style={s.removeOverBudgetBtn}
                      onPress={() => removeOverBudgetItem(item.item_id)}
                      disabled={removing === item.item_id}
                    >
                      {removing === item.item_id
                        ? <ActivityIndicator size="small" color={T.danger} />
                        : <Text style={s.removeOverBudgetBtnText}>Remove</Text>
                      }
                    </TouchableOpacity>
                  </View>
                ))}
              </View>
            )}
          </>
        }
      />

      {/* Action buttons */}
      <View style={s.stickyFooter}>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <TouchableOpacity style={[s.actionBtn, { flex: 1 }]} onPress={handleShare}>
            <Text style={s.actionBtnText}>Share list</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[s.actionBtn, { flex: 1, backgroundColor: T.primaryAccent }]}
            onPress={() => navigation.navigate('ShoppingListBuilder', { listId })}
          >
            <Text style={[s.actionBtnText, { color: T.primaryDark }]}>Edit list</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  )
}

// ── Styles ─────────────────────────────────────────────────────────────────── //

const s = StyleSheet.create({
  screen:          { flex: 1, backgroundColor: T.bg },
  center:          { flex: 1, alignItems: 'center', justifyContent: 'center' },
  listCard:        { backgroundColor: T.bg, borderRadius: T.radius, borderWidth: 0.5, borderColor: T.border, padding: 14, marginBottom: 10 },
  listCardRow:     { flexDirection: 'row', alignItems: 'center', gap: 10 },
  listCardName:    { fontSize: 15, fontWeight: '500', color: T.text, marginBottom: 3 },
  listCardSub:     { fontSize: 13, color: T.textSub },
  statusPill:      { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 20 },
  statusPillText:  { fontSize: 11, fontWeight: '500' },
  emptyState:      { alignItems: 'center', paddingTop: 80 },
  emptyTitle:      { fontSize: 17, fontWeight: '500', color: T.text, marginBottom: 8 },
  emptySub:        { fontSize: 14, color: T.textSub, textAlign: 'center' },
  fab:             { position: 'absolute', bottom: 28, right: 20, left: 20, backgroundColor: T.primary, borderRadius: 50, paddingVertical: 14, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.15, shadowRadius: 8, elevation: 4 },
  fabText:         { color: '#fff', fontSize: 15, fontWeight: '600' },
  modeRow:         { flexDirection: 'row', gap: 8, padding: 16, paddingBottom: 8 },
  modeBtn:         { flex: 1, paddingVertical: 8, borderRadius: T.radiusSm, borderWidth: 0.5, borderColor: T.border, alignItems: 'center', backgroundColor: T.bg },
  modeBtnActive:   { backgroundColor: T.primaryAccent, borderColor: T.primary },
  modeBtnText:     { fontSize: 12, color: T.textSub, fontWeight: '500' },
  modeBtnTextActive: { color: T.primaryDark },
  searchWrap:      { paddingHorizontal: 16, zIndex: 10 },
  searchRow:       { flexDirection: 'row', alignItems: 'center', borderWidth: 0.5, borderColor: T.border, borderRadius: T.radius, backgroundColor: T.bg, paddingHorizontal: 12 },
  searchInput:     { flex: 1, height: 44, fontSize: 14, color: T.text },
  addBtn:          { backgroundColor: T.primary, borderRadius: T.radiusSm, paddingHorizontal: 12, paddingVertical: 6, marginVertical: 6 },
  addBtnText:      { color: '#fff', fontSize: 13, fontWeight: '600' },
  suggestions:     { backgroundColor: T.bg, borderWidth: 0.5, borderColor: T.border, borderRadius: T.radius, marginTop: 4, overflow: 'hidden' },
  suggItem:        { flexDirection: 'row', alignItems: 'center', padding: 12, borderBottomWidth: 0.5, borderBottomColor: T.border },
  suggName:        { fontSize: 13, fontWeight: '500', color: T.text, marginBottom: 3 },
  suggCat:         { fontSize: 11, color: T.textHint, marginLeft: 4 },
  suggPrice:       { fontSize: 13, fontWeight: '600', color: T.primary },
  badgeRow:        { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: 2 },
  sectionHeader:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8 },
  sectionTitle:    { fontSize: 13, fontWeight: '600', color: T.textSub, textTransform: 'uppercase', letterSpacing: 0.5 },
  chevron:         { fontSize: 12, color: T.textSub },
  emptyItems:      { fontSize: 13, color: T.textHint, paddingVertical: 12, textAlign: 'center' },
  itemRow:         { flexDirection: 'row', alignItems: 'center', backgroundColor: T.bg, borderRadius: T.radiusSm, padding: 12, marginBottom: 8, borderWidth: 0.5, borderColor: T.border, gap: 8 },
  itemRowUnmatched: { borderColor: T.amber, backgroundColor: T.amberLight },
  itemName:        { fontSize: 14, fontWeight: '500', color: T.text, marginBottom: 2 },
  unmatchedLabel:  { fontSize: 11, color: T.amber },
  itemPrice:       { fontSize: 12, color: T.primary, fontWeight: '500' },
  qtyStepper:      { flexDirection: 'row', alignItems: 'center', gap: 6 },
  qtyBtn:          { width: 26, height: 26, borderRadius: 13, backgroundColor: T.grayLight, alignItems: 'center', justifyContent: 'center' },
  qtyBtnText:      { fontSize: 16, color: T.text, lineHeight: 20 },
  qtyValue:        { fontSize: 14, fontWeight: '600', color: T.text, minWidth: 18, textAlign: 'center' },
  removeBtn:       { padding: 4 },
  removeBtnText:   { fontSize: 14, color: T.textHint },
  badge:           { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  badgeText:       { fontSize: 10, fontWeight: '600' },
  discountPill:    { backgroundColor: T.primaryAccent, paddingHorizontal: 5, paddingVertical: 2, borderRadius: 4, marginTop: 2 },
  discountPillText: { fontSize: 10, fontWeight: '600', color: T.primaryDark },
  branchList:      { borderWidth: 0.5, borderColor: T.border, borderRadius: T.radius, overflow: 'hidden', marginBottom: 8 },
  branchGroupHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 8, backgroundColor: T.bgSurface },
  branchGroupCount: { fontSize: 11, color: T.textSub },
  branchItem:      { flexDirection: 'row', alignItems: 'center', padding: 12, borderTopWidth: 0.5, borderTopColor: T.border, gap: 10 },
  branchName:      { fontSize: 14, fontWeight: '500', color: T.text },
  branchDist:      { fontSize: 12, color: T.textSub, marginTop: 1 },
  checkbox:        { width: 20, height: 20, borderRadius: 4, borderWidth: 1.5, borderColor: T.border, alignItems: 'center', justifyContent: 'center' },
  checkboxChecked: { backgroundColor: T.primary, borderColor: T.primary },
  checkmark:       { color: '#fff', fontSize: 12, lineHeight: 14 },
  stickyFooter:    { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: T.bg, borderTopWidth: 0.5, borderTopColor: T.border, padding: 16, paddingBottom: Platform.OS === 'ios' ? 32 : 16 },
  optimiseBtn:     { backgroundColor: T.primary, borderRadius: T.radius, paddingVertical: 14, alignItems: 'center' },
  optimiseBtnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  actionBtn:       { backgroundColor: T.bg, borderRadius: T.radius, borderWidth: 0.5, borderColor: T.border, paddingVertical: 12, alignItems: 'center' },
  actionBtnText:   { fontSize: 14, fontWeight: '500', color: T.text },
  resultSectionHeader: { backgroundColor: T.bgSurface, paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: 0.5, borderBottomColor: T.border },
  resultSectionTitle:  { fontSize: 13, fontWeight: '600', color: T.text, flex: 1 },
  resultSectionSaving: { fontSize: 12, color: T.primary, marginTop: 2 },
  resultItem:          { flexDirection: 'row', alignItems: 'center', backgroundColor: T.bg, paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 0.5, borderBottomColor: T.border },
  resultItemName:      { fontSize: 14, fontWeight: '500', color: T.text, marginBottom: 2 },
  resultItemWas:       { fontSize: 11, color: T.textSub, textDecorationLine: 'line-through' },
  resultItemPrice:     { fontSize: 14, fontWeight: '600', color: T.primary },
  resultItemQty:       { fontSize: 11, color: T.textSub, marginTop: 2 },
  unmatchedBanner:     { margin: 16, padding: 12, backgroundColor: T.amberLight, borderRadius: T.radius, borderWidth: 0.5, borderColor: T.amber },
  unmatchedBannerTitle: { fontSize: 13, fontWeight: '600', color: T.amber, marginBottom: 3 },
  unmatchedBannerSub:  { fontSize: 12, color: T.amber },
  resultFooter:        { margin: 16, padding: 16, backgroundColor: T.bg, borderRadius: T.radius, borderWidth: 0.5, borderColor: T.border },
  totalRow:            { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 6 },
  totalLabel:          { fontSize: 13, color: T.textSub },
  totalSaving:         { fontSize: 15, fontWeight: '600', color: T.primary },
  grandTotalLabel:     { fontSize: 15, fontWeight: '600', color: T.text },
  grandTotal:          { fontSize: 20, fontWeight: '700', color: T.text },

  // Over-budget section
  overBudgetSection:      { marginHorizontal: 16, marginBottom: 16, borderRadius: T.radius, borderWidth: 1.5, borderColor: T.danger, overflow: 'hidden' },
  overBudgetBanner:       { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, backgroundColor: T.dangerLight },
  overBudgetBannerTitle:  { fontSize: 13, fontWeight: '600', color: T.danger, marginBottom: 2 },
  overBudgetBannerSub:    { fontSize: 11, color: T.danger, opacity: 0.85 },
  adjustBudgetBtn:        { paddingHorizontal: 10, paddingVertical: 6, borderRadius: T.radiusSm, borderWidth: 1, borderColor: T.danger, backgroundColor: '#fff' },
  adjustBudgetBtnText:    { fontSize: 11, fontWeight: '700', color: T.danger },
  overBudgetItem:         { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 10, borderTopWidth: 0.5, borderTopColor: T.danger, backgroundColor: T.dangerLight },
  overBudgetName:         { fontSize: 13, fontWeight: '500', color: T.danger, textDecorationLine: 'line-through' },
  overBudgetLabel:        { fontSize: 10, color: T.danger, opacity: 0.75, marginTop: 1 },
  overBudgetPrice:        { fontSize: 13, fontWeight: '600', color: T.danger },
  overBudgetQty:          { fontSize: 10, color: T.danger, opacity: 0.75, marginTop: 1 },
  removeOverBudgetBtn:    { paddingHorizontal: 10, paddingVertical: 6, borderRadius: T.radiusSm, borderWidth: 1, borderColor: T.danger, backgroundColor: '#fff', minWidth: 62, alignItems: 'center' },
  removeOverBudgetBtnText: { fontSize: 11, fontWeight: '700', color: T.danger },
})
