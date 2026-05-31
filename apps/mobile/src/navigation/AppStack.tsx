import { createNativeStackNavigator } from '@react-navigation/native-stack';
import AppTabs from './AppTabs';
import UpgradeScreen from '../screens/UpgradeScreen';
import PaymentPendingScreen from '../screens/PaymentPendingScreen';
import {
  ShoppingListHomeScreen,
  ShoppingListBuilderScreen,
  ShoppingListResultScreen,
} from '../screens/ShoppingList';
import { OptimisationResult } from '@bargain-hunters/api-client';
import { colors } from '../theme';

export type AppStackParams = {
  MainTabs: undefined;
  Upgrade: undefined;
  PaymentPending: undefined;
  ShoppingListHome: undefined;
  ShoppingListBuilder: { listId: number };
  ShoppingListResult: { listId: number; result: OptimisationResult };
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
      <Stack.Screen name="ShoppingListHome" component={ShoppingListHomeScreen} options={{ title: 'Shopping Lists' }} />
      <Stack.Screen name="ShoppingListBuilder" component={ShoppingListBuilderScreen} options={{ title: 'Build List' }} />
      <Stack.Screen name="ShoppingListResult" component={ShoppingListResultScreen} options={{ title: 'Best Deals Found' }} />
    </Stack.Navigator>
  );
}
