import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { colors } from "../theme";

export function SplashScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.icon}>🏷️</Text>
      <Text style={styles.appName}>Bargain Hunters</Text>
      <Text style={styles.tagline}>Get the best deals near you</Text>
      <ActivityIndicator style={styles.spinner} color="#FFFFFF" size="large" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
  },
  icon: {
    fontSize: 72,
    marginBottom: 20,
  },
  appName: {
    fontSize: 34,
    fontWeight: "700",
    color: "#FFFFFF",
    letterSpacing: 0.5,
    marginBottom: 8,
    textAlign: "center",
  },
  tagline: {
    fontSize: 16,
    fontWeight: "400",
    color: "rgba(255, 255, 255, 0.75)",
    marginBottom: 64,
    textAlign: "center",
  },
  spinner: {
    marginTop: 8,
  },
});
