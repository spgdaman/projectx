import { View, ActivityIndicator } from 'react-native';
import { useAuth } from '../store/auth';
import AuthStack from './AuthStack';
import AppStack from './AppStack';
import { colors } from '../theme';

export default function RootNavigator() {
  const { isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.primaryLight }}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return isAuthenticated ? <AppStack /> : <AuthStack />;
}
