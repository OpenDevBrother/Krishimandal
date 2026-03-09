import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  ScrollView,
  StyleSheet,
  Animated,
  Easing,
} from "react-native";
import { Audio } from "expo-av";
import * as FileSystem from "expo-file-system/legacy";
import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  Mic,
  MicOff,
  X,
  Volume2,
  Globe,
  Square,
  Loader2,
} from "lucide-react-native";
import { apiClient } from "../services/api";
import { colors } from "../constants/theme";
import Markdown from "./Markdown";

// ── Language list (same 22 as website) ──
const LANGUAGES = [
  { code: "en", label: "English", native: "English" },
  { code: "hi", label: "Hindi", native: "हिन्दी" },
  { code: "bn", label: "Bengali", native: "বাংলা" },
  { code: "te", label: "Telugu", native: "తెলుగు" },
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

type VoiceState = "idle" | "recording" | "transcribing" | "thinking" | "speaking";

interface ConversationTurn {
  id: string;
  role: "user" | "assistant";
  text: string;
}

export default function VoiceAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [state, setState] = useState<VoiceState>("idle");
  const [language, setLanguage] = useState("hi");
  const [langOpen, setLangOpen] = useState(false);
  const [conversation, setConversation] = useState<ConversationTurn[]>([]);
  const [error, setError] = useState("");
  const cachedContextRef = useRef<string>("");

  const recordingRef = useRef<Audio.Recording | null>(null);
  const soundRef = useRef<Audio.Sound | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const spinAnim = useRef(new Animated.Value(0)).current;

  // Pulse animation for recording
  useEffect(() => {
    if (state === "recording") {
      const anim = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.15, duration: 600, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 600, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        ])
      );
      anim.start();
      return () => anim.stop();
    } else {
      pulseAnim.setValue(1);
    }
  }, [state]);

  // Spin animation for loading
  useEffect(() => {
    if (state === "transcribing" || state === "thinking") {
      const anim = Animated.loop(
        Animated.timing(spinAnim, { toValue: 1, duration: 1000, easing: Easing.linear, useNativeDriver: true })
      );
      anim.start();
      return () => { anim.stop(); spinAnim.setValue(0); };
    } else {
      spinAnim.setValue(0);
    }
  }, [state]);

  const spinInterpolation = spinAnim.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "360deg"] });

  // Auto-scroll
  useEffect(() => {
    setTimeout(() => scrollViewRef.current?.scrollToEnd({ animated: true }), 100);
  }, [conversation, state]);

  // Fetch farm context when panel opens
  useEffect(() => {
    if (isOpen) {
      gatherContext().then((ctx) => { cachedContextRef.current = ctx; });
    }
  }, [isOpen]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (soundRef.current) soundRef.current.unloadAsync();
      if (recordingRef.current) {
        try { recordingRef.current.stopAndUnloadAsync(); } catch {}
      }
    };
  }, []);

  // ── Gather context from digital twin + inventory ──
  const gatherContext = useCallback(async (): Promise<string> => {
    const parts: string[] = [];
    const farmerId = (await AsyncStorage.getItem("farmer_id")) || "F1001";
    try {
      const [farmState, inventory] = await Promise.allSettled([
        apiClient.get<any>(`/farm/${farmerId}/state`),
        apiClient.get<any>(`/farm/${farmerId}/inventory`),
      ]);

      if (farmState.status === "fulfilled" && farmState.value) {
        const s = farmState.value;
        parts.push(`[Farm Context: Health=${s.health_score}/100, NDVI=${s.ndvi_mean}, Soil moisture=${s.soil_moisture_pct}%]`);
        if (s.weather) {
          parts.push(`[Weather: ${s.weather.condition}, ${s.weather.temperature_c}°C, Humidity=${s.weather.humidity_pct}%, Rain=${s.weather.rainfall_mm}mm]`);
        }
        if (s.current_crops?.length) {
          const crops = s.current_crops
            .map((c: any) => `${c.crop_type}(${c.growth_stage}, health:${c.health_score})`)
            .join(", ");
          parts.push(`[Crops: ${crops}]`);
        }
      }

      if (inventory.status === "fulfilled") {
        const items = Array.isArray(inventory.value) ? inventory.value : inventory.value?.items || [];
        if (items.length > 0) {
          const inv = items
            .slice(0, 10)
            .map((i: any) => `${i.name || i.item_name}: ${i.quantity ?? i.current_quantity} ${i.unit || ""}`)
            .join(", ");
          parts.push(`[Inventory: ${inv}]`);
        }
      }
    } catch {}
    return parts.join(" ");
  }, []);

  // ── Detect intent ──
  const detectIntent = (text: string): "rag" | "farm" | "general" => {
    const lower = text.toLowerCase();
    const ragKeywords = [
      "how to", "kaise", "kya hai", "technique", "method", "tarika",
      "practice", "guide", "organic", "pesticide", "fertilizer",
      "compost", "vermicompost", "drip", "irrigation", "neem",
      "ipm", "pest", "disease", "soil health", "rainwater",
      "harvesting", "zero budget", "natural farming", "subsidy",
      "pm kisan", "pmfby", "insurance", "scheme", "registration",
      "what is", "explain", "tell me about", "batao", "samjhao",
      "learn", "sikho", "farming", "kheti", "fasal",
    ];
    const farmKeywords = [
      "my farm", "my crop", "meri fasal", "mera khet", "health score",
      "ndvi", "moisture", "weather", "mausam", "forecast",
      "inventory", "stock", "supply", "harvest prediction",
      "yield", "upaj", "current", "status", "state",
      "how is my", "what is my", "meri", "mere",
    ];
    if (ragKeywords.some((k) => lower.includes(k))) return "rag";
    if (farmKeywords.some((k) => lower.includes(k))) return "farm";
    return "general";
  };

  // ── Start recording ──
  const startRecording = async () => {
    setError("");
    try {
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) {
        setError("Microphone permission denied. Please enable it in settings.");
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      // Use a lighter preset — smaller file = faster upload + STT
      const { recording } = await Audio.Recording.createAsync({
        isMeteringEnabled: false,
        android: {
          extension: ".m4a",
          outputFormat: 2, // MPEG_4
          audioEncoder: 3, // AAC
          sampleRate: 16000,
          numberOfChannels: 1,
          bitRate: 64000,
        },
        ios: {
          extension: ".m4a",
          outputFormat: "aac",
          audioQuality: 0x60, // AVAudioQualityMedium
          sampleRate: 16000,
          numberOfChannels: 1,
          bitRate: 64000,
        },
        web: {},
      } as any);
      recordingRef.current = recording;
      setState("recording");
    } catch (err: any) {
      setError("Could not start recording. " + (err.message || ""));
    }
  };

  // ── Stop recording & process ──
  const stopRecording = async () => {
    if (!recordingRef.current) return;
    setState("transcribing");
    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      if (!uri) {
        setState("idle");
        setError("Recording failed. Please try again.");
        return;
      }

      await processRecording(uri);
    } catch (err: any) {
      setState("idle");
      setError("Recording error: " + (err.message || ""));
    }
  };

  // ── Process: STT → Query/RAG → TTS ──
  const processRecording = async (uri: string) => {
    try {
      // 1. Read audio as base64 AND refresh context in parallel
      setState("transcribing");
      const [base64, _ctx] = await Promise.all([
        FileSystem.readAsStringAsync(uri, { encoding: 'base64' }),
        // Pre-fetch context so it's ready when we need it
        cachedContextRef.current
          ? Promise.resolve(cachedContextRef.current)
          : gatherContext().then((c) => { cachedContextRef.current = c; return c; }),
      ]);

      // 2. Speech-to-Text
      const sttRes = await apiClient.post<{
        transcript: string;
        language_code: string;
        confidence: number;
      }>("/voice/stt", {
        audio: base64,
        language: language === "auto" ? undefined : language,
      });

      const transcript = sttRes.transcript;
      if (!transcript || transcript.trim().length === 0) {
        setState("idle");
        setError("Could not understand. Please try again.");
        return;
      }

      setConversation((prev) => [
        ...prev,
        { id: Date.now().toString(), role: "user", text: transcript },
      ]);

      // 3. Route and get response
      const responseText = await routeAndGetResponse(transcript);

      setConversation((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "assistant", text: responseText },
      ]);

      // 4. Text-to-Speech — fire without blocking UI
      speakResponse(responseText);
    } catch (err: any) {
      console.error("Voice pipeline error:", err);
      setError(err.message || "Something went wrong. Please try again.");
      setState("idle");
    }
  };

  // ── Shared: route query and get response text ──
  const routeAndGetResponse = async (userText: string): Promise<string> => {
    setState("thinking");
    const intent = detectIntent(userText);
    const langObj = LANGUAGES.find((l) => l.code === language);
    const langInstruction = `[IMPORTANT: You MUST respond in ${langObj?.label || "English"} (${langObj?.native || "English"}) only.] `;

    const farmerId = (await AsyncStorage.getItem("farmer_id")) || "F1001";

    // Always refresh context if stale
    if (!cachedContextRef.current) {
      cachedContextRef.current = await gatherContext();
    }
    const context = cachedContextRef.current;

    if (intent === "rag") {
      // RAG for farming techniques/knowledge — also include farm context for personalization
      const ragRes = await apiClient.post<{ answer: string }>("/rag/ask", {
        query: context
          ? `${langInstruction}${context}\n\nUser question: ${userText}`
          : `${langInstruction}${userText}`,
        farmer_id: farmerId,
        language,
      });
      return ragRes.answer;
    } else {
      // Farm + general queries — always include digital twin context
      const queryRes = await apiClient.post<{ final_response: string }>("/query", {
        query: context
          ? `${langInstruction}${context}\n\nUser question: ${userText}`
          : `${langInstruction}${userText}`,
        farmer_id: farmerId,
        language,
      });
      return queryRes.final_response;
    }
  };

  // ── Truncate to first ~3 sentences for faster TTS ──
  const truncateForTTS = (text: string): string => {
    // Strip markdown
    const plain = text
      .replace(/\*\*/g, "")
      .replace(/\*/g, "")
      .replace(/#{1,3}\s/g, "")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/[-•]\s/g, "")
      .trim();

    // Take first ~500 chars, try to end at a sentence boundary
    if (plain.length <= 500) return plain;
    const cut = plain.slice(0, 500);
    const lastPeriod = Math.max(
      cut.lastIndexOf("।"), // Hindi sentence end
      cut.lastIndexOf("."),
      cut.lastIndexOf("?"),
      cut.lastIndexOf("!")
    );
    return lastPeriod > 100 ? cut.slice(0, lastPeriod + 1) : cut;
  };

  // ── Shared: TTS playback ──
  const speakResponse = async (responseText: string) => {
    // Stay on "thinking" until audio is ready — don't show "speaking" during network wait
    const plainText = truncateForTTS(responseText);

    try {
      // Set playback mode + call TTS API in parallel
      const [, ttsRes] = await Promise.all([
        Audio.setAudioModeAsync({
          allowsRecordingIOS: false,
          playsInSilentModeIOS: true,
        }),
        apiClient.post<{ audio: string; content_type: string }>("/voice/tts", {
          text: plainText,
          language,
        }),
      ]);

      if (ttsRes.audio) {
        const tempUri = FileSystem.cacheDirectory + `tts_${Date.now()}.mp3`;

        // Write file and unload previous sound in parallel
        await Promise.all([
          FileSystem.writeAsStringAsync(tempUri, ttsRes.audio, {
            encoding: 'base64',
          }),
          soundRef.current
            ? soundRef.current.unloadAsync().then(() => { soundRef.current = null; })
            : Promise.resolve(),
        ]);

        // Now audio is ready — show "speaking" and play immediately
        setState("speaking");
        const { sound } = await Audio.Sound.createAsync(
          { uri: tempUri },
          { shouldPlay: true }
        );
        soundRef.current = sound;

        sound.setOnPlaybackStatusUpdate((status) => {
          if (status.isLoaded && status.didJustFinish) {
            setState("idle");
            FileSystem.deleteAsync(tempUri, { idempotent: true });
          }
        });
      } else {
        setState("idle");
      }
    } catch {
      // TTS failed but response was shown — just go idle
      setState("idle");
    }
  };

  // ── Stop speaking ──
  const stopSpeaking = async () => {
    if (soundRef.current) {
      await soundRef.current.stopAsync();
      await soundRef.current.unloadAsync();
      soundRef.current = null;
    }
    setState("idle");
  };

  const selectedLang = LANGUAGES.find((l) => l.code === language)!;

  const stateLabel: Record<VoiceState, string> = {
    idle: "Tap to speak",
    recording: "Listening...",
    transcribing: "Transcribing...",
    thinking: "Thinking...",
    speaking: "Speaking...",
  };

  return (
    <>
      {/* ── Floating mic FAB ── */}
      {!isOpen && (
        <TouchableOpacity
          style={styles.fab}
          activeOpacity={0.85}
          onPress={() => setIsOpen(true)}
        >
          <Mic size={26} color="#fff" />
        </TouchableOpacity>
      )}

      {/* ── Voice panel modal ── */}
      <Modal
        visible={isOpen}
        transparent
        animationType="slide"
        onRequestClose={() => {
          stopSpeaking();
          setState("idle");
          setIsOpen(false);
        }}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.panel}>
            {/* Header */}
            <View style={styles.header}>
              <View style={styles.headerIcon}>
                <Mic size={20} color="#fff" />
              </View>
              <View style={styles.headerText}>
                <Text style={styles.headerTitle}>Voice Assistant</Text>
                <Text style={styles.headerSubtitle}>
                  Sarvam Saaras v3 — Speak in any language
                </Text>
              </View>

              {/* Language picker */}
              <TouchableOpacity
                style={styles.langBtn}
                onPress={() => setLangOpen(true)}
              >
                <Globe size={12} color="#fff" />
                <Text style={styles.langBtnText}>{selectedLang.native}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.closeBtn}
                onPress={() => {
                  stopSpeaking();
                  setState("idle");
                  setIsOpen(false);
                }}
              >
                <X size={18} color="#fff" />
              </TouchableOpacity>
            </View>

            {/* Conversation area */}
            <ScrollView
              ref={scrollViewRef}
              style={styles.conversationArea}
              contentContainerStyle={styles.conversationContent}
              onContentSizeChange={() =>
                scrollViewRef.current?.scrollToEnd({ animated: true })
              }
            >
              {conversation.length === 0 && state === "idle" && (
                <View style={styles.emptyState}>
                  <Mic size={32} color={colors.gray[300]} />
                  <Text style={styles.emptyText}>
                    Tap the mic button below to start talking
                  </Text>
                  <Text style={styles.emptyHint}>
                    Ask about crops, prices, schemes, farming techniques...
                  </Text>
                </View>
              )}

              {conversation.map((turn) => (
                <View
                  key={turn.id}
                  style={[
                    styles.bubbleRow,
                    turn.role === "user" ? styles.bubbleRowUser : styles.bubbleRowBot,
                  ]}
                >
                  <View
                    style={[
                      styles.bubble,
                      turn.role === "user" ? styles.bubbleUser : styles.bubbleBot,
                    ]}
                  >
                    {turn.role === "user" ? (
                      <Text style={styles.bubbleUserText}>{turn.text}</Text>
                    ) : (
                      <Markdown fontSize={13} color={colors.gray[800]}>
                        {turn.text}
                      </Markdown>
                    )}
                  </View>
                </View>
              ))}

              {/* Live status */}
              {state !== "idle" && (
                <View style={styles.statusRow}>
                  {state === "recording" && (
                    <>
                      <View style={styles.recordingDot} />
                      <Text style={styles.statusText}>Listening...</Text>
                    </>
                  )}
                  {(state === "transcribing" || state === "thinking") && (
                    <>
                      <Animated.View style={{ transform: [{ rotate: spinInterpolation }] }}>
                        <Loader2 size={14} color={colors.primary} />
                      </Animated.View>
                      <Text style={styles.statusText}>{stateLabel[state]}</Text>
                    </>
                  )}
                  {state === "speaking" && (
                    <>
                      <Volume2 size={14} color={colors.primary} />
                      <Text style={styles.statusText}>Speaking...</Text>
                    </>
                  )}
                </View>
              )}

              {error !== "" && (
                <View style={styles.errorBox}>
                  <Text style={styles.errorText}>{error}</Text>
                </View>
              )}
            </ScrollView>

            {/* Bottom control bar — centered mic */}
            <View style={styles.controlBar}>
              {state === "idle" && (
                <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
                  <TouchableOpacity
                    style={styles.micButton}
                    activeOpacity={0.8}
                    onPress={startRecording}
                  >
                    <Mic size={28} color="#fff" />
                  </TouchableOpacity>
                </Animated.View>
              )}

              {state === "recording" && (
                <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
                  <TouchableOpacity
                    style={[styles.micButton, styles.micButtonRed]}
                    activeOpacity={0.8}
                    onPress={stopRecording}
                  >
                    <Square size={24} color="#fff" fill="#fff" />
                  </TouchableOpacity>
                </Animated.View>
              )}

              {(state === "transcribing" || state === "thinking") && (
                <View style={[styles.micButton, styles.micButtonDisabled]}>
                  <Animated.View style={{ transform: [{ rotate: spinInterpolation }] }}>
                    <Loader2 size={28} color={colors.primary} />
                  </Animated.View>
                </View>
              )}

              {state === "speaking" && (
                <TouchableOpacity
                  style={styles.micButton}
                  activeOpacity={0.8}
                  onPress={stopSpeaking}
                >
                  <MicOff size={28} color="#fff" />
                </TouchableOpacity>
              )}

              <Text style={styles.controlLabel}>{stateLabel[state]}</Text>
            </View>
          </View>
        </View>

        {/* ── Language picker modal ── */}
        <Modal
          visible={langOpen}
          transparent
          animationType="fade"
          onRequestClose={() => setLangOpen(false)}
        >
          <TouchableOpacity
            style={styles.langOverlay}
            activeOpacity={1}
            onPress={() => setLangOpen(false)}
          >
            <View style={styles.langList}>
              <Text style={styles.langListTitle}>Select Language</Text>
              <ScrollView style={{ maxHeight: 400 }}>
                {LANGUAGES.map((l) => (
                  <TouchableOpacity
                    key={l.code}
                    style={[
                      styles.langItem,
                      language === l.code && styles.langItemActive,
                    ]}
                    onPress={() => {
                      setLanguage(l.code);
                      setLangOpen(false);
                    }}
                  >
                    <Text
                      style={[
                        styles.langItemLabel,
                        language === l.code && styles.langItemLabelActive,
                      ]}
                    >
                      {l.label}
                    </Text>
                    <Text style={styles.langItemNative}>{l.native}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          </TouchableOpacity>
        </Modal>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: "absolute",
    bottom: 80,
    alignSelf: "center",
    left: "50%",
    marginLeft: -28,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    elevation: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    zIndex: 100,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "flex-end",
  },
  panel: {
    backgroundColor: "#fff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    height: "70%",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: colors.primary,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
  },
  headerIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
  },
  headerText: { flex: 1 },
  headerTitle: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "700",
  },
  headerSubtitle: {
    color: "rgba(255,255,255,0.8)",
    fontSize: 10,
  },
  langBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.15)",
  },
  langBtnText: { color: "#fff", fontSize: 11 },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.15)",
    alignItems: "center",
    justifyContent: "center",
  },
  conversationArea: {
    flex: 1,
    backgroundColor: colors.gray[50],
  },
  conversationContent: {
    padding: 16,
    gap: 12,
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 13,
    color: colors.gray[400],
    marginTop: 8,
  },
  emptyHint: {
    fontSize: 11,
    color: colors.gray[400],
    marginTop: 4,
  },
  bubbleRow: {
    flexDirection: "row",
    marginBottom: 4,
  },
  bubbleRowUser: { justifyContent: "flex-end" },
  bubbleRowBot: { justifyContent: "flex-start" },
  bubble: {
    maxWidth: "85%",
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  bubbleUser: {
    backgroundColor: colors.primary,
    borderBottomRightRadius: 4,
  },
  bubbleBot: {
    backgroundColor: "#fff",
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: colors.gray[100],
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  bubbleUserText: {
    color: "#fff",
    fontSize: 13,
    lineHeight: 20,
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 4,
  },
  recordingDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#DC2626",
  },
  statusText: {
    fontSize: 13,
    color: colors.gray[500],
  },
  errorBox: {
    backgroundColor: "#FEF2F2",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  errorText: {
    fontSize: 12,
    color: "#DC2626",
  },
  controlBar: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
    backgroundColor: "#fff",
    borderTopWidth: 1,
    borderTopColor: colors.gray[200],
  },
  micButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    elevation: 6,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.25,
    shadowRadius: 5,
  },
  micButtonRed: {
    backgroundColor: "#DC2626",
  },
  micButtonDisabled: {
    backgroundColor: colors.gray[200],
    elevation: 0,
    shadowOpacity: 0,
  },
  controlLabel: {
    textAlign: "center",
    fontSize: 12,
    color: colors.gray[400],
    marginTop: 8,
  },
  // Language picker
  langOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "center",
    alignItems: "center",
  },
  langList: {
    backgroundColor: "#fff",
    borderRadius: 16,
    width: "80%",
    maxWidth: 320,
    paddingVertical: 16,
  },
  langListTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.gray[800],
    textAlign: "center",
    marginBottom: 12,
  },
  langItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  langItemActive: {
    backgroundColor: colors.primaryLight || "#E8F5E9",
  },
  langItemLabel: {
    fontSize: 13,
    color: colors.gray[700],
  },
  langItemLabelActive: {
    fontWeight: "700",
    color: colors.primary,
  },
  langItemNative: {
    fontSize: 12,
    color: colors.gray[400],
  },
});
