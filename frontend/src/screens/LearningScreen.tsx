import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  FlatList,
  Image,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Linking,
  Modal,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  BookOpen,
  Play,
  Search,
  Send,
  Bot,
  User,
  Sparkles,
  ExternalLink,
  Leaf,
  Activity,
  ThermometerSun,
  Droplets,
  AlertTriangle,
  Headphones,
  FileText,
  ChevronDown,
} from "lucide-react-native";
import Toast from "react-native-toast-message";
import { apiClient } from "../services/api";
import Header from "../components/Header";
import Card from "../components/Card";
import MarkdownRenderer from "../components/Markdown";
import { colors } from "../constants/theme";

// ── Types ────────────────────────────────────────────────────────────────────

interface LearningContent {
  content_id: string;
  title: string;
  content_type: string;
  language: string;
  topic: string;
  url: string;
  duration_minutes: number;
  relevance_score: number;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: string[];
  confidence?: number;
  pipeline?: string;
  timestamp: Date;
}

interface FarmContext {
  crop?: string;
  growth_stage?: string;
  health_score?: number;
  ndvi?: number;
  moisture?: number;
  weather_condition?: string;
  temperature?: number;
}

interface YTVideo {
  videoId: string;
  title: string;
  channel: string;
  thumbnail: string;
  topic: string;
}

// ── Constants ────────────────────────────────────────────────────────────────

const TOPICS = [
  { key: "all", label: "All Topics" },
  { key: "pest_control", label: "Pest Control" },
  { key: "organic_farming", label: "Organic Farming" },
  { key: "drip_irrigation", label: "Drip Irrigation" },
  { key: "soil_health", label: "Soil Health" },
  { key: "water_management", label: "Water Mgmt" },
  { key: "pm_kisan", label: "PM-KISAN" },
  { key: "pmfby", label: "PMFBY" },
];

const TOPIC_SEARCH_QUERIES: Record<string, string> = {
  all: "Indian farming agriculture best practices hindi",
  pest_control: "integrated pest management IPM indian farming hindi",
  organic_farming: "organic farming zero budget natural farming india hindi",
  drip_irrigation: "drip irrigation setup india farming hindi",
  soil_health: "soil health card india farming hindi",
  water_management: "rainwater harvesting water management agriculture india",
  pm_kisan: "PM KISAN yojana registration hindi",
  pmfby: "PMFBY fasal bima crop insurance india hindi",
};

const SUGGESTED_QUESTIONS = [
  "How do I manage pests without chemicals?",
  "What is the best irrigation schedule for wheat?",
  "How to improve soil organic carbon?",
  "Which government schemes can help me?",
  "How do I start organic farming?",
];

const LANGUAGES = [
  { code: "en", label: "English", native: "English" },
  { code: "hi", label: "Hindi", native: "हिन्दी" },
  { code: "bn", label: "Bengali", native: "বাংলা" },
  { code: "te", label: "Telugu", native: "తెలుగు" },
  { code: "mr", label: "Marathi", native: "मराठी" },
  { code: "ta", label: "Tamil", native: "தமிழ்" },
  { code: "gu", label: "Gujarati", native: "ગુજરાતી" },
  { code: "kn", label: "Kannada", native: "ಕನ್ನಡ" },
  { code: "ml", label: "Malayalam", native: "മലയാളം" },
  { code: "or", label: "Odia", native: "ଓଡ଼ିଆ" },
  { code: "pa", label: "Punjabi", native: "ਪੰਜਾਬੀ" },
  { code: "as", label: "Assamese", native: "অসমীয়া" },
  { code: "ur", label: "Urdu", native: "اردو" },
];

type TabKey = "videos" | "content" | "chatbot";

// ── Component ────────────────────────────────────────────────────────────────

export default function LearningScreen() {
  const [activeTab, setActiveTab] = useState<TabKey>("videos");
  const [selectedTopic, setSelectedTopic] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Videos
  const [ytVideos, setYtVideos] = useState<YTVideo[]>([]);
  const [ytLoading, setYtLoading] = useState(false);
  const [ytSearched, setYtSearched] = useState(false);

  // Content
  const [learningContent, setLearningContent] = useState<LearningContent[]>([]);
  const [loadingContent, setLoadingContent] = useState(false);

  // Chatbot
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [farmContext, setFarmContext] = useState<FarmContext | null>(null);
  const [farmContextLoading, setFarmContextLoading] = useState(false);
  const [selectedLang, setSelectedLang] = useState("en");
  const [langModalOpen, setLangModalOpen] = useState(false);
  const [showFarmContext, setShowFarmContext] = useState(false);
  const chatScrollRef = useRef<ScrollView>(null);

  // ── Effects ──────────────────────────────────────────────────────────────

  useEffect(() => {
    fetchFarmContext();
  }, []);

  useEffect(() => {
    if (activeTab === "videos") fetchYouTubeVideos();
  }, [activeTab, selectedTopic, farmContext]);

  useEffect(() => {
    if (activeTab === "content") fetchContent();
  }, [activeTab, selectedTopic]);

  useEffect(() => {
    setTimeout(() => chatScrollRef.current?.scrollToEnd({ animated: true }), 100);
  }, [messages]);

  // ── Data fetching ────────────────────────────────────────────────────────

  const fetchYouTubeVideos = async () => {
    setYtLoading(true);
    setYtSearched(true);
    const topicTag = selectedTopic === "all" ? "agriculture" : selectedTopic;

    let query: string;
    if (searchQuery.trim()) {
      query = searchQuery.trim();
      if (farmContext?.crop) query += ` ${farmContext.crop}`;
      query += " indian agriculture farming";
    } else if (selectedTopic === "all" && farmContext?.crop) {
      const parts = [farmContext.crop];
      if (farmContext.growth_stage) parts.push(farmContext.growth_stage, "stage");
      parts.push("farming best practices india hindi");
      query = parts.join(" ");
    } else {
      query = TOPIC_SEARCH_QUERIES[selectedTopic] || TOPIC_SEARCH_QUERIES.all;
      if (farmContext?.crop) query += ` ${farmContext.crop}`;
    }

    try {
      const res = await apiClient.get<{ videos: any[]; source: string }>(
        `/youtube/search?q=${encodeURIComponent(query)}&max_results=12`
      );
      const videos: YTVideo[] = (res.videos || []).map((v: any) => {
        const id = v.videoId || v.video_id || "";
        const fallback = `https://img.youtube.com/vi/${id}/mqdefault.jpg`;
        const raw = v.thumbnail || fallback;
        // Force https — Android blocks cleartext http
        const thumb = raw.replace(/^http:\/\//, "https://");
        return {
          videoId: id,
          title: v.title || "",
          channel: v.channel || v.uploaderName || v.author || "",
          thumbnail: thumb,
          topic: topicTag,
        };
      });
      setYtVideos(videos);
    } catch {
      setYtVideos([]);
    } finally {
      setYtLoading(false);
    }
  };

  const fetchContent = async () => {
    setLoadingContent(true);
    try {
      const topic = selectedTopic === "all" ? undefined : selectedTopic;
      const url = `/learning/content${topic ? `?topic=${topic}` : ""}`;
      const data = await apiClient.get<LearningContent[]>(url);
      setLearningContent(data);
    } catch {
      Toast.show({ type: "error", text1: "Could not load learning content" });
    } finally {
      setLoadingContent(false);
    }
  };

  const fetchFarmContext = async () => {
    setFarmContextLoading(true);
    try {
      const farmerId = (await AsyncStorage.getItem("farmer_id")) || "F1001";
      const [profileRes, stateRes] = await Promise.allSettled([
        apiClient.get<any>(`/farm/${farmerId}`),
        apiClient.get<any>(await apiClient.farmPath("/state")),
      ]);

      const ctx: FarmContext = {};
      if (profileRes.status === "fulfilled" && profileRes.value.current_crops?.[0]) {
        const crop = profileRes.value.current_crops[0];
        ctx.crop = crop.crop_type;
        ctx.growth_stage = crop.growth_stage;
      }
      if (stateRes.status === "fulfilled") {
        const s = stateRes.value;
        ctx.health_score = s.health_score;
        ctx.ndvi = s.ndvi_mean;
        ctx.moisture = s.soil_moisture_pct;
        if (s.weather) {
          ctx.weather_condition = s.weather.condition;
          ctx.temperature = s.weather.temperature_c;
        }
      }
      setFarmContext(ctx);

      const contextMsg = ctx.crop
        ? `I can see you're growing ${ctx.crop} (${ctx.growth_stage} stage) with a health score of ${ctx.health_score}/100. Ask me anything about farming!`
        : "I'm your farming knowledge assistant. Ask me about pest control, organic farming, irrigation, government schemes, and more!";

      setMessages([
        { id: "welcome", role: "system", content: contextMsg, timestamp: new Date() },
      ]);
    } catch {
      setMessages([
        {
          id: "welcome",
          role: "system",
          content:
            "I'm your farming knowledge assistant powered by RAG. Ask me about pest control, organic farming, irrigation, schemes, and more!",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setFarmContextLoading(false);
    }
  };

  // ── Chat handler ─────────────────────────────────────────────────────────

  const sendChatMessage = useCallback(
    async (text?: string) => {
      const query = (text || chatInput).trim();
      if (!query || chatLoading) return;

      const userMsg: ChatMessage = {
        id: Date.now().toString(),
        role: "user",
        content: query,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setChatInput("");
      setChatLoading(true);

      try {
        const langObj = LANGUAGES.find((l) => l.code === selectedLang);
        const langInstruction = `[IMPORTANT: You MUST respond in ${langObj?.label || selectedLang} (${langObj?.native || ""}) only.] `;

        let enrichedQuery = langInstruction + query;
        if (farmContext?.crop) {
          enrichedQuery = `${langInstruction}[Farm context: crop=${farmContext.crop}, stage=${farmContext.growth_stage}, health=${farmContext.health_score}/100, NDVI=${farmContext.ndvi}, moisture=${farmContext.moisture}%] ${query}`;
        }

        const farmerId = (await AsyncStorage.getItem("farmer_id")) || "F1001";
        const res = await apiClient.post<{
          answer: string;
          sources?: string[];
          confidence?: number;
          pipeline?: string;
        }>("/rag/ask", {
          query: enrichedQuery,
          farmer_id: farmerId,
          language: selectedLang,
        });

        const assistantMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: res.answer,
          sources: res.sources,
          confidence: res.confidence,
          pipeline: res.pipeline,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMsg]);

        if (res.confidence && res.confidence < 0.7) {
          setMessages((prev) => [
            ...prev,
            {
              id: (Date.now() + 2).toString(),
              role: "system",
              content:
                "This answer has lower confidence. Contact your local KVK at 1800-180-1551 (toll-free) for expert advice.",
              timestamp: new Date(),
            },
          ]);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: "Sorry, I couldn't process your question. Please try again.",
            timestamp: new Date(),
          },
        ]);
      } finally {
        setChatLoading(false);
      }
    },
    [chatInput, chatLoading, farmContext, selectedLang]
  );

  // ── Helpers ──────────────────────────────────────────────────────────────

  const stripHtml = (html: string) => html.replace(/<[^>]*>/g, "");

  const getContentTypeIcon = (type: string) => {
    if (type === "video") return <Play size={14} color={colors.red[600]} />;
    if (type === "audio") return <Headphones size={14} color={colors.purple[600]} />;
    return <FileText size={14} color={colors.blue[600]} />;
  };

  const getContentTypeBg = (type: string) => {
    if (type === "video") return colors.red[50];
    if (type === "audio") return colors.purple[50];
    return colors.blue[50];
  };

  // ── Render ───────────────────────────────────────────────────────────────

  const [failedThumbs, setFailedThumbs] = useState<Set<string>>(new Set());

  const renderVideoItem = ({ item }: { item: YTVideo }) => {
    const fallbackUri = `https://img.youtube.com/vi/${item.videoId}/mqdefault.jpg`;
    const thumbUri = failedThumbs.has(item.videoId) ? fallbackUri : (item.thumbnail || fallbackUri);

    return (
    <TouchableOpacity
      style={styles.videoCard}
      activeOpacity={0.8}
      onPress={() => Linking.openURL(`https://www.youtube.com/watch?v=${item.videoId}`)}
    >
      <Image
        source={{ uri: thumbUri }}
        style={styles.videoThumb}
        resizeMode="cover"
        onError={() => {
          setFailedThumbs((prev) => new Set(prev).add(item.videoId));
        }}
      />
      <View style={styles.playOverlay}>
        <View style={styles.playButton}>
          <Play size={20} color={colors.primary} fill={colors.primary} />
        </View>
      </View>
      <View style={styles.videoInfo}>
        <Text style={styles.videoTitle} numberOfLines={2}>
          {stripHtml(item.title)}
        </Text>
        <View style={styles.videoMeta}>
          <Text style={styles.videoChannel} numberOfLines={1}>
            {item.channel}
          </Text>
          <View style={styles.topicBadge}>
            <Text style={styles.topicBadgeText}>
              {item.topic.replace(/_/g, " ")}
            </Text>
          </View>
        </View>
        <View style={styles.watchRow}>
          <Text style={styles.watchText}>Watch on YouTube</Text>
          <ExternalLink size={12} color={colors.primary} />
        </View>
      </View>
    </TouchableOpacity>
  );
  };

  const getReadLabel = (type: string) => {
    if (type === "video") return "Watch";
    if (type === "audio") return "Listen";
    return "Read";
  };

  const renderContentItem = ({ item }: { item: LearningContent }) => (
    <Card style={styles.contentCard}>
      <View style={styles.contentRow}>
        <View style={[styles.contentIcon, { backgroundColor: getContentTypeBg(item.content_type) }]}>
          {getContentTypeIcon(item.content_type)}
        </View>
        <View style={styles.contentBody}>
          <Text style={styles.contentTitle} numberOfLines={2}>
            {item.title}
          </Text>
          <View style={styles.contentMeta}>
            <Text style={styles.contentDuration}>{item.duration_minutes} min</Text>
            <View style={styles.topicBadge}>
              <Text style={styles.topicBadgeText}>
                {item.topic.replace(/_/g, " ").replace(/-/g, " ")}
              </Text>
            </View>
            <View style={[styles.topicBadge, { backgroundColor: colors.gray[100] }]}>
              <Text style={[styles.topicBadgeText, { color: colors.gray[600] }]}>
                {item.content_type.toUpperCase()}
              </Text>
            </View>
          </View>
        </View>
        <View style={styles.contentRight}>
          <View style={styles.contentScore}>
            <Text style={styles.scoreText}>{Math.round(item.relevance_score * 100)}%</Text>
            <Text style={styles.scoreLabel}>match</Text>
          </View>
          {item.url && item.url !== "#" && (
            <TouchableOpacity
              style={styles.readBtn}
              onPress={() => Linking.openURL(item.url)}
              activeOpacity={0.7}
            >
              <Text style={styles.readBtnText}>{getReadLabel(item.content_type)}</Text>
              <ExternalLink size={10} color={colors.primary} />
            </TouchableOpacity>
          )}
        </View>
      </View>
    </Card>
  );

  const renderChatMessage = ({ item: msg }: { item: ChatMessage }) => (
    <View
      style={[
        styles.msgRow,
        msg.role === "user" ? styles.msgRowUser : styles.msgRowBot,
      ]}
    >
      {msg.role !== "user" && (
        <View style={styles.botAvatar}>
          <Bot size={16} color={colors.primary} />
        </View>
      )}
      <View
        style={[
          styles.msgBubble,
          msg.role === "user" ? styles.userBubble : styles.botBubble,
        ]}
      >
        <Text
          style={[
            styles.msgText,
            msg.role === "user" ? styles.userMsgText : styles.botMsgText,
          ]}
        >
          {msg.content}
        </Text>
        {msg.sources && msg.sources.length > 0 && (
          <View style={styles.sourcesWrap}>
            <View style={styles.sourcesHeader}>
              <BookOpen size={11} color={colors.blue[600]} />
              <Text style={styles.sourcesTitle}>Sources</Text>
            </View>
            {msg.sources.map((src, i) => (
              <Text key={i} style={styles.sourceItem}>
                {i + 1}. {src}
              </Text>
            ))}
          </View>
        )}
        {msg.confidence !== undefined && (
          <View style={styles.confidenceRow}>
            <Text style={styles.confidenceText}>
              Confidence: {Math.round(msg.confidence * 100)}%
            </Text>
            {msg.pipeline && (
              <View style={styles.pipelineBadge}>
                <Text style={styles.pipelineText}>{msg.pipeline}</Text>
              </View>
            )}
          </View>
        )}
      </View>
      {msg.role === "user" && (
        <View style={styles.userAvatar}>
          <User size={16} color={colors.gray[600]} />
        </View>
      )}
    </View>
  );

  return (
    <View style={styles.container}>
      <Header />

      {/* Sub-header */}
      <View style={styles.subHeader}>
        <View style={styles.headerIcon}>
          <BookOpen size={20} color={colors.primary} />
        </View>
        <View>
          <Text style={styles.subHeaderTitle}>Learning Platform</Text>
          <Text style={styles.subHeaderSub}>Learn, ask questions, and grow</Text>
        </View>
      </View>

      {/* Tabs */}
      <View style={styles.tabBar}>
        {([
          { key: "videos" as TabKey, label: "Videos", Icon: Play },
          { key: "content" as TabKey, label: "Content", Icon: BookOpen },
          { key: "chatbot" as TabKey, label: "AI Expert", Icon: Bot },
        ] as const).map((tab) => {
          const active = activeTab === tab.key;
          return (
            <TouchableOpacity
              key={tab.key}
              style={[styles.tab, active && styles.tabActive]}
              onPress={() => setActiveTab(tab.key)}
              activeOpacity={0.7}
            >
              <tab.Icon size={14} color={active ? colors.primary : colors.gray[500]} />
              <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>
                {tab.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Topic filter (videos & content tabs) */}
      {activeTab !== "chatbot" && (
        <View style={styles.filterSection}>
          <View style={styles.searchRow}>
            <Search size={16} color={colors.gray[400]} />
            <TextInput
              style={styles.searchInput}
              value={searchQuery}
              onChangeText={setSearchQuery}
              placeholder={
                activeTab === "videos"
                  ? "Search farming videos..."
                  : "Search topics..."
              }
              placeholderTextColor={colors.gray[400]}
              onSubmitEditing={() => {
                if (activeTab === "videos") fetchYouTubeVideos();
              }}
              returnKeyType="search"
            />
          </View>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.topicScroll}
          >
            {TOPICS.map((t) => (
              <TouchableOpacity
                key={t.key}
                style={[
                  styles.topicChip,
                  selectedTopic === t.key && styles.topicChipActive,
                ]}
                onPress={() => setSelectedTopic(t.key)}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.topicChipText,
                    selectedTopic === t.key && styles.topicChipTextActive,
                  ]}
                >
                  {t.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}

      {/* ── Videos Tab ──────────────────────────────────────────────────── */}
      {activeTab === "videos" && (
        <View style={styles.flex1}>
          {ytLoading ? (
            <View style={styles.center}>
              <ActivityIndicator size="large" color={colors.primary} />
              <Text style={styles.loadingText}>Searching YouTube...</Text>
            </View>
          ) : ytVideos.length > 0 ? (
            <FlatList
              data={ytVideos}
              keyExtractor={(item) => item.videoId}
              renderItem={renderVideoItem}
              numColumns={2}
              columnWrapperStyle={styles.videoRow}
              contentContainerStyle={styles.listPadding}
              showsVerticalScrollIndicator={false}
            />
          ) : ytSearched ? (
            <View style={styles.center}>
              <Play size={40} color={colors.gray[300]} />
              <Text style={styles.emptyTitle}>Could not fetch videos</Text>
              <Text style={styles.emptySubtitle}>
                The video search service may be unavailable
              </Text>
              <TouchableOpacity
                style={styles.ytButton}
                onPress={() =>
                  Linking.openURL(
                    `https://www.youtube.com/results?search_query=${encodeURIComponent(
                      farmContext?.crop
                        ? `${farmContext.crop} farming india`
                        : "indian farming agriculture"
                    )}`
                  )
                }
              >
                <Play size={16} color={colors.white} />
                <Text style={styles.ytButtonText}>Search on YouTube</Text>
              </TouchableOpacity>
            </View>
          ) : null}
        </View>
      )}

      {/* ── Content Tab ─────────────────────────────────────────────────── */}
      {activeTab === "content" && (
        <View style={styles.flex1}>
          {loadingContent ? (
            <View style={styles.center}>
              <ActivityIndicator size="large" color={colors.primary} />
            </View>
          ) : learningContent.length > 0 ? (
            <FlatList
              data={learningContent}
              keyExtractor={(item) => item.content_id}
              renderItem={renderContentItem}
              contentContainerStyle={styles.listPadding}
              showsVerticalScrollIndicator={false}
            />
          ) : (
            <View style={styles.center}>
              <Text style={styles.emptySubtitle}>No content available for this topic.</Text>
            </View>
          )}
        </View>
      )}

      {/* ── Chatbot Tab ─────────────────────────────────────────────────── */}
      {activeTab === "chatbot" && (
        <KeyboardAvoidingView
          style={styles.flex1}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
        >
          {/* Farm Context Toggle */}
          <TouchableOpacity
            style={styles.farmContextToggle}
            onPress={() => setShowFarmContext(!showFarmContext)}
            activeOpacity={0.7}
          >
            <Activity size={14} color={colors.primary} />
            <Text style={styles.farmContextToggleText}>Your Farm Context</Text>
            <ChevronDown
              size={14}
              color={colors.gray[400]}
              style={showFarmContext ? { transform: [{ rotate: "180deg" }] } : undefined}
            />
          </TouchableOpacity>

          {showFarmContext && (
            <Card style={styles.farmContextCard}>
              {farmContextLoading ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : farmContext ? (
                <View style={styles.contextItems}>
                  {farmContext.crop && (
                    <View style={styles.contextRow}>
                      <Leaf size={13} color={colors.green[600]} />
                      <Text style={styles.contextLabel}>{farmContext.crop}</Text>
                      <View style={styles.stageBadge}>
                        <Text style={styles.stageBadgeText}>
                          {farmContext.growth_stage}
                        </Text>
                      </View>
                    </View>
                  )}
                  {farmContext.health_score !== undefined && (
                    <View style={styles.contextRow}>
                      <Activity
                        size={13}
                        color={
                          farmContext.health_score >= 70
                            ? colors.green[600]
                            : colors.amber[500]
                        }
                      />
                      <Text style={styles.contextLabel}>
                        Health: {farmContext.health_score}/100
                      </Text>
                    </View>
                  )}
                  {farmContext.moisture !== undefined && (
                    <View style={styles.contextRow}>
                      <Droplets size={13} color={colors.blue[500]} />
                      <Text style={styles.contextLabel}>
                        Moisture: {farmContext.moisture}%
                      </Text>
                    </View>
                  )}
                  {farmContext.temperature !== undefined && (
                    <View style={styles.contextRow}>
                      <ThermometerSun size={13} color={colors.amber[500]} />
                      <Text style={styles.contextLabel}>
                        {Math.round(farmContext.temperature)}°C —{" "}
                        {farmContext.weather_condition}
                      </Text>
                    </View>
                  )}
                  <View style={styles.contextNote}>
                    <Sparkles size={11} color={colors.amber[500]} />
                    <Text style={styles.contextNoteText}>
                      AI uses this for personalized answers
                    </Text>
                  </View>

                  {/* Suggested actions */}
                  {farmContext.health_score !== undefined &&
                    farmContext.health_score < 70 && (
                      <TouchableOpacity
                        style={[styles.suggestBtn, { backgroundColor: colors.red[50] }]}
                        onPress={() =>
                          sendChatMessage("My crop health is low, what should I do?")
                        }
                      >
                        <AlertTriangle size={10} color={colors.red[700]} />
                        <Text style={[styles.suggestBtnText, { color: colors.red[700] }]}>
                          Low health — get advice
                        </Text>
                      </TouchableOpacity>
                    )}
                  {farmContext.moisture !== undefined && farmContext.moisture < 30 && (
                    <TouchableOpacity
                      style={[styles.suggestBtn, { backgroundColor: colors.blue[50] }]}
                      onPress={() =>
                        sendChatMessage(
                          "My soil moisture is critically low. What irrigation should I use?"
                        )
                      }
                    >
                      <Droplets size={10} color={colors.blue[700]} />
                      <Text style={[styles.suggestBtnText, { color: colors.blue[700] }]}>
                        Low moisture — irrigation tips
                      </Text>
                    </TouchableOpacity>
                  )}
                  <TouchableOpacity
                    style={[styles.suggestBtn, { backgroundColor: colors.primaryLight }]}
                    onPress={() =>
                      sendChatMessage(
                        `What are the best practices for ${farmContext.crop || "my crop"} in the ${farmContext.growth_stage || "current"} stage?`
                      )
                    }
                  >
                    <Leaf size={10} color={colors.primary} />
                    <Text style={[styles.suggestBtnText, { color: colors.primary }]}>
                      Best practices for {farmContext.crop || "crops"}
                    </Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <Text style={styles.noDataText}>No farm data loaded</Text>
              )}
            </Card>
          )}

          {/* Chat header */}
          <View style={styles.chatHeader}>
            <Bot size={18} color={colors.primary} />
            <View style={styles.chatHeaderText}>
              <Text style={styles.chatHeaderTitle}>KrishiMandal AI Expert</Text>
              <Text style={styles.chatHeaderSub}>RAG-powered agricultural knowledge</Text>
            </View>
            <TouchableOpacity
              style={styles.langButton}
              onPress={() => setLangModalOpen(true)}
            >
              <Text style={styles.langButtonText}>
                {LANGUAGES.find((l) => l.code === selectedLang)?.native || "English"}
              </Text>
              <ChevronDown size={12} color={colors.gray[400]} />
            </TouchableOpacity>
          </View>

          {/* Messages */}
          <ScrollView
            ref={chatScrollRef}
            style={styles.chatMessages}
            contentContainerStyle={styles.chatMessagesContent}
            showsVerticalScrollIndicator={false}
          >
            {messages.map((msg) => (
              <View
                key={msg.id}
                style={[
                  styles.msgRow,
                  msg.role === "user" ? styles.msgRowUser : styles.msgRowBot,
                ]}
              >
                {msg.role !== "user" && (
                  <View style={styles.botAvatar}>
                    <Bot size={16} color={colors.primary} />
                  </View>
                )}
                <View
                  style={[
                    styles.msgBubble,
                    msg.role === "user" ? styles.userBubble : styles.botBubble,
                  ]}
                >
                  {msg.role === "user" ? (
                    <Text style={[styles.msgText, styles.userMsgText]}>
                      {msg.content}
                    </Text>
                  ) : (
                    <MarkdownRenderer
                      fontSize={13}
                      color={colors.gray[800]}
                    >
                      {msg.content}
                    </MarkdownRenderer>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <View style={styles.sourcesWrap}>
                      <View style={styles.sourcesHeader}>
                        <BookOpen size={11} color={colors.blue[600]} />
                        <Text style={styles.sourcesTitle}>Sources</Text>
                      </View>
                      {msg.sources.map((src, i) => (
                        <Text key={i} style={styles.sourceItem}>
                          {i + 1}. {src}
                        </Text>
                      ))}
                    </View>
                  )}
                  {msg.confidence !== undefined && (
                    <View style={styles.confidenceRow}>
                      <Text style={styles.confidenceText}>
                        Confidence: {Math.round(msg.confidence * 100)}%
                      </Text>
                      {msg.pipeline && (
                        <View style={styles.pipelineBadge}>
                          <Text style={styles.pipelineText}>{msg.pipeline}</Text>
                        </View>
                      )}
                    </View>
                  )}
                </View>
                {msg.role === "user" && (
                  <View style={styles.userAvatar}>
                    <User size={16} color={colors.gray[600]} />
                  </View>
                )}
              </View>
            ))}

            {chatLoading && (
              <View style={[styles.msgRow, styles.msgRowBot]}>
                <View style={styles.botAvatar}>
                  <Bot size={16} color={colors.primary} />
                </View>
                <View style={styles.botBubble}>
                  <View style={styles.loadingRow}>
                    <ActivityIndicator size="small" color={colors.primary} />
                    <Text style={styles.loadingChatText}>
                      Searching knowledge base...
                    </Text>
                  </View>
                </View>
              </View>
            )}

            {/* Suggested questions */}
            {messages.length <= 1 && !chatLoading && (
              <View style={styles.suggestedSection}>
                <Text style={styles.suggestedLabel}>Try asking</Text>
                {SUGGESTED_QUESTIONS.map((q) => (
                  <TouchableOpacity
                    key={q}
                    style={styles.suggestedQ}
                    onPress={() => sendChatMessage(q)}
                    activeOpacity={0.7}
                  >
                    <Text style={styles.suggestedQText}>{q}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </ScrollView>

          {/* Chat Input */}
          <View style={styles.chatInputWrap}>
            <TextInput
              style={styles.chatInput}
              value={chatInput}
              onChangeText={setChatInput}
              placeholder="Ask about farming, schemes, pest control..."
              placeholderTextColor={colors.gray[400]}
              editable={!chatLoading}
              onSubmitEditing={() => sendChatMessage()}
              returnKeyType="send"
            />
            <TouchableOpacity
              style={[
                styles.sendBtn,
                chatInput.trim() && !chatLoading
                  ? styles.sendBtnActive
                  : styles.sendBtnDisabled,
              ]}
              onPress={() => sendChatMessage()}
              disabled={!chatInput.trim() || chatLoading}
            >
              <Send size={18} color={chatInput.trim() && !chatLoading ? colors.white : colors.gray[400]} />
            </TouchableOpacity>
          </View>

          {/* Language Modal */}
          <Modal visible={langModalOpen} transparent animationType="slide">
            <TouchableOpacity
              style={styles.modalOverlay}
              activeOpacity={1}
              onPress={() => setLangModalOpen(false)}
            >
              <View style={styles.modalContent}>
                <Text style={styles.modalTitle}>Select Language</Text>
                <FlatList
                  data={LANGUAGES}
                  keyExtractor={(item) => item.code}
                  renderItem={({ item: lang }) => (
                    <TouchableOpacity
                      style={[
                        styles.langItem,
                        selectedLang === lang.code && styles.langItemActive,
                      ]}
                      onPress={() => {
                        setSelectedLang(lang.code);
                        setLangModalOpen(false);
                      }}
                    >
                      <Text
                        style={[
                          styles.langNative,
                          selectedLang === lang.code && styles.langNativeActive,
                        ]}
                      >
                        {lang.native}
                      </Text>
                      <Text style={styles.langLabel}>{lang.label}</Text>
                    </TouchableOpacity>
                  )}
                />
              </View>
            </TouchableOpacity>
          </Modal>
        </KeyboardAvoidingView>
      )}
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray[50] },
  flex1: { flex: 1 },

  // Sub-header
  subHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: colors.gray[200],
  },
  headerIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
  },
  subHeaderTitle: { fontSize: 16, fontWeight: "bold", color: colors.gray[900] },
  subHeaderSub: { fontSize: 11, color: colors.gray[500] },

  // Tabs
  tabBar: {
    flexDirection: "row",
    gap: 4,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: colors.white,
  },
  tab: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: colors.gray[100],
  },
  tabActive: {
    backgroundColor: colors.white,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  tabLabel: { fontSize: 12, fontWeight: "600", color: colors.gray[500] },
  tabLabelActive: { color: colors.primary },

  // Filter
  filterSection: { paddingHorizontal: 16, paddingVertical: 8, backgroundColor: colors.white },
  searchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.gray[50],
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.gray[200],
    paddingHorizontal: 12,
    marginBottom: 8,
  },
  searchInput: { flex: 1, paddingVertical: 10, fontSize: 14, color: colors.gray[800] },
  topicScroll: { marginBottom: 4 },
  topicChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.gray[300],
    marginRight: 6,
  },
  topicChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  topicChipText: { fontSize: 11, fontWeight: "600", color: colors.gray[600] },
  topicChipTextActive: { color: colors.white },

  // Center/empty
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32 },
  loadingText: { marginTop: 12, fontSize: 13, color: colors.gray[500] },
  emptyTitle: { fontSize: 14, fontWeight: "600", color: colors.gray[600], marginTop: 12 },
  emptySubtitle: { fontSize: 12, color: colors.gray[400], marginTop: 4, textAlign: "center" },
  ytButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 10,
    marginTop: 16,
  },
  ytButtonText: { color: colors.white, fontSize: 14, fontWeight: "600" },

  // Videos
  listPadding: { padding: 12 },
  videoRow: { gap: 10, marginBottom: 10 },
  videoCard: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: 12,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  videoThumb: { width: "100%", height: 100, backgroundColor: colors.gray[100] },
  playOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    height: 100,
    alignItems: "center",
    justifyContent: "center",
  },
  playButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.9)",
    alignItems: "center",
    justifyContent: "center",
  },
  videoInfo: { padding: 10 },
  videoTitle: { fontSize: 12, fontWeight: "600", color: colors.gray[800], marginBottom: 4 },
  videoMeta: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  videoChannel: { fontSize: 10, color: colors.gray[500], flex: 1, marginRight: 8 },
  topicBadge: {
    backgroundColor: colors.primaryLight,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
  },
  topicBadgeText: {
    fontSize: 9,
    fontWeight: "600",
    color: colors.primary,
    textTransform: "capitalize",
  },
  watchRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 6 },
  watchText: { fontSize: 11, fontWeight: "600", color: colors.primary },

  // Content
  contentCard: { marginBottom: 8 },
  contentRow: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  contentIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  contentBody: { flex: 1 },
  contentTitle: { fontSize: 13, fontWeight: "600", color: colors.gray[800], marginBottom: 4 },
  contentMeta: { flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" },
  contentDuration: { fontSize: 11, color: colors.gray[500] },
  contentRight: { alignItems: "flex-end", gap: 6 },
  contentScore: { alignItems: "flex-end" },
  scoreText: { fontSize: 13, fontWeight: "bold", color: colors.primary },
  scoreLabel: { fontSize: 9, color: colors.gray[400] },
  readBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.primaryLight,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
  },
  readBtnText: { fontSize: 11, fontWeight: "600", color: colors.primary },

  // Farm context
  farmContextToggle: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: colors.gray[200],
  },
  farmContextToggleText: {
    flex: 1,
    fontSize: 12,
    fontWeight: "bold",
    color: colors.gray[700],
  },
  farmContextCard: { marginHorizontal: 12, marginVertical: 6, padding: 12 },
  contextItems: { gap: 8 },
  contextRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  contextLabel: { fontSize: 12, color: colors.gray[600], flex: 1 },
  stageBadge: {
    backgroundColor: colors.primaryLight,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  stageBadgeText: {
    fontSize: 10,
    fontWeight: "600",
    color: colors.primary,
    textTransform: "capitalize",
  },
  contextNote: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingTop: 8,
    marginTop: 4,
    borderTopWidth: 1,
    borderTopColor: colors.gray[100],
  },
  contextNoteText: { fontSize: 10, color: colors.gray[500] },
  suggestBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 6,
  },
  suggestBtnText: { fontSize: 11, fontWeight: "500" },
  noDataText: { fontSize: 12, color: colors.gray[400] },

  // Chat header
  chatHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: colors.primaryLight,
    borderBottomWidth: 1,
    borderBottomColor: colors.gray[200],
  },
  chatHeaderText: { flex: 1 },
  chatHeaderTitle: { fontSize: 13, fontWeight: "bold", color: colors.primary },
  chatHeaderSub: { fontSize: 10, color: colors.gray[500] },
  langButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.white,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.gray[300],
  },
  langButtonText: { fontSize: 11, fontWeight: "500", color: colors.gray[700] },

  // Chat messages
  chatMessages: { flex: 1, backgroundColor: colors.gray[50] },
  chatMessagesContent: { padding: 12, gap: 8 },
  msgRow: { flexDirection: "row", gap: 6, alignItems: "flex-start" },
  msgRowUser: { justifyContent: "flex-end" },
  msgRowBot: { justifyContent: "flex-start" },
  botAvatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
  },
  userAvatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.gray[200],
    alignItems: "center",
    justifyContent: "center",
  },
  msgBubble: {
    maxWidth: "75%",
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  userBubble: {
    backgroundColor: colors.primary,
    borderBottomRightRadius: 4,
  },
  botBubble: {
    backgroundColor: colors.white,
    borderBottomLeftRadius: 4,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
    borderWidth: 1,
    borderColor: colors.gray[100],
  },
  msgText: { fontSize: 13, lineHeight: 20 },
  userMsgText: { color: colors.white },
  botMsgText: { color: colors.gray[800] },
  sourcesWrap: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.gray[100],
  },
  sourcesHeader: { flexDirection: "row", alignItems: "center", gap: 4, marginBottom: 4 },
  sourcesTitle: { fontSize: 10, fontWeight: "bold", color: colors.blue[600] },
  sourceItem: { fontSize: 10, color: colors.gray[500], marginBottom: 2 },
  confidenceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 6,
  },
  confidenceText: { fontSize: 10, color: colors.gray[400] },
  pipelineBadge: {
    backgroundColor: colors.gray[100],
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
  },
  pipelineText: { fontSize: 9, color: colors.gray[500] },
  loadingRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  loadingChatText: { fontSize: 13, color: colors.gray[500] },

  // Suggested
  suggestedSection: { gap: 6, paddingTop: 8 },
  suggestedLabel: {
    fontSize: 11,
    fontWeight: "600",
    color: colors.gray[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  suggestedQ: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.gray[200],
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  suggestedQText: { fontSize: 13, color: colors.gray[700] },

  // Chat input
  chatInputWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    padding: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.gray[200],
  },
  chatInput: {
    flex: 1,
    backgroundColor: colors.gray[50],
    borderRadius: 24,
    borderWidth: 1,
    borderColor: colors.gray[300],
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 14,
    color: colors.gray[800],
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  sendBtnActive: { backgroundColor: colors.primary },
  sendBtnDisabled: { backgroundColor: colors.gray[200] },

  // Language modal
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "flex-end",
  },
  modalContent: {
    backgroundColor: colors.white,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: "60%",
    paddingBottom: 30,
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: "bold",
    color: colors.gray[800],
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.gray[200],
  },
  langItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.gray[100],
  },
  langItemActive: { backgroundColor: colors.primaryLight },
  langNative: { fontSize: 15, color: colors.gray[700] },
  langNativeActive: { color: colors.primary, fontWeight: "600" },
  langLabel: { fontSize: 12, color: colors.gray[400] },
});
