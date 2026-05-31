/**
 * Shared React Query hooks — consume in both web (Next.js) and mobile (Expo).
 * Each hook expects an `apiClient` axios instance to be passed in, so this
 * package stays framework-agnostic and doesn't own token storage.
 */
import { useQuery, useMutation, useQueryClient, UseQueryOptions } from "@tanstack/react-query";
import type { AxiosInstance } from "axios";
import type {
  Deal,
  Paginated,
  Category,
  CategoryTree,
  Retailer,
  Product,
  Subscription,
  CreateSubscriptionInput,
  PaymentStatusResponse,
  UserProfile,
} from "./types";

// ─── Deals ───────────────────────────────────────────────────────────────────
export function useDeals(
  client: AxiosInstance,
  params?: { search?: string; retailer?: number; category?: number; page?: number },
  options?: Omit<UseQueryOptions<Paginated<Deal>>, "queryKey" | "queryFn">
) {
  return useQuery<Paginated<Deal>>({
    queryKey: ["deals", params],
    queryFn: () => client.get("/deals/", { params }).then((r) => r.data),
    ...options,
  });
}

export function useDeal(client: AxiosInstance, id: number) {
  return useQuery<Deal>({
    queryKey: ["deal", id],
    queryFn: () => client.get(`/deals/${id}/`).then((r) => r.data),
    enabled: !!id,
  });
}

// ─── Categories ──────────────────────────────────────────────────────────────
export function useCategories(client: AxiosInstance) {
  return useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => client.get("/categories/").then((r) => r.data.results ?? r.data),
  });
}

export function useCategoryTree(client: AxiosInstance) {
  return useQuery<CategoryTree[]>({
    queryKey: ["categories", "tree"],
    queryFn: () => client.get("/categories/tree/").then((r) => r.data),
  });
}

// ─── Retailers ───────────────────────────────────────────────────────────────
export function useRetailers(client: AxiosInstance) {
  return useQuery<Retailer[]>({
    queryKey: ["retailers"],
    queryFn: () => client.get("/retailers/").then((r) => r.data.results ?? r.data),
  });
}

// ─── Products ────────────────────────────────────────────────────────────────
export function useProducts(
  client: AxiosInstance,
  params?: { search?: string; retailer?: number; category?: number }
) {
  return useQuery<Paginated<Product>>({
    queryKey: ["products", params],
    queryFn: () => client.get("/products/", { params }).then((r) => r.data),
  });
}

// ─── Subscriptions ───────────────────────────────────────────────────────────
export function useSubscriptions(client: AxiosInstance) {
  return useQuery<Subscription[]>({
    queryKey: ["subscriptions"],
    queryFn: () =>
      client.get("/subscriptions/").then((r) => r.data.results ?? r.data),
  });
}

export function useCreateSubscription(client: AxiosInstance) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateSubscriptionInput) =>
      client.post<Subscription>("/subscriptions/", input).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  });
}

export function useToggleSubscription(client: AxiosInstance) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      active
        ? client.post(`/subscriptions/${id}/deactivate/`)
        : client.post(`/subscriptions/${id}/activate/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  });
}

export function useDeleteSubscription(client: AxiosInstance) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.delete(`/subscriptions/${id}/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  });
}

// ─── Payments ────────────────────────────────────────────────────────────────
export function useInitiatePayment(client: AxiosInstance) {
  return useMutation({
    mutationFn: (phone: string) =>
      client.post("/payments/initiate/", { phone }).then((r) => r.data),
  });
}

export function usePaymentStatus(client: AxiosInstance, enabled = true) {
  return useQuery<PaymentStatusResponse>({
    queryKey: ["paymentStatus"],
    queryFn: () => client.get("/payments/status/").then((r) => r.data),
    refetchInterval: enabled ? 3000 : false,
    enabled,
  });
}

// ─── User profile ─────────────────────────────────────────────────────────────
export function useMe(client: AxiosInstance) {
  return useQuery<UserProfile>({
    queryKey: ["me"],
    queryFn: () => client.get("/auth/me/").then((r) => r.data),
  });
}
