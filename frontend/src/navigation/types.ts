import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { BottomTabScreenProps } from "@react-navigation/bottom-tabs";
import type {
  CompositeScreenProps,
  NavigatorScreenParams,
} from "@react-navigation/native";

// Auth stack (unauthenticated)
export type AuthStackParamList = {
  Login: undefined;
};

// Bottom tabs
export type TabParamList = {
  Home: undefined;
  Schemes: undefined;
  Learning: undefined;
  Inventory: undefined;
  Alerts: undefined;
  Profile: undefined;
};

// Main stack (authenticated) — contains tabs + detail screens
export type MainStackParamList = {
  MainTabs: NavigatorScreenParams<TabParamList>;
  SchemeDetail: { schemeId: string };
  ApplicationForm: { schemeId: string };
  Applications: undefined;
  AddEditInventory: { itemId?: string };
};

// Root stack
export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainStackParamList>;
};

// Screen prop types
export type LoginScreenProps = NativeStackScreenProps<AuthStackParamList, "Login">;

export type DashboardScreenProps = CompositeScreenProps<
  BottomTabScreenProps<TabParamList, "Home">,
  NativeStackScreenProps<MainStackParamList>
>;

export type SchemeListScreenProps = CompositeScreenProps<
  BottomTabScreenProps<TabParamList, "Schemes">,
  NativeStackScreenProps<MainStackParamList>
>;

export type SchemeDetailScreenProps = NativeStackScreenProps<
  MainStackParamList,
  "SchemeDetail"
>;

export type ApplicationFormScreenProps = NativeStackScreenProps<
  MainStackParamList,
  "ApplicationForm"
>;

export type ApplicationsScreenProps = NativeStackScreenProps<
  MainStackParamList,
  "Applications"
>;

export type InventoryScreenProps = CompositeScreenProps<
  BottomTabScreenProps<TabParamList, "Inventory">,
  NativeStackScreenProps<MainStackParamList>
>;

export type AddEditInventoryScreenProps = NativeStackScreenProps<
  MainStackParamList,
  "AddEditInventory"
>;

export type NotificationsScreenProps = BottomTabScreenProps<
  TabParamList,
  "Alerts"
>;

export type LearningScreenProps = BottomTabScreenProps<TabParamList, "Learning">;

export type ProfileScreenProps = BottomTabScreenProps<TabParamList, "Profile">;
