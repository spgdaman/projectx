'use client'

import { useState, useEffect, useRef } from 'react'
import {
  shoppingListApi,
  ShoppingList,
  ShoppingListItem,
  ProductSearchResult,
  Branch,
  OptimisationResult,
} from '@bargain-hunters/api-client'

// ── Helpers ───────────────────────────────────────────────────────────────── //

function formatKES(amount: string | number | null | undefined): string {
  if (amount == null) return '—'
  const n = typeof amount === 'string' ? parseFloat(amount) : amount
  return `KES ${n.toLocaleString('en-KE', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function useDebounce<T>(value: T, ms: number): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

// ── Retailer badge ─────────────────────────────────────────────────────────── //

const RETAILER_CLASS: Record<string, string> = {
  Naivas:    'bg-brand-100 text-brand-700',
  Quickmart: 'bg-amber-50  text-amber-800',
  Carrefour: 'bg-violet-50 text-violet-800',
}

function RetailerBadge({ name }: { name: string }) {
  const cls = RETAILER_CLASS[name] ?? 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${cls}`}>
      {name}
    </span>
  )
}

function DiscountPill({ pct }: { pct: number }) {
  return (
    <span className="inline-block px-1.5 py-0.5 rounded bg-brand-100 text-brand-700 text-[10px] font-semibold">
      {pct}% off
    </span>
  )
}

// ════════════════════════════════════════════════════════════════════════════ //
// ShoppingListPage — root page component
// ════════════════════════════════════════════════════════════════════════════ //

export function ShoppingListPage() {
  const [lists, setLists]              = useState<ShoppingList[]>([])
  const [activeListId, setActive]      = useState<number | null>(null)
  const [result, setResult]            = useState<OptimisationResult | null>(null)
  const [creating, setCreating]        = useState(false)
  const [loadingLists, setLoading]     = useState(true)
  const [showNewForm, setShowNewForm]  = useState(false)
  const [newListName, setNewListName]  = useState('')
  const nameInputRef                   = useRef<HTMLInputElement>(null)
  const view = result ? 'result' : activeListId ? 'builder' : 'home'

  useEffect(() => {
    shoppingListApi.getLists()
      .then(setLists)
      .finally(() => setLoading(false))
  }, [])

  const openNewForm = () => {
    setShowNewForm(true)
    setNewListName('')
    setTimeout(() => nameInputRef.current?.focus(), 50)
  }

  const createList = async (e: React.FormEvent) => {
    e.preventDefault()
    const name = newListName.trim() || 'My shopping list'
    setCreating(true)
    try {
      const list = await shoppingListApi.createList({ name, mode: 'split' })
      setLists(prev => [list, ...prev])
      setActive(list.id)
      setShowNewForm(false)
      setNewListName('')
      setResult(null)
    } finally {
      setCreating(false)
    }
  }

  const deleteList = async (id: number) => {
    if (!confirm('Delete this list?')) return
    await shoppingListApi.deleteList(id)
    setLists(prev => prev.filter(l => l.id !== id))
    if (activeListId === id) setActive(null)
  }

  return (
    <div className="min-h-screen bg-brand-50">
      <div className="max-w-6xl mx-auto px-4 py-8">

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Shopping lists</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Find the best deals across retailers
            </p>
          </div>
          <button
            onClick={openNewForm}
            disabled={creating}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-60 transition-colors"
          >
            + New list
          </button>
        </div>

        <div className="flex gap-6">
          {/* Left: list sidebar */}
          <div className="w-64 flex-shrink-0">

            {/* Inline create form */}
            {showNewForm && (
              <form
                onSubmit={createList}
                className="mb-3 p-3 bg-white border border-brand-300 rounded-lg shadow-sm"
              >
                <p className="text-xs font-semibold text-gray-500 mb-2">Name your list</p>
                <input
                  ref={nameInputRef}
                  value={newListName}
                  onChange={e => setNewListName(e.target.value)}
                  placeholder="e.g. Weekly groceries"
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md outline-none focus:border-brand-600 mb-2"
                />
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={creating}
                    className="flex-1 py-1.5 bg-brand-600 text-white text-xs font-semibold rounded-md hover:bg-brand-700 disabled:opacity-60"
                  >
                    {creating ? '...' : 'Create'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowNewForm(false)}
                    className="flex-1 py-1.5 bg-gray-100 text-gray-600 text-xs font-semibold rounded-md hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {loadingLists ? (
              <div className="text-sm text-gray-400 py-4 text-center">Loading...</div>
            ) : lists.length === 0 && !showNewForm ? (
              <div className="text-sm text-gray-400 py-4 text-center">
                No lists yet — create one above
              </div>
            ) : (
              <div className="space-y-2">
                {lists.map(list => (
                  <div
                    key={list.id}
                    className={`group relative p-3 rounded-lg border cursor-pointer transition-colors ${
                      activeListId === list.id
                        ? 'border-brand-600 bg-brand-50'
                        : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                    onClick={() => { setActive(list.id); setResult(null) }}
                  >
                    <p className="text-sm font-medium text-gray-900 truncate pr-6">
                      {list.name}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {list.item_count} items ·{' '}
                      <span className={list.status === 'optimised' ? 'text-brand-600' : ''}>
                        {list.status}
                      </span>
                    </p>
                    <button
                      onClick={e => { e.stopPropagation(); deleteList(list.id) }}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 text-xs transition-opacity"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: main panel */}
          <div className="flex-1 min-w-0">
            {view === 'home' && (
              <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
                <p className="text-gray-400 text-sm mb-4">
                  Select a list or create a new one
                </p>
                <button
                  onClick={openNewForm}
                  className="text-brand-600 text-sm font-medium hover:underline"
                >
                  + Create your first list
                </button>
              </div>
            )}
            {view === 'builder' && activeListId && (
              <ShoppingListBuilder
                listId={activeListId}
                onOptimised={r => setResult(r)}
                onRename={newName =>
                  setLists(prev => prev.map(l =>
                    l.id === activeListId ? { ...l, name: newName } : l
                  ))
                }
              />
            )}
            {view === 'result' && result && activeListId && (
              <ShoppingListResult
                result={result}
                onBack={() => setResult(null)}
                onEdit={() => setResult(null)}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════════════ //
// ShoppingListBuilder
// ════════════════════════════════════════════════════════════════════════════ //

function ShoppingListBuilder({
  listId,
  onOptimised,
  onRename,
}: {
  listId: number
  onOptimised: (result: OptimisationResult) => void
  onRename: (name: string) => void
}) {
  const [list, setList]               = useState<ShoppingList | null>(null)
  const [query, setQuery]             = useState('')
  const [suggestions, setSugg]        = useState<ProductSearchResult[]>([])
  const [showSugg, setShowSugg]       = useState(false)
  const [searching, setSearching]     = useState(false)
  const [branches, setBranches]       = useState<Branch[]>([])
  const [branchesLoaded, setBranchesLoaded] = useState(false)
  const [savingBranch, setSavingBranch]     = useState<number | null>(null)
  const [listMode, setListMode]       = useState<ShoppingList['mode']>('split')
  const [budget, setBudget]           = useState('')
  const [optimising, setOptimising]   = useState(false)
  const [error, setError]             = useState<string | null>(null)
  const inputRef   = useRef<HTMLInputElement>(null)
  const debouncedQ = useDebounce(query, 300)

  useEffect(() => {
    shoppingListApi.getList(listId).then(l => {
      setList(l)
      setListMode(l.mode)
      if (l.budget) setBudget(String(l.budget))
    })
  }, [listId])

  useEffect(() => {
    if (debouncedQ.length < 2) { setSugg([]); setShowSugg(false); return }
    setSearching(true)
    shoppingListApi.searchProducts(debouncedQ, 8)
      .then(r => { setSugg(r); setShowSugg(r.length > 0) })
      .catch(() => setSugg([]))
      .finally(() => setSearching(false))
  }, [debouncedQ])

  useEffect(() => {
    shoppingListApi.getBranchesNearby()
      .then(data => { setBranches(data); setBranchesLoaded(true) })
  }, [])

  const switchMode = async (m: ShoppingList['mode']) => {
    setListMode(m)
    if (m !== 'budget') {
      await shoppingListApi.updateList(listId, { mode: m })
    }
    // budget mode: save mode + budget together once budget is confirmed
  }

  const saveBudget = async () => {
    const amt = parseFloat(budget)
    if (listMode === 'budget' && amt > 0) {
      await shoppingListApi.updateList(listId, { mode: 'budget', budget: amt })
    }
  }

  const selectSuggestion = async (sug: ProductSearchResult) => {
    setQuery(''); setShowSugg(false); inputRef.current?.blur()
    const item = await shoppingListApi.addItem(listId, {
      raw_query: sug.product_name, product_id: sug.product_id,
    })
    setList(prev => prev
      ? { ...prev, items: [...prev.items, item], item_count: prev.item_count + 1 }
      : prev
    )
  }

  const addByTyping = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    const raw = query.trim(); setQuery(''); setShowSugg(false)
    const item = await shoppingListApi.addItem(listId, { raw_query: raw })
    setList(prev => prev
      ? { ...prev, items: [...prev.items, item], item_count: prev.item_count + 1 }
      : prev
    )
  }

  const removeItem = async (itemId: number) => {
    await shoppingListApi.removeItem(listId, itemId)
    setList(prev => prev
      ? { ...prev, items: prev.items.filter(i => i.id !== itemId), item_count: prev.item_count - 1 }
      : prev
    )
  }

  const updateQty = async (item: ShoppingListItem, delta: number) => {
    const qty = Math.max(1, (item.qty || 1) + delta)
    const updated = await shoppingListApi.updateItem(listId, item.id, { qty })
    setList(prev => prev
      ? { ...prev, items: prev.items.map(i => i.id === updated.id ? updated : i) }
      : prev
    )
  }

  const toggleBranch = async (branch: Branch) => {
    setSavingBranch(branch.id)
    try {
      if (branch.is_preferred) {
        await shoppingListApi.removeBranchPreference(branch.id)
      } else {
        await shoppingListApi.addBranchPreference({ branch: branch.id, priority: 0 })
      }
      setBranches(prev => prev.map(b =>
        b.id === branch.id ? { ...b, is_preferred: !b.is_preferred } : b
      ))
    } finally {
      setSavingBranch(null)
    }
  }

  const handleOptimise = async () => {
    setError(null)
    if (listMode === 'budget' && (!budget || parseFloat(budget) <= 0)) {
      setError('Enter a budget amount (KES) above before optimising.')
      return
    }
    setOptimising(true)
    try {
      const result = await shoppingListApi.optimiseList(listId, listMode)
      onOptimised(result)
    } catch (e: unknown) {
      const err = e as { body?: string }
      let msg = 'Optimisation failed — please try again.'
      try {
        const parsed = JSON.parse(err.body ?? '')
        msg = parsed.detail ?? msg
      } catch { /* keep default */ }
      setError(msg)
    } finally {
      setOptimising(false)
    }
  }

  if (!list) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-400 text-sm">
        Loading...
      </div>
    )
  }

  const unmatchedCount = list.items.filter(i => !i.is_matched).length

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">

      {/* List name + mode */}
      <div className="px-5 py-4 border-b border-gray-100 space-y-3">
        <div className="flex items-center gap-3">
          <input
            defaultValue={list.name}
            onBlur={e => {
              const name = e.target.value.trim() || list.name
              shoppingListApi.updateList(listId, { name })
              onRename(name)
            }}
            className="text-base font-semibold text-gray-900 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-brand-600 outline-none flex-1 min-w-0 pb-0.5 transition-colors"
            title="Click to rename"
          />
        </div>

        {/* Mode buttons */}
        <div className="flex gap-1.5">
          {(['split', 'single', 'budget'] as const).map(m => (
            <button
              key={m}
              onClick={() => switchMode(m)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                listMode === m
                  ? 'bg-brand-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {m === 'split' ? 'Best price' : m === 'single' ? 'One store' : 'Budget'}
            </button>
          ))}
        </div>

        {/* Budget input — only visible in budget mode */}
        {listMode === 'budget' && (
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500 font-medium whitespace-nowrap">
              Budget (KES)
            </label>
            <input
              type="number"
              min="1"
              value={budget}
              onChange={e => setBudget(e.target.value)}
              onBlur={saveBudget}
              placeholder="e.g. 5000"
              className="flex-1 px-2.5 py-1.5 text-sm border border-gray-200 rounded-md outline-none focus:border-brand-600 transition-colors"
            />
            {budget && parseFloat(budget) > 0 && (
              <span className="text-xs text-brand-600 font-medium whitespace-nowrap">
                {formatKES(parseFloat(budget))}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 divide-x divide-gray-100">

        {/* Left: items */}
        <div className="p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Items ({list.item_count})
            {unmatchedCount > 0 && (
              <span className="text-amber-500 ml-1">· {unmatchedCount} need review</span>
            )}
          </p>

          {/* Search */}
          <form onSubmit={addByTyping} className="relative mb-3">
            <div className="flex items-center border border-gray-200 rounded-lg px-3 gap-2 focus-within:border-brand-600 transition-colors">
              <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search products..."
                className="flex-1 py-2.5 text-sm outline-none bg-transparent text-gray-900 placeholder-gray-400"
              />
              {searching && (
                <div className="w-4 h-4 border-2 border-brand-600 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              )}
              {query && !searching && (
                <button type="submit" className="text-xs font-medium text-brand-600 hover:text-brand-700 flex-shrink-0">
                  Add
                </button>
              )}
            </div>

            {showSugg && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 overflow-hidden max-h-72 overflow-y-auto">
                {suggestions.map(sug => (
                  <button
                    key={sug.product_id}
                    type="button"
                    className="w-full flex items-start gap-3 px-4 py-3 hover:bg-gray-50 text-left border-b border-gray-100 last:border-0"
                    onClick={() => selectSuggestion(sug)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{sug.product_name}</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {sug.retailers.map(r => <RetailerBadge key={r} name={r} />)}
                        {sug.master_category && (
                          <span className="text-[10px] text-gray-400">{sug.master_category}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      {sug.best_price != null && (
                        <p className="text-sm font-semibold text-brand-600">{formatKES(sug.best_price)}</p>
                      )}
                      {sug.discount_pct != null && <DiscountPill pct={sug.discount_pct} />}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </form>

          {/* Item rows */}
          <div className="space-y-2">
            {list.items.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-6">No items — search above to add</p>
            )}
            {list.items.map(item => (
              <div
                key={item.id}
                className={`flex items-center gap-3 p-3 rounded-lg border text-sm ${
                  item.is_matched ? 'border-gray-200 bg-white' : 'border-amber-200 bg-amber-50'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">
                    {item.product_name || item.raw_query}
                  </p>
                  {!item.is_matched && (
                    <p className="text-xs text-amber-600">Not confirmed — try searching and selecting from the dropdown</p>
                  )}
                  {item.is_matched && item.best_price != null && (
                    <p className="text-xs text-brand-600 font-medium">
                      {formatKES(item.best_price)}
                      {item.old_price && (
                        <span className="text-gray-400 line-through ml-1">{formatKES(item.old_price)}</span>
                      )}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  <button onClick={() => updateQty(item, -1)} className="w-6 h-6 rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 flex items-center justify-center text-sm leading-none">−</button>
                  <span className="w-5 text-center text-sm font-medium">{item.qty}</span>
                  <button onClick={() => updateQty(item, +1)} className="w-6 h-6 rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 flex items-center justify-center text-sm leading-none">+</button>
                </div>
                <button onClick={() => removeItem(item.id)} className="text-gray-300 hover:text-red-400 text-sm transition-colors">✕</button>
              </div>
            ))}
          </div>
        </div>

        {/* Right: branches */}
        <div className="p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
            Select branches
          </p>
          <p className="text-xs text-gray-400 mb-3">
            Optional — leave all unchecked to search all retailers
          </p>
          {!branchesLoaded ? (
            <p className="text-sm text-gray-400 text-center py-4">Loading branches...</p>
          ) : branches.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">No branches found</p>
          ) : (
            <div className="space-y-4">
              {(['Naivas', 'Quickmart', 'Carrefour'] as const).map(retailer => {
                const group = branches.filter(b => b.retailer === retailer)
                if (!group.length) return null
                return (
                  <div key={retailer}>
                    <div className="flex items-center gap-2 mb-2">
                      <RetailerBadge name={retailer} />
                      <span className="text-xs text-gray-400">
                        {group.filter(b => b.is_preferred).length} selected
                      </span>
                    </div>
                    <div className="space-y-1">
                      {group.map(branch => (
                        <button
                          key={branch.id}
                          onClick={() => toggleBranch(branch)}
                          disabled={savingBranch === branch.id}
                          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-colors ${
                            branch.is_preferred
                              ? 'border-brand-600 bg-brand-50'
                              : 'border-gray-200 bg-white hover:border-gray-300'
                          }`}
                        >
                          <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                            branch.is_preferred ? 'bg-brand-600 border-brand-600' : 'border-gray-300'
                          }`}>
                            {branch.is_preferred && (
                              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{branch.name}</p>
                            {branch.distance_km != null && (
                              <p className="text-xs text-gray-400">{branch.distance_km.toFixed(1)} km away</p>
                            )}
                          </div>
                          {savingBranch === branch.id && (
                            <div className="w-3 h-3 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-gray-100 bg-gray-50">
        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
        <button
          onClick={handleOptimise}
          disabled={optimising || list.item_count === 0}
          className="w-full py-3 bg-brand-600 text-white text-sm font-semibold rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {optimising ? 'Finding best deals...' : 'Find best deals →'}
        </button>
      </div>
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════════════ //
// ShoppingListResult
// ════════════════════════════════════════════════════════════════════════════ //

function ShoppingListResult({
  result,
  onBack: _onBack,
  onEdit,
}: {
  result: OptimisationResult
  onBack: () => void
  onEdit: () => void
}) {
  const plan        = result.branch_plan
  const totalSaving = parseFloat(plan.total_saving)
  const grandTotal  = parseFloat(plan.grand_total)
  const savingPct   = grandTotal + totalSaving > 0
    ? Math.round(totalSaving / (grandTotal + totalSaving) * 100)
    : 0

  const handleShare = () => {
    const lines: string[] = ['🛒 Bargain Hunters Shopping List\n']
    for (const group of plan.branches) {
      lines.push(`📍 ${group.branch_name} (${group.retailer})`)
      lines.push('─'.repeat(40))
      for (const item of group.items) {
        const disc = item.old_price
          ? ` [${Math.round((parseFloat(item.old_price) - parseFloat(item.price)) / parseFloat(item.old_price) * 100)}% off]`
          : ''
        lines.push(`  ${item.product_name}${disc}`)
        lines.push(`    × ${item.qty}  KES ${item.price}  = KES ${item.line_total}`)
      }
      lines.push('─'.repeat(40))
      lines.push(`  Subtotal: ${formatKES(group.branch_total)}`)
      if (parseFloat(group.branch_saving) > 0)
        lines.push(`  Saved:    ${formatKES(group.branch_saving)}`)
      lines.push('')
    }
    if (plan.unmatched_items.length)
      lines.push(`Not found: ${plan.unmatched_items.join(', ')}\n`)
    lines.push('─'.repeat(40))
    lines.push(`Grand total:    ${formatKES(plan.grand_total)}`)
    lines.push(`Total savings:  ${formatKES(plan.total_saving)} (${savingPct}% off)`)
    navigator.clipboard.writeText(lines.join('\n'))
      .then(() => alert('Copied to clipboard!'))
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">

      {/* Receipt header */}
      <div className="px-5 py-4 bg-brand-50 border-b border-brand-100 flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold text-brand-700 uppercase tracking-widest mb-1">
            Best deal plan
          </p>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900">{formatKES(plan.grand_total)}</span>
            {totalSaving > 0 && (
              <span className="text-sm font-semibold text-brand-600">
                save {formatKES(plan.total_saving)}
                <span className="ml-1 px-1.5 py-0.5 bg-brand-100 text-brand-700 rounded text-[11px]">
                  {savingPct}% off
                </span>
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleShare}
            className="px-3 py-1.5 text-xs font-medium bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Copy
          </button>
          <button
            onClick={onEdit}
            className="px-3 py-1.5 text-xs font-medium bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Edit list
          </button>
        </div>
      </div>

      {/* Unmatched warning */}
      {plan.unmatched_items.length > 0 && (
        <div className="px-5 py-3 bg-amber-50 border-b border-amber-100 flex items-start gap-2">
          <span className="text-amber-500 text-sm mt-px">⚠</span>
          <div>
            <p className="text-xs font-semibold text-amber-700">
              {plan.unmatched_items.length} item{plan.unmatched_items.length !== 1 ? 's' : ''} couldn't be matched
            </p>
            <p className="text-xs text-amber-600 mt-0.5">{plan.unmatched_items.join(' · ')}</p>
          </div>
        </div>
      )}

      {/* Branch sections */}
      {plan.branches.map((group, gi) => {
        const branchSaving = parseFloat(group.branch_saving)
        const showBranchName = group.branch_name !== group.retailer

        return (
          <div key={group.branch_id ?? `g${gi}`} className="border-b border-gray-100 last:border-0">

            {/* Branch header */}
            <div className="px-5 py-3 bg-gray-50 flex items-center justify-between border-b border-gray-200">
              <div className="flex items-center gap-2">
                <RetailerBadge name={group.retailer} />
                {showBranchName && (
                  <span className="text-sm font-semibold text-gray-900">{group.branch_name}</span>
                )}
              </div>
              <div className="text-right">
                <span className="text-sm font-bold text-gray-900">{formatKES(group.branch_total)}</span>
                {branchSaving > 0 && (
                  <span className="text-xs font-medium text-brand-600 ml-2">
                    −{formatKES(group.branch_saving)}
                  </span>
                )}
              </div>
            </div>

            {/* Column labels */}
            <div className="px-5 py-1.5 grid grid-cols-[1fr_3rem_6rem_6rem] gap-x-3 border-b border-gray-100 bg-gray-50">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Item</span>
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide text-right">Qty</span>
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide text-right">Unit price</span>
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide text-right">Total</span>
            </div>

            {/* Line items */}
            {group.items.map(item => {
              const unitPrice   = parseFloat(item.price)
              const oldPrice    = item.old_price ? parseFloat(item.old_price) : null
              const lineSaving  = parseFloat(item.saving)
              const discountPct = oldPrice
                ? Math.round((oldPrice - unitPrice) / oldPrice * 100)
                : 0

              return (
                <div
                  key={item.item_id}
                  className="px-5 py-3 grid grid-cols-[1fr_3rem_6rem_6rem] gap-x-3 items-start border-b border-gray-50 last:border-0"
                >
                  {/* Product + discount info */}
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 leading-snug">{item.product_name}</p>
                    {oldPrice && (
                      <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                        <span className="text-[11px] text-gray-400 line-through">
                          {formatKES(oldPrice)}
                        </span>
                        {discountPct > 0 && (
                          <span className="px-1 py-px rounded text-[10px] font-bold bg-brand-100 text-brand-700">
                            {discountPct}% off
                          </span>
                        )}
                        {lineSaving > 0 && (
                          <span className="text-[11px] font-semibold text-brand-600">
                            save {formatKES(item.saving)}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Qty */}
                  <span className="text-sm text-gray-600 text-right tabular-nums pt-px">
                    {item.qty}
                  </span>

                  {/* Unit price */}
                  <span className="text-sm text-gray-700 text-right tabular-nums pt-px">
                    {formatKES(item.price)}
                  </span>

                  {/* Line total */}
                  <span className="text-sm font-semibold text-gray-900 text-right tabular-nums pt-px">
                    {formatKES(item.line_total)}
                  </span>
                </div>
              )
            })}

            {/* Branch subtotal row */}
            <div className="px-5 py-2.5 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
              <span className="text-xs text-gray-500">
                {group.items.length} item{group.items.length !== 1 ? 's' : ''}
                {branchSaving > 0 && (
                  <span className="text-brand-600 ml-1.5 font-medium">
                    · saved {formatKES(group.branch_saving)}
                  </span>
                )}
              </span>
              <span className="text-sm font-bold text-gray-900">
                Subtotal: {formatKES(group.branch_total)}
              </span>
            </div>
          </div>
        )
      })}

      {/* Grand total footer */}
      <div className="px-5 py-4 bg-gray-50 border-t border-gray-200 space-y-2">
        {totalSaving > 0 && (
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-500">Total savings</span>
            <span className="font-semibold text-brand-600">−{formatKES(plan.total_saving)}</span>
          </div>
        )}
        <div className="flex justify-between items-center pt-2 border-t border-gray-200">
          <span className="text-base font-bold text-gray-900">Grand total</span>
          <span className="text-2xl font-bold text-gray-900">{formatKES(plan.grand_total)}</span>
        </div>
      </div>
    </div>
  )
}
