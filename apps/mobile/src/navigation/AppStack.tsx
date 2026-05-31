import { createNativeStackNavigator } from '@react-navigation/native-stack';
import AppTabs from './AppTabs';
import UpgradeScreen from '../screens/UpgradeScreen';
import PaymentPendingScreen from '../screens/PaymentPendingScreen';
import { colors } from '../theme';

export type AppStackParams = {
  MainTabs: undefined;
  Upgrade: undefined;
  PaymentPending: undefined;
};

const Stack = createNativeStackNavigator<AppStackParams>();

export default function AppStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.primary,
        headerTitleStyle: { color: colors.textPrimary, fontWeight: '700' },
      }}
    >
      <Stack.Screen name="MainTabs" component={AppTabs} options={{ headerShown: false }} />
      <Stack.Screen name="Upgrade" component={UpgradeScreen} options={{ title: 'Upgrade to Premium' }} />
      <Stack.Screen name="PaymentPending" component={PaymentPendingScreen} options={{ title: 'Processing Payment', headerBackVisible: false }} />
    </Stack.Navigator>
  );
}
