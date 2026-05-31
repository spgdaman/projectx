// ─── Paginated response wrapper ───────────────────────────────────────────────
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ─── Auth ────────────────────────────────────────────────────────────────────
export interface TokenPair {
  access: string;
  refresh: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface UserProfile {
  user: User;
  phone_number: string;
  payment_status: boolean;
  is_free_tier: boolean;
  is_active: boolean;
  grace_until: string | null;
  has_access: boolean;
}

// ─── Catalogue ───────────────────────────────────────────────────────────────
export interface Category {
  id: number;
  name: string;
  parent: number | null;
}

export interface CategoryTree extends Category {
  children: CategoryTree[];
}

export interface Retailer {
  id: number;
  name: string;
}

export interface Product {
  id: number;
  name: string;
  price: string;
  sku: string | null;
  url: string | null;
  retailer: Retailer;
  master_category: Category | null;
}

// ─── Deals ───────────────────────────────────────────────────────────────────
export interface Deal {
  id: number;
  product: Product;
  retailer: Retailer;
  current_price: string;
  old_price: string | null;
  link: string | null;
  scraped_at: string;
  discount_pct: number | null;
}

// ─── Subscriptions ───────────────────────────────────────────────────────────
export type TargetType = "product" | "category" | "retailer";

export interface Subscription {
  id: number;
  target_type: TargetType;
  product: Product | null;
  category: Category | null;
  retailer: Retailer | null;
  is_active: boolean;
  is_paid: boolean;
  is_free_tier: boolean;
  is_valid: boolean;
  created_at: string;
  last_updated_at: string;
  expires_at: string | null;
}

export interface CreateSubscriptionInput {
  target_type: TargetType;
  product_id?: number;
  category_id?: number;
  retailer_id?: number;
}

// ─── Payments ────────────────────────────────────────────────────────────────
export type PaymentStatus = "pending" | "success" | "failed" | "expired" | "none";

export interface Payment {
  id: number;
  amount: string;
  currency: string;
  provider: string;
  status: PaymentStatus;
  reference: string;
  created_at: string;
  completed_at: string | null;
  expires_at: string | null;
}

export interface PaymentStatusResponse {
  status: PaymentStatus;
  reference?: string;
}
