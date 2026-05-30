import { useCallback, useEffect, useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import * as SplashScreen from "expo-splash-screen";

SplashScreen.preventAutoHideAsync();

const BRAND = {
  primary: "#E54416",
  primaryDark: "#C73D0F",
  primaryLight: "#FFF9F1",
  white: "#FFFFFF",
  whiteSub: "rgba(255,255,255,0.80)",
  textPrimary: "#111827",
  textSecondary: "#6B7280",
} as const;

const SPLASH_DURATION_MS = 2500;

function BrandedSplash() {
  return (
    <View style={styles.splash}>
      <View style={styles.logoContainer}>
        <Image
          source={require("./assets/icon.png")}
          style={styles.logoImage}
          resizeMode="contain"
        />
      </View>
      <Text style={styles.appName}>Bargain Hunters</Text>
      <Text style={styles.tagline}>Get the best deals near you</Text>
      <View style={styles.dotRow}>
        <View style={[styles.dot, styles.dotActive]} />
        <View style={styles.dot} />
        <View style={styles.dot} />
      </View>
    </View>
  );
}

function HomeScreen() {
  return (
    <View style={styles.home}>
      <StatusBar style="dark" />
      <View style={styles.homeBadge}>
        <Text style={styles.homeBadgeText}>Coming Soon</Text>
      </View>
      <Text style={styles.homeTitle}>Bargain Hunters</Text>
      <Text style={styles.homeSubtitle}>
        Your deals are on their way.{"\n"}Stay tuned.
      </Text>
    </View>
  );
}

export default function App() {
  const [appReady, setAppReady] = useState(false);
  const [splashDone, setSplashDone] = useState(false);

  useEffect(() => {
    // Simulate any init work here (fonts, auth check, etc.)
    const timer = setTimeout(() => setAppReady(true), SPLASH_DURATION_MS);
    return () => clearTimeout(timer);
  }, []);

  const onLayoutRootView = useCallback(async () => {
    if (appReady) {
      await SplashScreen.hideAsync();
      setSplashDone(true);
    }
  }, [appReady]);

  if (!appReady) {
    return (
      <>
        <StatusBar style="light" />
        <BrandedSplash />
      </>
    );
  }

  return (
    <View style={{ flex: 1 }} onLayout={onLayoutRootView}>
      {splashDone && <HomeScreen />}
    </View>
  );
}

const styles = StyleSheet.create({
  // ── Splash ──────────────────────────────────────────────────────────────────
  splash: {
    flex: 1,
    backgroundColor: BRAND.primary,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
  },
  logoContainer: {
    width: 96,
    height: 96,
    borderRadius: 24,
    backgroundColor: BRAND.white,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 28,
    shadowColor: BRAND.primaryDark,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  logoImage: {
    width: 72,
    height: 72,
    borderRadius: 16,
  },
  appName: {
    fontSize: 34,
    fontWeight: "700",
    color: BRAND.white,
    letterSpacing: 0.4,
    marginBottom: 8,
    textAlign: "center",
  },
  tagline: {
    fontSize: 16,
    fontWeight: "400",
    color: BRAND.whiteSub,
    marginBottom: 52,
    textAlign: "center",
  },
  dotRow: {
    flexDirection: "row",
    gap: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "rgba(255,255,255,0.35)",
  },
  dotActive: {
    backgroundColor: BRAND.white,
    width: 24,
  },

  // ── Home ────────────────────────────────────────────────────────────────────
  home: {
    flex: 1,
    backgroundColor: BRAND.primaryLight,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
  },
  homeBadge: {
    backgroundColor: "#FDEBD0",
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    marginBottom: 20,
  },
  homeBadgeText: {
    color: BRAND.primaryDark,
    fontSize: 13,
    fontWeight: "600",
    letterSpacing: 0.3,
  },
  homeTitle: {
    fontSize: 30,
    fontWeight: "700",
    color: BRAND.textPrimary,
    textAlign: "center",
    marginBottom: 12,
  },
  homeSubtitle: {
    fontSize: 16,
    color: BRAND.textSecondary,
    textAlign: "center",
    lineHeight: 24,
  },
});
