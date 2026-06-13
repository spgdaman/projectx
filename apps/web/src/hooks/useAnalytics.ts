'use client'

import posthog from 'posthog-js'

export function useAnalytics() {
  return {
    trackDealViewed: (deal: {
      id: number | string
      product_name: string
      retailer: string
      category?: string
      current_price: number
      old_price?: number
      discount_pct?: number
    }) => {
      posthog.capture('deal_viewed', deal)
    },

    trackDealClicked: (deal: {
      id: number | string
      product_name: string
      retailer: string
      destination_url?: string
      discount_pct?: number
    }) => {
      posthog.capture('deal_clicked', deal)
    },

    trackSearch: (query: string, results_count: number) => {
      posthog.capture('search_performed', {
        query,
        results_count,
        has_results: results_count > 0,
      })
    },

    trackAlertCreated: (type: 'product' | 'category' | 'retailer') => {
      posthog.capture('alert_created', { subscription_type: type })
    },

    trackShoppingListCreated: () => {
      posthog.capture('shopping_list_created')
    },

    trackListOptimised: (mode: string, items_count: number) => {
      posthog.capture('shopping_list_optimised', { mode, items_count })
    },

    trackCategoryFiltered: (category_name: string) => {
      posthog.capture('category_filtered', { category_name })
    },

    identifyUser: (
      userId: string | number,
      properties?: { is_free_tier?: boolean; created_at?: string }
    ) => {
      posthog.identify(String(userId), properties)
    },

    resetUser: () => {
      posthog.reset()
    },
  }
}
