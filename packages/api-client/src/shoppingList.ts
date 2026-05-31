/**
 * packages/api-client/src/shoppingList.ts
 * ----------------------------------------
 * Shared typed API client for the shopping list feature.
 * Used by both the React Native app and the Next.js website.
 *
 * Call configure() once at app startup in each app:
 *
 *   Web (layout.tsx or providers.tsx):
 *     configure({
 *       baseUrl: process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000',
 *       getToken: () => localStorage.getItem('access_token'),
 *     })
 *
 *   Mobile (App.tsx):
 *     configure({
 *       baseUrl: Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000',
 *       getToken: () => SecureStore.getItemAsync('access_token'),
 *     })
 */

// ── Types ──────────────────────────────────────────────────────────────────── //

export interface ProductSearchResult {
  product_id:      number
  product_name:    string
  score:           number
  match_type:      'exact' | 'fuzzy' | 'category'
  master_category: string | null
  retailers:       string[]
  best_price:      number | null
  old_price:       number | null
  discount_pct:    number | null
  image_url:       string | null
  product_url:     string | null
}

export interface Branch {
  id:           number
  name:         string
  retailer:     string
  is_preferred: boolean
  distance_km:  number | null
}

export interface BranchPreference {
  id:            number
  branch:        number
  branch_name:   string
  retailer_name: string
  priority:      number
  home_lat:      number | null
  home_lng:      number | null
}

export interface ShoppingListItem {
  id:            number
  raw_query:     string
  qty:           number
  position:      number
  product:       number | null
  product_name:  string | null
  retailer_name: string | null
  deal:          number | null
  branch:        number | null
  branch_name:   string | null
  is_matched:    boolean
  match_score:   number | null
  best_price:    number | null
  old_price:     number | null
  discount_pct:  number | null
  line_total:    number | null
  saving:        number | null
}

export interface ShoppingList {
  id:            number
  name:          string
  mode:          'single' | 'split' | 'budget'
  budget:        number | null
  status:        'draft' | 'optimised' | 'completed'
  item_count:    number
  matched_count: number
  items:         ShoppingListItem[]
  created_at:    string
  updated_at:    string
}

export interface BranchPlanItem {
  item_id:      number
  product_name: string
  deal_id:      number
  price:        string
  old_price:    string | null
  qty:          number
  line_total:   string
  saving:       string
}

export interface BranchPlanGroup {
  branch_id:     number
  branch_name:   string
  retailer:      string
  items:         BranchPlanItem[]
  branch_total:  string
  branch_saving: string
}

export interface OptimisationResult {
  id:          number
  mode:        string
  grand_total: string
  total_saving: string
  branch_plan: {
    branches:        BranchPlanGroup[]
    grand_total:     string
    total_saving:    string
    unmatched_items: string[]
  }
  computed_at: string
  is_stale:    boolean
}

// ── Configuration ─────────────────────────────────────────────────────────── //

interface Config {
  baseUrl:  string
  getToken: () => Promise<string | null> | string | null
}

let _config: Config = {
  baseUrl:  '',
  getToken: () => null,
}

export function configureShoppingList(config: Config) {
  _config = config
}

// ── Core fetch wrapper ─────────────────────────────────────────────────────── //

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await _config.getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${_config.baseUrl}${path}`, { ...options, headers })

  if (!res.ok) {
    const body = await res.text()
    throw new ShoppingListApiError(res.status, body)
  }

  if (res.status === 204) return undefined as unknown as T
  return res.json() as Promise<T>
}

export class ShoppingListApiError extends Error {
  constructor(
    public status: number,
    public body: string,
  ) {
    super(`API error ${status}: ${body}`)
  }
}

// ── API methods ───────────────────────────────────────────────────────────── //

export const shoppingListApi = {

  searchProducts(q: string, limit = 10): Promise<ProductSearchResult[]> {
    const params = new URLSearchParams({ q, limit: String(limit) })
    return request<ProductSearchResult[]>(`/api/products/search/?${params}`)
  },

  getBranchesNearby(params?: {
    lat?: number
    lng?: number
    retailer_ids?: number[]
  }): Promise<Branch[]> {
    const qs = new URLSearchParams()
    if (params?.lat)          qs.set('lat', String(params.lat))
    if (params?.lng)          qs.set('lng', String(params.lng))
    if (params?.retailer_ids) qs.set('retailer_ids', params.retailer_ids.join(','))
    return request<Branch[]>(`/api/branches/nearby/?${qs}`)
  },

  getBranchPreferences(): Promise<BranchPreference[]> {
    return request<BranchPreference[]>('/api/user/branches/')
  },

  addBranchPreference(data: {
    branch: number
    priority?: number
    home_lat?: number
    home_lng?: number
  }): Promise<BranchPreference> {
    return request<BranchPreference>('/api/user/branches/', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  removeBranchPreference(branchId: number): Promise<void> {
    return request<void>(`/api/user/branches/${branchId}/`, { method: 'DELETE' })
  },

  getLists(): Promise<ShoppingList[]> {
    return request<ShoppingList[]>('/api/shopping-lists/')
  },

  createList(data: {
    name?: string
    mode?: ShoppingList['mode']
    budget?: number
  }): Promise<ShoppingList> {
    return request<ShoppingList>('/api/shopping-lists/', {
      method: 'POST',
      body: JSON.stringify({ name: 'My shopping list', mode: 'split', ...data }),
    })
  },

  getList(id: number): Promise<ShoppingList> {
    return request<ShoppingList>(`/api/shopping-lists/${id}/`)
  },

  updateList(
    id: number,
    data: Partial<Pick<ShoppingList, 'name' | 'mode' | 'budget'>>,
  ): Promise<ShoppingList> {
    return request<ShoppingList>(`/api/shopping-lists/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  deleteList(id: number): Promise<void> {
    return request<void>(`/api/shopping-lists/${id}/`, { method: 'DELETE' })
  },

  addItem(
    listId: number,
    data: { raw_query: string; product_id?: number; qty?: number },
  ): Promise<ShoppingListItem> {
    return request<ShoppingListItem>(`/api/shopping-lists/${listId}/items/`, {
      method: 'POST',
      body: JSON.stringify({ qty: 1, ...data }),
    })
  },

  updateItem(
    listId: number,
    itemId: number,
    data: { qty?: number; product_id?: number },
  ): Promise<ShoppingListItem> {
    return request<ShoppingListItem>(
      `/api/shopping-lists/${listId}/items/${itemId}/`,
      { method: 'PATCH', body: JSON.stringify(data) },
    )
  },

  removeItem(listId: number, itemId: number): Promise<void> {
    return request<void>(
      `/api/shopping-lists/${listId}/items/${itemId}/`,
      { method: 'DELETE' },
    )
  },

  optimiseList(listId: number, mode?: ShoppingList['mode']): Promise<OptimisationResult> {
    return request<OptimisationResult>(
      `/api/shopping-lists/${listId}/optimise/`,
      { method: 'POST', body: JSON.stringify(mode ? { mode } : {}) },
    )
  },

  getOptimisationResult(listId: number): Promise<OptimisationResult> {
    return request<OptimisationResult>(`/api/shopping-lists/${listId}/result/`)
  },
}
