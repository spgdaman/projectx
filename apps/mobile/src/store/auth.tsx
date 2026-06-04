import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import * as SecureStore from 'expo-secure-store';
import { authApi } from '../lib/api';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  is_staff: boolean;
  phone_number: string;
  date_of_birth: string | null;
  payment_status: boolean;
  is_free_tier: boolean;
  has_access: boolean;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (phone: string, password: string) => Promise<void>;
  register: (phone: string, password: string, email: string, dob: string, firstName?: string, lastName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    const { data } = await authApi.me();
    setUser({
      ...data.user,
      phone_number: data.phone_number,
      date_of_birth: data.date_of_birth ?? null,
      payment_status: data.payment_status,
      is_free_tier: data.is_free_tier,
      has_access: data.has_access,
    });
  }, []);

  useEffect(() => {
    async function checkAuth() {
      try {
        const token = await SecureStore.getItemAsync('access_token');
        if (!token) return;
        await fetchMe();
      } catch {
        try {
          await SecureStore.deleteItemAsync('access_token');
          await SecureStore.deleteItemAsync('refresh_token');
        } catch {}
      } finally {
        setIsLoading(false);
      }
    }
    checkAuth();
  }, [fetchMe]);

  const login = useCallback(async (phone: string, password: string) => {
    const { data } = await authApi.login(phone, password);
    await SecureStore.setItemAsync('access_token', data.access);
    await SecureStore.setItemAsync('refresh_token', data.refresh);
    await fetchMe();
  }, [fetchMe]);

  const register = useCallback(async (
    phone: string, password: string, email: string,
    dob: string, firstName?: string, lastName?: string
  ) => {
    const { data } = await authApi.register(phone, password, email, dob, firstName, lastName);
    await SecureStore.setItemAsync('access_token', data.access);
    await SecureStore.setItemAsync('refresh_token', data.refresh);
    try { await fetchMe(); } catch { /* tokens stored; session restores on next load */ }
  }, [fetchMe]);

  const logout = useCallback(async () => {
    await SecureStore.deleteItemAsync('access_token');
    await SecureStore.deleteItemAsync('refresh_token');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
