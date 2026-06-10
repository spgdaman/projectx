import axios from "axios";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: false,
  timeout: 10000,
});

// Attach JWT stored in localStorage (client-only)
if (typeof window !== "undefined") {
  apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  apiClient.interceptors.response.use(
    (res) => res,
    async (error) => {
      const original = error.config;
      if (error.response?.status === 401 && !original._retry) {
        original._retry = true;
        const refresh = localStorage.getItem("refresh_token");
        if (refresh) {
          try {
            const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, { refresh });
            localStorage.setItem("access_token", data.access);
            original.headers.Authorization = `Bearer ${data.access}`;
            return apiClient(original);
          } catch {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            window.location.href = "/login";
          }
        }
      }
      return Promise.reject(error);
    }
  );
}

export const authApi = {
  login: (phone: string, password: string) =>
    apiClient.post<{ access: string; refresh: string }>("/auth/login/", { phone, password }),
  register: (phone: string, password: string, email: string, dateOfBirth: string, firstName?: string, lastName?: string) =>
    apiClient.post<{ access: string; refresh: string }>("/auth/register/", {
      phone,
      password,
      email,
      date_of_birth: dateOfBirth,
      first_name: firstName ?? "",
      last_name: lastName ?? "",
    }),
  me: () => apiClient.get("/auth/me/"),
};

export const dealsApi = {
  list: (params?: { retailer?: number; category?: number; search?: string; page?: number; ordering?: string }) =>
    apiClient.get("/deals/", { params }),
  detail: (id: number) => apiClient.get(`/deals/${id}/`),
};

export const productsApi = {
  list: (params?: { retailer?: number; category?: number; search?: string; page?: number }) =>
    apiClient.get("/products/", { params }),
  detail: (id: number) => apiClient.get(`/products/${id}/`),
};

export const categoriesApi = {
  tree: () => apiClient.get("/categories/tree/"),
  list: (params?: { retailer?: number }) => apiClient.get("/categories/", { params }),
};

export const retailersApi = {
  list: () => apiClient.get("/retailers/"),
};

export const subscriptionsApi = {
  list: () => apiClient.get("/subscriptions/"),
  create: (data: { target_type: string; product_id?: number; category_id?: number; retailer_id?: number }) =>
    apiClient.post("/subscriptions/", data),
  activate: (id: number) => apiClient.post(`/subscriptions/${id}/activate/`),
  deactivate: (id: number) => apiClient.post(`/subscriptions/${id}/deactivate/`),
  destroy: (id: number) => apiClient.delete(`/subscriptions/${id}/`),
};

export const paymentsApi = {
  initiate: (phone: string) => apiClient.post("/payments/initiate/", { phone }),
  status: () => apiClient.get("/payments/status/"),
};

export const adminApi = {
  stats: () => apiClient.get("/admin/stats/"),
  users: (params?: { search?: string; plan?: string; page?: number }) =>
    apiClient.get("/admin/users/", { params }),
  userDetail: (id: number) => apiClient.get(`/admin/users/${id}/`),
  mappings: () => apiClient.get("/admin/mappings/"),
  createMapping: (retailer_category_id: number, master_category_id: number) =>
    apiClient.post("/admin/mappings/", { retailer_category_id, master_category_id }),
  deleteMapping: (id: number) => apiClient.delete(`/admin/mappings/${id}/`),
  toggleAdmin: (id: number) => apiClient.post(`/admin/users/${id}/toggle_admin/`),
  setUserPlan: (id: number, plan: "premium" | "free") =>
    apiClient.post(`/admin/users/${id}/set-plan/`, { plan }),
  scraperRuns: (params?: { retailer?: string; status?: string; page?: number }) =>
    apiClient.get("/admin/scraper-runs/", { params }),
  triggerScrape: (retailer: string) =>
    apiClient.post(`/admin/trigger-scrape/${retailer}/`),
  uncategorizedProducts: (params?: { search?: string; retailer?: number; page?: number }) =>
    apiClient.get("/admin/uncategorized-products/", { params }),
  setProductCategory: (productId: number, masterCategoryId: number) =>
    apiClient.patch(`/admin/products/${productId}/set-category/`, { master_category_id: masterCategoryId }),
};
