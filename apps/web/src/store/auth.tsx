"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authApi } from "@/lib/api";

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
  register: (phone: string, password: string, email: string, dateOfBirth: string, firstName?: string, lastName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    const { data } = await authApi.me();
    setUser({
      ...data.user,   // id, username, email, first_name, last_name, is_staff, date_joined
      phone_number: data.phone_number,
      date_of_birth: data.date_of_birth ?? null,
      payment_status: data.payment_status,
      is_free_tier: data.is_free_tier,
      has_access: data.has_access,
    });
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    fetchMe()
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      })
      .finally(() => setIsLoading(false));
  }, [fetchMe]);

  const login = useCallback(
    async (phone: string, password: string) => {
      const { data } = await authApi.login(phone, password);
      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);
      await fetchMe();
    },
    [fetchMe]
  );

  const register = useCallback(
    async (phone: string, password: string, email: string, dateOfBirth: string, firstName?: string, lastName?: string) => {
      const { data } = await authApi.register(phone, password, email, dateOfBirth, firstName, lastName);
      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);
      // fetchMe failure should not surface as a registration error —
      // the account was created; just let isAuthenticated stay false
      // so the login redirect will pick it up gracefully.
      try {
        await fetchMe();
      } catch {
        // swallow — tokens are stored, next page load will restore session
      }
    },
    [fetchMe]
  );

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated: !!user, login, register, logout }}  // eslint-disable-line
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
