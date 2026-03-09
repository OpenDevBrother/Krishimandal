import React, { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import DigitalTwinSidebar from "../components/DigitalTwinSidebar";
import VoiceAssistant from "../components/VoiceAssistant";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import {
  Home,
  FileText,
  Package,
  Bell,
  User,
  BookOpen,
} from "lucide-react-native";
import { useAuth } from "../services/authContext";
import { apiClient } from "../services/api";
import { colors } from "../constants/theme";
import type {
  AuthStackParamList,
  MainStackParamList,
  TabParamList,
} from "./types";

// Screens
import LoginScreen from "../screens/LoginScreen";
import DashboardScreen from "../screens/DashboardScreen";
import SchemeListScreen from "../screens/SchemeListScreen";
import SchemeDetailScreen from "../screens/SchemeDetailScreen";
import ApplicationFormScreen from "../screens/ApplicationFormScreen";
import ApplicationsScreen from "../screens/ApplicationsScreen";
import InventoryScreen from "../screens/InventoryScreen";
import AddEditInventoryScreen from "../screens/AddEditInventoryScreen";
import NotificationsScreen from "../screens/NotificationsScreen";
import LearningScreen from "../screens/LearningScreen";
import ProfileScreen from "../screens/ProfileScreen";

const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const MainStack = createNativeStackNavigator<MainStackParamList>();
const Tab = createBottomTabNavigator<TabParamList>();

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
    </AuthStack.Navigator>
  );
}

function TabNavigator() {
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchUnread = async () => {
    try {
      const path = await apiClient.farmPath("/notifications/unread-count");
      const data = await apiClient.get<{ unread_count: number }>(path);
      setUnreadCount(data.unread_count);
    } catch {
      // ignore
    }
  };

  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.gray[400],
        tabBarStyle: {
          backgroundColor: colors.white,
          borderTopWidth: 1,
          borderTopColor: colors.gray[200],
          paddingBottom: 5,
          paddingTop: 5,
          height: 60,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
        },
      }}
    >
      <Tab.Screen
        name="Home"
        component={DashboardScreen}
        options={{
          tabBarIcon: ({ color, size }) => <Home size={size} color={color} />,
        }}
      />
      <Tab.Screen
        name="Schemes"
        component={SchemeListScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <FileText size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Learning"
        component={LearningScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <BookOpen size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Inventory"
        component={InventoryScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Package size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Alerts"
        component={NotificationsScreen}
        options={{
          tabBarIcon: ({ color, size }) => <Bell size={size} color={color} />,
          tabBarBadge: unreadCount > 0 ? unreadCount : undefined,
          tabBarBadgeStyle: {
            backgroundColor: colors.red[500],
            fontSize: 10,
          },
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          tabBarIcon: ({ color, size }) => <User size={size} color={color} />,
        }}
      />
    </Tab.Navigator>
  );
}

function MainNavigator() {
  return (
    <MainStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.primary },
        headerTintColor: colors.white,
        headerTitleStyle: { fontWeight: "bold" },
      }}
    >
      <MainStack.Screen
        name="MainTabs"
        component={TabNavigator}
        options={{ headerShown: false }}
      />
      <MainStack.Screen
        name="SchemeDetail"
        component={SchemeDetailScreen}
        options={{ title: "Scheme Details" }}
      />
      <MainStack.Screen
        name="ApplicationForm"
        component={ApplicationFormScreen}
        options={{ title: "Apply" }}
      />
      <MainStack.Screen
        name="Applications"
        component={ApplicationsScreen}
        options={{ title: "My Applications" }}
      />
      <MainStack.Screen
        name="AddEditInventory"
        component={AddEditInventoryScreen}
        options={{ title: "Inventory Item" }}
      />
    </MainStack.Navigator>
  );
}

export default function AppNavigator() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <NavigationContainer>
      {isAuthenticated ? (
        <View style={{ flex: 1 }}>
          <MainNavigator />
          <DigitalTwinSidebar />
          <VoiceAssistant />
        </View>
      ) : (
        <AuthNavigator />
      )}
    </NavigationContainer>
  );
}
