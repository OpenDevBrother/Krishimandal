import { useState, useEffect, useRef } from "react";
import {
  BookOpen, Play, FileText, Headphones, Search,
  Send, Bot, User, Loader2, Sparkles, ExternalLink,
  Leaf, Activity, ThermometerSun, Droplets, AlertTriangle,
  Languages, ChevronDown,
} from "lucide-react";
import toast from "react-hot-toast";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Markdown from "../components/Markdown";
import { colors } from "../constants/theme";

// ── Types ─────────────────────────────────────────────────────────────────────

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

// ── Constants ─────────────────────────────────────────────────────────────────

const TOPICS = [
  { key: "all", label: "All Topics" },
  { key: "pest_control", label: "Pest Control" },
  { key: "organic_farming", label: "Organic Farming" },
  { key: "drip_irrigation", label: "Drip Irrigation" },
  { key: "soil_health", label: "Soil Health" },
  { key: "water_management", label: "Water Management" },
  { key: "pm_kisan", label: "PM-KISAN" },
  { key: "pmfby", label: "PMFBY Insurance" },
];

// YouTube search queries mapped to each topic for fetching real videos
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

interface YTVideo {
  videoId: string;
  title: string;
  channel: string;
  thumbnail: string;
  topic: string;
}

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
  { code: "mai", label: "Maithili", native: "मैथिली" },
  { code: "sa", label: "Sanskrit", native: "संस्कृतम्" },
  { code: "ne", label: "Nepali", native: "नेपाली" },
  { code: "sd", label: "Sindhi", native: "سنڌي" },
  { code: "ks", label: "Kashmiri", native: "कॉशुर" },
  { code: "doi", label: "Dogri", native: "डोगरी" },
  { code: "kok", label: "Konkani", native: "कोंकणी" },
  { code: "mni", label: "Manipuri", native: "মৈতৈলোন্" },
  { code: "sat", label: "Santali", native: "ᱥᱟᱱᱛᱟᱲᱤ" },
  { code: "ur", label: "Urdu", native: "اردو" },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function LearningPage() {
  const [activeTab, setActiveTab] = useState<"videos" | "content" | "chatbot">("videos");
  const [selectedTopic, setSelectedTopic] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [learningContent, setLearningContent] = useState<LearningContent[]>([]);
  const [loadingContent, setLoadingContent] = useState(false);

  // YouTube videos state
  const [ytVideos, setYtVideos] = useState<YTVideo[]>([]);
  const [ytLoading, setYtLoading] = useState(false);
  const [ytSearched, setYtSearched] = useState(false);

  // Chatbot state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [farmContext, setFarmContext] = useState<FarmContext | null>(null);
  const [farmContextLoading, setFarmContextLoading] = useState(false);
  const [selectedLang, setSelectedLang] = useState("en");
  const [langDropdownOpen, setLangDropdownOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const langDropdownRef = useRef<HTMLDivElement>(null);

  // Fetch farm context on mount (needed for personalized videos + chatbot)
  useEffect(() => {
    if (!farmContext && !farmContextLoading) fetchFarmContext();
  }, []);

  // Fetch YouTube videos when topic changes, tab opens, or farm context loads
  useEffect(() => {
    if (activeTab === "videos") fetchYouTubeVideos();
  }, [activeTab, selectedTopic, farmContext]);

  useEffect(() => {
    if (activeTab === "content") fetchContent();
  }, [activeTab, selectedTopic]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Close language dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (langDropdownRef.current && !langDropdownRef.current.contains(e.target as Node)) {
        setLangDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // ── Data fetching ───────────────────────────────────────────────────────

  const fetchYouTubeVideos = async () => {
    setYtLoading(true);
    setYtSearched(true);

    const topicTag = selectedTopic === "all" ? "agriculture" : selectedTopic;

    // Build personalized query from farm context + selected topic
    let query: string;
    if (searchQuery.trim()) {
      // User typed a custom search — append farming context
      query = searchQuery.trim();
      if (farmContext?.crop) query += ` ${farmContext.crop}`;
      query += " indian agriculture farming";
    } else if (selectedTopic === "all" && farmContext?.crop) {
      // No specific topic — personalize from farmer's crop & stage
      const parts = [farmContext.crop];
      if (farmContext.growth_stage) parts.push(farmContext.growth_stage, "stage");
      parts.push("farming best practices india hindi");
      query = parts.join(" ");
    } else {
      // Specific topic selected — add crop context if available
      query = TOPIC_SEARCH_QUERIES[selectedTopic] || TOPIC_SEARCH_QUERIES.all;
      if (farmContext?.crop) query += ` ${farmContext.crop}`;
    }

    try {
      // Call backend proxy (avoids CORS issues with Piped/Invidious)
      const res = await apiClient.get<{ videos: any[]; source: string }>(
        `/youtube/search?q=${encodeURIComponent(query)}&max_results=12`
      );

      const videos: YTVideo[] = (res.videos || []).map((v: any) => ({
        videoId: v.videoId || v.video_id || "",
        title: v.title || "",
        channel: v.channel || v.uploaderName || v.author || "",
        thumbnail: v.thumbnail || `https://img.youtube.com/vi/${v.videoId || v.video_id}/mqdefault.jpg`,
        topic: topicTag,
      }));

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
      toast.error("Could not load learning content");
    } finally {
      setLoadingContent(false);
    }
  };

  const fetchFarmContext = async () => {
    setFarmContextLoading(true);
    try {
      const farmerId = localStorage.getItem("farmer_id") || "F1001";
      const [profileRes, stateRes] = await Promise.allSettled([
        apiClient.get<any>(`/farm/${farmerId}`),
        apiClient.get<any>(apiClient.farmPath("/state")),
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

      // Set welcome message with farm context
      const contextMsg = ctx.crop
        ? `I can see you're growing **${ctx.crop}** (${ctx.growth_stage} stage) with a health score of **${ctx.health_score}/100**. Ask me anything about farming — I'll use your farm data to give personalized advice!`
        : "I'm your farming knowledge assistant. Ask me about pest control, organic farming, irrigation, government schemes, and more!";

      setMessages([{
        id: "welcome",
        role: "system",
        content: contextMsg,
        timestamp: new Date(),
      }]);
    } catch {
      setMessages([{
        id: "welcome",
        role: "system",
        content: "I'm your farming knowledge assistant powered by RAG. Ask me about pest control, organic farming, irrigation, schemes, and more!",
        timestamp: new Date(),
      }]);
    } finally {
      setFarmContextLoading(false);
    }
  };

  // ── Chat handler ────────────────────────────────────────────────────────

  const sendChatMessage = async (text?: string) => {
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
      // Build context-aware query that includes farm state and language instruction
      const langObj = LANGUAGES.find((l) => l.code === selectedLang);
      const langInstruction = selectedLang !== "en" ? `[IMPORTANT: Respond in ${langObj?.label || selectedLang} (${langObj?.native || ""})] ` : "";

      let enrichedQuery = langInstruction + query;
      if (farmContext?.crop) {
        enrichedQuery = `${langInstruction}[Farm context: crop=${farmContext.crop}, stage=${farmContext.growth_stage}, health=${farmContext.health_score}/100, NDVI=${farmContext.ndvi}, moisture=${farmContext.moisture}%] ${query}`;
      }

      const farmerId = localStorage.getItem("farmer_id") || "F1001";
      const res = await apiClient.post<{
        answer: string;
        sources?: string[];
        confidence?: number;
        pipeline?: string;
        grounded?: boolean;
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

      // If confidence is low, suggest content
      if (res.confidence && res.confidence < 0.7) {
        const suggestMsg: ChatMessage = {
          id: (Date.now() + 2).toString(),
          role: "system",
          content: "This answer has lower confidence. I recommend contacting your local KVK (Krishi Vigyan Kendra) at **1800-180-1551** (toll-free) for expert advice.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, suggestMsg]);
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
  };

  // ── Search handler for videos ────────────────────────────────────────────

  const handleVideoSearch = () => {
    if (activeTab === "videos") fetchYouTubeVideos();
  };

  const contentTypeIcon = (type: string) => {
    if (type === "video") return <Play size={14} />;
    if (type === "audio") return <Headphones size={14} />;
    return <FileText size={14} />;
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="p-4 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: colors.primaryLight }}>
          <BookOpen size={22} style={{ color: colors.primary }} />
        </div>
        <div>
          <h1 className="text-xl font-bold m-0" style={{ color: colors.gray[900] }}>Learning Platform</h1>
          <p className="text-sm m-0" style={{ color: colors.gray[500] }}>Learn, ask questions, and grow your farming knowledge</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 p-1 rounded-xl" style={{ backgroundColor: colors.gray[100] }}>
        {[
          { key: "videos" as const, label: "Video Library", icon: Play },
          { key: "content" as const, label: "Learning Content", icon: BookOpen },
          { key: "chatbot" as const, label: "Ask AI Expert", icon: Bot },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border-none cursor-pointer text-sm font-semibold transition-all"
              style={{
                backgroundColor: active ? "#fff" : "transparent",
                color: active ? colors.primary : colors.gray[500],
                boxShadow: active ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
              }}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Topic filter + Search (shared for videos and content tabs) */}
      {activeTab !== "chatbot" && (
        <div className="flex flex-col md:flex-row gap-3 mb-5">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: colors.gray[400] }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleVideoSearch(); }}
              placeholder={activeTab === "videos" ? "Search YouTube for farming videos..." : "Search topics..."}
              className="w-full pl-9 pr-4 py-2.5 rounded-lg border text-sm outline-none"
              style={{ borderColor: colors.gray[200] }}
            />
          </div>
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {TOPICS.map((t) => (
              <button
                key={t.key}
                onClick={() => setSelectedTopic(t.key)}
                className="whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-semibold border cursor-pointer transition-colors"
                style={{
                  backgroundColor: selectedTopic === t.key ? colors.primary : "transparent",
                  color: selectedTopic === t.key ? "#fff" : colors.gray[600],
                  borderColor: selectedTopic === t.key ? colors.primary : colors.gray[300],
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Videos Tab ──────────────────────────────────────────────────── */}
      {activeTab === "videos" && (
        <div>
          {ytLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin" style={{ color: colors.primary }} />
              <span className="ml-3 text-sm" style={{ color: colors.gray[500] }}>Searching YouTube for farming videos...</span>
            </div>
          ) : ytVideos.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {ytVideos.map((video) => (
                <Card key={video.videoId} className="overflow-hidden p-0">
                  {/* Thumbnail */}
                  <div className="relative">
                    <img
                      src={video.thumbnail || `https://img.youtube.com/vi/${video.videoId}/mqdefault.jpg`}
                      alt={video.title}
                      className="w-full h-40 object-cover bg-gray-100"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = `https://img.youtube.com/vi/${video.videoId}/mqdefault.jpg`;
                      }}
                    />
                    <div className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                      <a
                        href={`https://www.youtube.com/watch?v=${video.videoId}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="w-12 h-12 rounded-full bg-white/90 flex items-center justify-center"
                      >
                        <Play size={24} fill={colors.primary} color={colors.primary} />
                      </a>
                    </div>
                  </div>
                  <div className="p-3">
                    <p
                      className="text-sm font-semibold m-0 mb-1 line-clamp-2"
                      style={{ color: colors.gray[800] }}
                      dangerouslySetInnerHTML={{ __html: video.title }}
                    />
                    <div className="flex items-center justify-between">
                      <span className="text-xs truncate max-w-[60%]" style={{ color: colors.gray[500] }}>{video.channel}</span>
                      <span
                        className="text-[10px] px-2 py-0.5 rounded-full font-medium capitalize"
                        style={{ backgroundColor: colors.primaryLight, color: colors.primary }}
                      >
                        {video.topic.replace(/_/g, " ")}
                      </span>
                    </div>
                    <a
                      href={`https://www.youtube.com/watch?v=${video.videoId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 flex items-center gap-1.5 text-xs font-semibold no-underline"
                      style={{ color: colors.primary }}
                    >
                      Watch on YouTube <ExternalLink size={12} />
                    </a>
                  </div>
                </Card>
              ))}
            </div>
          ) : ytSearched ? (
            <div className="text-center py-16">
              <Play size={40} className="mx-auto mb-3" style={{ color: colors.gray[300] }} />
              <p className="text-sm font-semibold mb-2" style={{ color: colors.gray[600] }}>
                Could not fetch videos automatically
              </p>
              <p className="text-xs mb-4" style={{ color: colors.gray[400] }}>
                The video search service may be unavailable. Search directly on YouTube instead:
              </p>
              <a
                href={`https://www.youtube.com/results?search_query=${encodeURIComponent(
                  farmContext?.crop
                    ? `${farmContext.crop} ${farmContext.growth_stage || ""} farming india`
                    : TOPIC_SEARCH_QUERIES[selectedTopic] || "indian farming agriculture"
                )}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold no-underline text-white"
                style={{ backgroundColor: colors.primary }}
              >
                <Play size={16} /> Search on YouTube <ExternalLink size={14} />
              </a>
            </div>
          ) : null}
        </div>
      )}

      {/* ── Learning Content Tab ────────────────────────────────────────── */}
      {activeTab === "content" && (
        <div>
          {loadingContent ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin" style={{ color: colors.primary }} />
            </div>
          ) : (
            <div className="space-y-3">
              {learningContent.map((item) => (
                <Card key={item.content_id}>
                  <div className="flex items-start gap-3">
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                      style={{
                        backgroundColor:
                          item.content_type === "video" ? colors.red[50] :
                          item.content_type === "audio" ? colors.purple[50] :
                          colors.blue[50],
                        color:
                          item.content_type === "video" ? colors.red[600] :
                          item.content_type === "audio" ? colors.purple[600] :
                          colors.blue[600],
                      }}
                    >
                      {contentTypeIcon(item.content_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold m-0 mb-0.5" style={{ color: colors.gray[800] }}>{item.title}</p>
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-xs" style={{ color: colors.gray[500] }}>
                          {item.duration_minutes} min
                        </span>
                        <span
                          className="text-[10px] px-2 py-0.5 rounded-full font-medium capitalize"
                          style={{ backgroundColor: colors.primaryLight, color: colors.primary }}
                        >
                          {item.topic.replace(/_/g, " ").replace(/-/g, " ")}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium uppercase" style={{ backgroundColor: colors.gray[100], color: colors.gray[600] }}>
                          {item.content_type}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1.5 shrink-0">
                      <div className="text-right">
                        <div className="text-xs font-bold" style={{ color: colors.primary }}>
                          {Math.round(item.relevance_score * 100)}%
                        </div>
                        <div className="text-[10px]" style={{ color: colors.gray[400] }}>match</div>
                      </div>
                      {item.url && item.url !== "#" && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold no-underline transition-colors"
                          style={{ backgroundColor: colors.primaryLight, color: colors.primary }}
                        >
                          Read <ExternalLink size={10} />
                        </a>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
              {learningContent.length === 0 && (
                <div className="text-center py-12">
                  <p className="text-sm" style={{ color: colors.gray[500] }}>No content available for this topic.</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Chatbot Tab ─────────────────────────────────────────────────── */}
      {activeTab === "chatbot" && (
        <div className="flex flex-col md:flex-row gap-4">
          {/* Farm Context Sidebar */}
          <div className="md:w-64 shrink-0">
            <Card className="sticky top-4">
              <div className="flex items-center gap-2 mb-3">
                <Activity size={16} style={{ color: colors.primary }} />
                <span className="text-xs font-bold" style={{ color: colors.gray[700] }}>Your Farm Context</span>
              </div>
              {farmContextLoading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 size={16} className="animate-spin" style={{ color: colors.primary }} />
                </div>
              ) : farmContext ? (
                <div className="space-y-2.5 text-xs">
                  {farmContext.crop && (
                    <div className="flex items-center gap-2">
                      <Leaf size={13} style={{ color: colors.green[600] }} />
                      <span className="text-gray-600">{farmContext.crop}</span>
                      <span className="ml-auto px-1.5 py-0.5 rounded text-[10px] font-medium capitalize"
                        style={{ backgroundColor: colors.primaryLight, color: colors.primary }}>
                        {farmContext.growth_stage}
                      </span>
                    </div>
                  )}
                  {farmContext.health_score !== undefined && (
                    <div className="flex items-center gap-2">
                      <Activity size={13} style={{ color: farmContext.health_score >= 70 ? colors.green[600] : colors.amber[500] }} />
                      <span className="text-gray-600">Health: {farmContext.health_score}/100</span>
                    </div>
                  )}
                  {farmContext.moisture !== undefined && (
                    <div className="flex items-center gap-2">
                      <Droplets size={13} style={{ color: colors.blue[500] }} />
                      <span className="text-gray-600">Moisture: {farmContext.moisture}%</span>
                    </div>
                  )}
                  {farmContext.temperature !== undefined && (
                    <div className="flex items-center gap-2">
                      <ThermometerSun size={13} style={{ color: colors.amber[500] }} />
                      <span className="text-gray-600">{Math.round(farmContext.temperature)}°C — {farmContext.weather_condition}</span>
                    </div>
                  )}
                  <div className="pt-2 mt-2 border-t border-gray-100">
                    <div className="flex items-center gap-1">
                      <Sparkles size={11} style={{ color: colors.amber[500] }} />
                      <span className="text-[10px]" style={{ color: colors.gray[500] }}>
                        AI uses this context for personalized answers
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-gray-400">No farm data loaded</p>
              )}

              {/* Suggested topics based on farm */}
              {farmContext && (
                <div className="mt-4 pt-3 border-t border-gray-100">
                  <p className="text-[10px] font-bold uppercase tracking-wide mb-2" style={{ color: colors.gray[400] }}>
                    Suggested for you
                  </p>
                  <div className="space-y-1">
                    {farmContext.health_score !== undefined && farmContext.health_score < 70 && (
                      <button
                        onClick={() => sendChatMessage("My crop health is low, what should I do?")}
                        className="w-full text-left text-[11px] px-2 py-1.5 rounded-md border-none cursor-pointer"
                        style={{ backgroundColor: colors.red[50], color: colors.red[700] }}
                      >
                        <AlertTriangle size={10} className="inline mr-1" />
                        Low health — get advice
                      </button>
                    )}
                    {farmContext.moisture !== undefined && farmContext.moisture < 30 && (
                      <button
                        onClick={() => sendChatMessage("My soil moisture is critically low. What irrigation should I use?")}
                        className="w-full text-left text-[11px] px-2 py-1.5 rounded-md border-none cursor-pointer"
                        style={{ backgroundColor: colors.blue[50], color: colors.blue[700] }}
                      >
                        <Droplets size={10} className="inline mr-1" />
                        Low moisture — irrigation tips
                      </button>
                    )}
                    <button
                      onClick={() => sendChatMessage(`What are the best practices for ${farmContext.crop || "my crop"} in the ${farmContext.growth_stage || "current"} stage?`)}
                      className="w-full text-left text-[11px] px-2 py-1.5 rounded-md border-none cursor-pointer"
                      style={{ backgroundColor: colors.primaryLight, color: colors.primary }}
                    >
                      <Leaf size={10} className="inline mr-1" />
                      Best practices for {farmContext.crop || "crops"}
                    </button>
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Chat Area */}
          <div className="flex-1 flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden" style={{ minHeight: "500px", maxHeight: "70vh" }}>
            {/* Chat Header */}
            <div className="flex items-center gap-2.5 px-4 py-3 border-b border-gray-200" style={{ backgroundColor: colors.primaryLight }}>
              <Bot size={20} style={{ color: colors.primary }} />
              <div className="flex-1">
                <h3 className="text-sm font-bold m-0" style={{ color: colors.primary }}>KrishiMandal AI Expert</h3>
                <p className="text-[11px] m-0" style={{ color: colors.gray[500] }}>
                  RAG-powered — answers from verified agricultural knowledge
                </p>
              </div>
              {/* Language Selector */}
              <div className="relative" ref={langDropdownRef}>
                <button
                  onClick={() => setLangDropdownOpen((prev) => !prev)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium cursor-pointer transition-colors"
                  style={{
                    backgroundColor: "#fff",
                    borderColor: colors.gray[300],
                    color: colors.gray[700],
                  }}
                >
                  <Languages size={14} style={{ color: colors.primary }} />
                  <span>{LANGUAGES.find((l) => l.code === selectedLang)?.native || "English"}</span>
                  <ChevronDown size={12} style={{ color: colors.gray[400] }} />
                </button>
                {langDropdownOpen && (
                  <div
                    className="absolute right-0 top-full mt-1 w-56 max-h-72 overflow-y-auto rounded-lg border shadow-lg z-50"
                    style={{ backgroundColor: "#fff", borderColor: colors.gray[200] }}
                  >
                    {LANGUAGES.map((lang) => (
                      <button
                        key={lang.code}
                        onClick={() => {
                          setSelectedLang(lang.code);
                          setLangDropdownOpen(false);
                        }}
                        className="w-full flex items-center justify-between px-3 py-2 text-left text-sm border-none cursor-pointer transition-colors hover:bg-gray-50"
                        style={{
                          backgroundColor: selectedLang === lang.code ? colors.primaryLight : "transparent",
                          color: selectedLang === lang.code ? colors.primary : colors.gray[700],
                          fontWeight: selectedLang === lang.code ? 600 : 400,
                        }}
                      >
                        <span>{lang.native}</span>
                        <span className="text-xs" style={{ color: colors.gray[400] }}>{lang.label}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role !== "user" && (
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5"
                      style={{ backgroundColor: colors.primaryLight, color: colors.primary }}
                    >
                      <Bot size={16} />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "text-white rounded-br-sm"
                        : "bg-white text-gray-800 rounded-bl-sm shadow-sm border border-gray-100"
                    }`}
                    style={msg.role === "user" ? { backgroundColor: colors.primary } : undefined}
                  >
                    {msg.role === "user" ? (
                      <p className="m-0 whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <Markdown>{msg.content}</Markdown>
                    )}
                    {/* Sources & confidence */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <div className="flex items-center gap-1 mb-1">
                          <BookOpen size={11} style={{ color: colors.blue[600] }} />
                          <span className="text-[10px] font-bold" style={{ color: colors.blue[600] }}>Sources</span>
                        </div>
                        {msg.sources.map((src, i) => (
                          <p key={i} className="text-[10px] m-0 mb-0.5" style={{ color: colors.gray[500] }}>
                            {i + 1}. {src}
                          </p>
                        ))}
                      </div>
                    )}
                    {msg.confidence !== undefined && (
                      <div className="mt-1.5 flex items-center gap-2">
                        <span className="text-[10px]" style={{ color: colors.gray[400] }}>
                          Confidence: {Math.round(msg.confidence * 100)}%
                        </span>
                        {msg.pipeline && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ backgroundColor: colors.gray[100], color: colors.gray[500] }}>
                            {msg.pipeline}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  {msg.role === "user" && (
                    <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center shrink-0 mt-0.5">
                      <User size={16} className="text-gray-600" />
                    </div>
                  )}
                </div>
              ))}

              {chatLoading && (
                <div className="flex gap-2 items-center">
                  <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                    style={{ backgroundColor: colors.primaryLight, color: colors.primary }}>
                    <Bot size={16} />
                  </div>
                  <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm border border-gray-100">
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Loader2 size={14} className="animate-spin" style={{ color: colors.primary }} />
                      <span>Searching knowledge base...</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Suggested questions */}
              {messages.length <= 1 && !chatLoading && (
                <div className="space-y-1.5 pt-2">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide m-0">Try asking</p>
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => sendChatMessage(q)}
                      className="block w-full text-left text-sm px-3 py-2 rounded-lg bg-white border border-gray-200 text-gray-700 hover:border-[#2D5F2E] hover:bg-[#E8F5E9] cursor-pointer transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-3 bg-white border-t border-gray-200 shrink-0">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendChatMessage();
                    }
                  }}
                  placeholder="Ask about farming, schemes, pest control..."
                  disabled={chatLoading}
                  className="flex-1 px-3.5 py-2.5 rounded-full border border-gray-300 text-sm outline-none focus:border-[#2D5F2E] focus:ring-1 focus:ring-[#2D5F2E] disabled:opacity-50 disabled:bg-gray-50"
                />
                <button
                  onClick={() => sendChatMessage()}
                  disabled={!chatInput.trim() || chatLoading}
                  className="w-10 h-10 rounded-full flex items-center justify-center border-none cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{
                    backgroundColor: chatInput.trim() && !chatLoading ? colors.primary : colors.gray[200],
                    color: chatInput.trim() && !chatLoading ? "#fff" : colors.gray[400],
                  }}
                >
                  <Send size={18} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
