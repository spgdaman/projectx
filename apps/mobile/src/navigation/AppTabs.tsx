import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import DealsScreen from '../screens/DealsScreen';
import CreateAlertScreen from '../screens/CreateAlertScreen';
import MyAlertsScreen from '../screens/MyAlertsScreen';
import ProfileScreen from '../screens/ProfileScreen';
import { colors } from '../theme';

const Tab = createBottomTabNavigator();

function TabIcon({ emoji, focused }: { emoji: string; focused: boolean }) {
  return <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.5 }}>{emoji}</Text>;
}

export default function AppTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        headerStyle: { backgroundColor: colors.surface },
        headerTitleStyle: { color: colors.textPrimary, fontWeight: '700', fontSize: 18 },
        headerShadowVisible: false,
      }}
    >
      <Tab.Screen
        name="Deals"
        component={DealsScreen}
        options={{
          title: "Today's Deals",
          tabBarLabel: 'Deals',
          tabBarIcon: ({ focused }) => <TabIcon emoji="🏷️" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="CreateAlert"
        component={CreateAlertScreen}
        options={{
          title: 'Create Alert',
          tabBarLabel: 'Alert',
          tabBarIcon: ({ focused }) => <TabIcon emoji="🔔" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="MyAlerts"
        component={MyAlertsScreen}
        options={{
          title: 'My Alerts',
          tabBarLabel: 'My Alerts',
          tabBarIcon: ({ focused }) => <TabIcon emoji="📋" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          title: 'My Profile',
          tabBarLabel: 'Profile',
          tabBarIcon: ({ focused }) => <TabIcon emoji="👤" focused={focused} />,
        }}
      />
    </Tab.Navigator>
  );
}
