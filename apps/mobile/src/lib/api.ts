import axios from 'axios';
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { configureShoppingList } from '@bargain-hunters/api-client';

// Production URL is the default. Override with EXPO_PUBLIC_API_URL for local dev
// (e.g. EXPO_PUBLIC_API_URL=http://10.0.2.2:8000/api/v1 for Android emulator)
const BASE = process.env.EXPO_PUBLIC_API_URL
  ?? 'https://www.bargainhunters.co.ke/api/v1';

const API_ORIGIN = BASE.replace(/\/api\/v1\/?$/, '');

configureShoppingList({
  baseUrl: API_ORIGIN,
  getToken: () => SecureStore.getItemAsync('access_token'),
});

export const apiClient = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
});

apiClient.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = await SecureStore.getItemAsync('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/auth/refresh/`, { refresh });
          await SecureStore.setItemAsync('access_token', data.access);
          original.headers.Authorization = `Bearer ${data.access}`;
          return apiClient(original);
        } catch {
          await SecureStore.deleteItemAsync('access_token');
          await SecureStore.deleteItemAsync('refresh_token');
        }
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: (phone: string, password: string) =>
    apiClient.post<{ access: string; refresh: string }>('/auth/login/', { phone, password }),
  register: (phone: string, password: string, email: string, dateOfBirth: string, firstName?: string, lastName?: string) =>
    apiClient.post<{ access: string; refresh: string }>('/auth/register/', {
      phone, password, email,
      date_of_birth: dateOfBirth,
      first_name: firstName ?? '',
      last_name: lastName ?? '',
    }),
  me: () => apiClient.get('/auth/me/'),
};

export const dealsApi = {
  list: (params?: { retailer?: number; category?: number; search?: string; page?: number }) =>
    apiClient.get('/deals/', { params }),
};

export const productsApi = {
  list: (params?: { search?: string; page?: number }) =>
    apiClient.get('/products/', { params }),
};

export const categoriesApi = {
  list: () => apiClient.get('/categories/'),
};

export const retailersApi = {
  list: () => apiClient.get('/retailers/'),
};

export const subscriptionsApi = {
  list: () => apiClient.get('/subscriptions/'),
  create: (data: { target_type: string; product_id?: number; category_id?: number; retailer_id?: number }) =>
    apiClient.post('/subscriptions/', data),
  activate: (id: number) => apiClient.post(`/subscriptions/${id}/activate/`),
  deactivate: (id: number) => apiClient.post(`/subscriptions/${id}/deactivate/`),
  destroy: (id: number) => apiClient.delete(`/subscriptions/${id}/`),
};

export const paymentsApi = {
  initiate: (phone: string) => apiClient.post('/payments/initiate/', { phone }),
  status: () => apiClient.get('/payments/status/'),
};
