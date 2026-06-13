import { usePostHog } from 'posthog-react-native';

export function useAnalytics() {
  const posthog = usePostHog();

  return {
    trackDealViewed: (deal: {
      id: number | string;
      product_name: string;
      retailer: string;
      category?: string;
      current_price: number;
      old_price?: number;
      discount_pct?: number;
    }) => {
      posthog?.capture('deal_viewed', deal);
    },

    trackDealClicked: (deal: {
      id: number | string;
      product_name: string;
      retailer: string;
      discount_pct?: number;
    }) => {
      posthog?.capture('deal_clicked', deal);
    },

    trackSearch: (query: string, results_count: number) => {
      posthog?.capture('search_performed', {
        query,
        results_count,
        has_results: results_count > 0,
        platform: 'mobile',
      });
    },

    trackAlertCreated: (type: 'product' | 'category' | 'retailer') => {
      posthog?.capture('alert_created', {
        subscription_type: type,
        platform: 'mobile',
      });
    },

    trackShoppingListCreated: () => {
      posthog?.capture('shopping_list_created', { platform: 'mobile' });
    },

    trackScreenView: (screen_name: string) => {
      posthog?.capture('$screen', { $screen_name: screen_name });
    },

    identifyUser: (
      userId: string | number,
      properties?: { is_free_tier?: boolean; created_at?: string }
    ) => {
      posthog?.identify(String(userId), properties);
    },

    resetUser: () => {
      posthog?.reset();
    },
  };
}
