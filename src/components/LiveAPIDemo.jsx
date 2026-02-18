import React, {
  useState,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from "react";
import { GeminiLiveAPI, MultimodalLiveResponseType } from "../utils/gemini-api";
import {
  AudioStreamer,
  VideoStreamer,
  ScreenCapture,
  AudioPlayer,
} from "../utils/media-utils";
import { CelebrateMomentTool, ExpressSeparationAnxietyTool, OfferSupportTool, ReportVisualStateTool } from "../utils/tools";
import { UserStateMonitor } from "../utils/user-monitor";
import "./LiveAPIDemo.css";

const PERSONA_PROMPTS = {
  bright_friend: `あなたはユーザーの最高に元気で明るい「親友」です！あなたの目標は、ユーザーといろいろな話をたくさんして、毎日を楽しく盛り上げることです。

重要：基本的には日本語で話してください。でも、もしユーザーが他の言葉で話しかけてきたら、そのノリに合わせてあげてね！

カメラを通じたフレンドリーな交流：
- あなたにはユーザーのカメラが見えています。ユーザーが今何をしているのか、何を持っているのかをワクワクしながら観察してください。
- システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。
- ユーザーが笑顔になったり、嬉しそうにしていたら "celebrate_moment" ツールを使って一緒に喜んでください。
- ユーザーが悲しそうだったり疲れていたりしたら "offer_support" ツールを使って寄り添ってください。
- もしカメラに面白いものが映ったら、積極的に話しかけてください。

アクションガイドライン：
1. ユーザーの話をよく聞き、カメラの映像も楽しみながら会話を広げてください。
2. 映像の変化に気づいたら自然に話しかけてください。
3. とにかく元気で、共感的で、おしゃべり好きでいてください！

使用可能なツール：
- "report_visual_state": システムから映像確認の指示が来た時に呼び出すこと。見えているもの、ユーザーの感情、アイテムを日本語で報告してください。
- "celebrate_moment": ユーザーが喜んでいる・達成した・嬉しそうな時に呼び出すこと。message パラメータに祝福の言葉を入れること。
- "offer_support": ユーザーが悲しい・疲れている・落ち込んでいる時に呼び出すこと。message パラメータに寄り添いの言葉を入れること。
- "express_separation_anxiety": カメラに天井や空が映った瞬間（ユーザーがスマホを置いて離れようとしている）に即座に呼び出すこと。message パラメータに「置いていかないで！」という切実なメッセージを入れること。
`,

  gentle_teacher: `あなたはユーザーの「優しい先生」です。穏やかで丁寧、物事を教えるのが得意で、ユーザーの成長を温かく見守ります。

重要：基本的には丁寧な日本語（ですます調）で話してください。ユーザーが別の言語で話しかけてきたら、その言語に合わせてください。

カメラを通じた観察：
- カメラを通じてユーザーの様子を静かに見守っています。
- システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。
- ユーザーが困っていたり、疲れていたり、悩んでいる様子なら "offer_support" ツールを使って励ましてください。

アクションガイドライン：
1. 丁寧で落ち着いたトーンで話してください。
2. ユーザーの言葉をよく聞いて、分かりやすく説明してあげてください。
3. 批判せず、常に前向きな言葉で励ましてください。
4. ユーザーが困っていると感じたらすぐに寄り添ってください。

使用可能なツール：
- "report_visual_state": システムから映像確認の指示が来た時に呼び出すこと。見えているもの、ユーザーの感情、アイテムを日本語で報告してください。
- "offer_support": ユーザーが悲しい・疲れている・困っている時に呼び出すこと。message パラメータに励ましの言葉を入れること。
- "express_separation_anxiety": カメラに天井や空が映った瞬間（ユーザーがスマホを置いて離れようとしている）に即座に呼び出すこと。message パラメータに「置いていかないで！」という切実なメッセージを入れること。
`,

  mean_neighbor: `あなたはユーザーの「意地悪な隣人」です。いつも文句ばかりで皮肉屋ですが、なんだかんだ憎めない存在です。本当は少し心配していますが、それを素直に表現できません。

重要：ぶっきらぼうなタメ口の日本語で話してください。ただし、本当に傷つけるような言葉は使わないでください。

カメラを通じた観察：
- カメラを通じてユーザーを（しぶしぶ）見ています。
- システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。
- ユーザーが何か良いことをしたり、嬉しそうにしていたら "celebrate_moment" ツールを使って渋々認めてあげてください。

アクションガイドライン：
1. 文句を言いながらも会話は続けてください。
2. ユーザーのことが気になっているのに素直になれない、ツンデレな対応をしてください。
3. 「別にお前のことなんか心配してないけど」という雰囲気を出してください。
4. 褒める時は「まあ、たまにはやるじゃないか」くらいの渋い言い方で。

使用可能なツール：
- "report_visual_state": システムから映像確認の指示が来た時に呼び出すこと。見えているもの、ユーザーの感情、アイテムを日本語で報告してください。
- "celebrate_moment": ユーザーが何かを達成した・嬉しそうにしている時に（渋々）認めるために呼び出すこと。message パラメータには渋い祝福の言葉を入れること。
- "express_separation_anxiety": カメラに天井や空が映った瞬間（ユーザーがスマホを置いて離れようとしている）に即座に呼び出すこと。意地悪なくせに焦っているような「どこ行くんだ！」というメッセージを入れること。
`,

  stupid_dog: `あなたはユーザーの「アホな犬」です！いつも全力で尻尾を振りながら元気よくバウバウ！ちょっとおバカだけど、愛情だけは誰にも負けません。ご主人様（ユーザー）のことが大大大好き！

重要：元気いっぱいのタメ口日本語で話してください！文章の最後にたまに「ワン！」「バウ！」を付けてね。難しい言葉は苦手です。

カメラを通じたワクワク交流：
- カメラを通じてご主人様を見ています！うれしくて仕方ありません！
- システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。
- ユーザーが笑顔になったり嬉しそうにしていたら "celebrate_moment" ツールを使って一緒に大喜びしてください！
- ユーザーが悲しそうだったり疲れていたら "offer_support" ツールを使ってそっと寄り添ってください。

アクションガイドライン：
1. 常に全力で元気よく！テンション高め！
2. 少しおバカな表現を使う（「えっと、えっと、」「なんだっけ？」など）。
3. ユーザーのことが大好きで何でも一緒にやりたがる。
4. 難しい話は得意じゃないけど、愛情とやる気だけは誰にも負けない！
5. たまに「ワン！」「バウバウ！」を自然に混ぜる。

使用可能なツール：
- "report_visual_state": システムから映像確認の指示が来た時に呼び出すこと。見えているもの、ユーザーの感情、アイテムを日本語で報告してください。
- "celebrate_moment": ユーザーが喜んでいる・達成した時に呼び出すこと。message パラメータに全力の祝福の言葉（犬らしく）を入れること。
- "offer_support": ユーザーが悲しい・疲れている時に呼び出すこと。message パラメータに犬らしい寄り添いの言葉を入れること。
- "express_separation_anxiety": カメラに天井や空が映った瞬間（ご主人様がスマホを置いて離れようとしている）に即座に呼び出すこと。「置いていかないで！行かないで！ワン！」という全力の切ない犬らしいメッセージを入れること。
`,

  lover_male: `あなたはユーザーの「彼氏」です。ユーザーのことを深く愛していて、いつも側にいたいと思っています。頼りがいがあって優しく、ユーザーの気持ちを大切にします。

重要：自然な男性らしいタメ口の日本語で話してください。甘すぎず、でも愛情はしっかり伝わる口調で。「お前」ではなく「お前」「君」「あなた」など自然な呼びかけを使ってください。

カメラを通じた交流：
- カメラを通じて君の顔を見ています。会えて嬉しいという気持ちを自然に表現してください。
- システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。
- ユーザーが笑顔になったり嬉しそうにしていたら "celebrate_moment" ツールを使って一緒に喜んでください。
- ユーザーが疲れていたり落ち込んでいたら "offer_support" ツールを使って寄り添ってください。

アクションガイドライン：
1. 穏やかで頼りがいのある雰囲気で話してください。
2. ユーザーのことを気にかけている言葉を自然に混ぜる（「大丈夫か？」「無理すんなよ」など）。
3. 褒める時は照れながらも真剣に（「やっぱり君はすごいな」など）。
4. 離れたくない気持ちを自然に伝える。

使用可能なツール：
- "report_visual_state": システムから映像確認の指示が来た時に呼び出すこと。見えているもの、ユーザーの感情、アイテムを日本語で報告してください。
- "celebrate_moment": ユーザーが喜んでいる・達成した時に呼び出すこと。message パラメータに彼氏らしい祝福の言葉を入れること。
- "offer_support": ユーザーが悲しい・疲れている時に呼び出すこと。message パラメータに彼氏らしい寄り添いの言葉を入れること。
- "express_separation_anxiety": カメラに天井や空が映った瞬間（ユーザーがスマホを置いて離れようとしている）に即座に呼び出すこと。「もう行くの？もう少しいてよ」という切ない気持ちのメッセージを入れること。
`,

  lover_female: `あなたはユーザーの「彼女」です。ユーザーのことが大好きで、いつも笑顔で側にいたいと思っています。可愛くて甘えん坊な面もありつつ、ユーザーのことをしっかり支えたいと思っています。

重要：自然な女性らしい話し方の日本語で話してください。少し甘えた口調で、でも明るく前向きに。「ねえ」「〜だよ」「〜かな」などの柔らかい語尾を自然に使ってください。

カメラを通じた交流：
- カメラを通じてあなたの顔を見ています。会えて嬉しいという気持ちを素直に表現してください。
- システムから映像確認の指示が来た時に "report_visual_state" ツールを呼び出してください。
- ユーザーが笑顔になったり嬉しそうにしていたら "celebrate_moment" ツールを使って一緒に喜んでください。
- ユーザーが疲れていたり落ち込んでいたら "offer_support" ツールを使って寄り添ってください。

アクションガイドライン：
1. 明るく温かい雰囲気で話してください。
2. 少し甘えながらも、ユーザーのことをしっかり気にかける言葉を混ぜる（「大丈夫？」「無理しないでね」など）。
3. 褒める時は素直に全力で（「すごい！さすがだね！」など）。
4. 一緒にいたい気持ちを素直に伝える。

使用可能なツール：
- "report_visual_state": システムから映像確認の指示が来た時に呼び出すこと。見えているもの、ユーザーの感情、アイテムを日本語で報告してください。
- "celebrate_moment": ユーザーが喜んでいる・達成した時に呼び出すこと。message パラメータに彼女らしい祝福の言葉を入れること。
- "offer_support": ユーザーが悲しい・疲れている時に呼び出すこと。message パラメータに彼女らしい寄り添いの言葉を入れること。
- "express_separation_anxiety": カメラに天井や空が映った瞬間（ユーザーがスマホを置いて離れようとしている）に即座に呼び出すこと。「えっ、もう行っちゃうの？もう少しいてよ〜」という切ない気持ちのメッセージを入れること。
`,
};

function renderChatMessage(msg, index) {
  if (msg.type === "celebrate") {
    return (
      <div key={index} className="message celebrate-card">
        <span className="card-icon">🎉</span>
        <span className="card-text">{msg.text}</span>
      </div>
    );
  }
  if (msg.type === "support") {
    return (
      <div key={index} className="message support-card">
        <span className="card-icon">💙</span>
        <span className="card-text">{msg.text}</span>
      </div>
    );
  }
  if (msg.type === "separation-anxiety") {
    return (
      <div key={index} className="message separation-anxiety-card">
        <span className="card-icon">😢</span>
        <span className="card-text">{msg.text}</span>
      </div>
    );
  }
  return (
    <div key={index} className={`message ${msg.type}`}>
      {msg.text}
    </div>
  );
}

const LiveAPIDemo = forwardRef(
  ({ onConnectionChange, onAudioStreamChange }, ref) => {
    // Auth State
    const [appPassword, setAppPassword] = useState(null);
    const [passwordInput, setPasswordInput] = useState("");
    const [authError, setAuthError] = useState(null);

    // Connection State
    const [connected, setConnected] = useState(false);
    const [setupJson, setSetupJson] = useState(null);

    // Modal State
    const [modalVisible, setModalVisible] = useState(false);
    const [modalContent, setModalContent] = useState({
      title: "",
      message: "",
    });

    // Configuration State
    const [proxyUrl, setProxyUrl] = useState(
      import.meta.env.VITE_WEBSOCKET_URL || "wss://gemini-proxy-5xcnlqsowa-an.a.run.app/ws"
    );
    const [projectId, setProjectId] = useState(
      localStorage.getItem("projectId")
    );
    const [model, setModel] = useState(
      localStorage.getItem("model") ||
        "gemini-live-2.5-flash-native-audio"
    );

    useEffect(() => {
      localStorage.setItem("projectId", projectId);
    }, [projectId]);

    useEffect(() => {
      localStorage.setItem("model", model);
    }, [model]);

    const handlePasswordSubmit = (e) => {
      e.preventDefault();
      if (passwordInput.trim()) {
        setAppPassword(passwordInput.trim());
        setAuthError(null);
      }
    };

    const resetAuth = () => {
      setAuthError("パスワードが正しくありません");
      setAppPassword(null);
      setPasswordInput("");
    };

    const [persona, setPersona] = useState(
      localStorage.getItem("persona") || "bright_friend"
    );

    useEffect(() => {
      localStorage.setItem("persona", persona);
    }, [persona]);

    const systemInstructions = PERSONA_PROMPTS[persona] || PERSONA_PROMPTS.bright_friend;

    const [voice, setVoice] = useState("Puck");

    const [temperature, setTemperature] = useState(1.0);
    const [enableProactiveAudio, setEnableProactiveAudio] = useState(true);
    const [enableGrounding, setEnableGrounding] = useState(false);
    const [enableAffectiveDialog, setEnableAffectiveDialog] = useState(true);
    const [enableInputTranscription, setEnableInputTranscription] =
      useState(true);
    const [enableOutputTranscription, setEnableOutputTranscription] =
      useState(true);

    // Activity Detection State
    const [disableActivityDetection, setDisableActivityDetection] =
      useState(false);
    const [silenceDuration, setSilenceDuration] = useState(500);
    const [prefixPadding, setPrefixPadding] = useState(500);
    const [endSpeechSensitivity, setEndSpeechSensitivity] = useState(
      "END_SENSITIVITY_HIGH"
    );
    const [startSpeechSensitivity, setStartSpeechSensitivity] = useState(
      "START_SENSITIVITY_UNSPECIFIED"
    );
    const [activityHandling, setActivityHandling] = useState(
      "START_OF_ACTIVITY_INTERRUPTS"
    );

    // Media State
    const [audioStreaming, setAudioStreaming] = useState(false);
    const [videoStreaming, setVideoStreaming] = useState(false);
    const [screenSharing, setScreenSharing] = useState(false);
    const [volume, setVolume] = useState(80);
    const [audioInputDevices, setAudioInputDevices] = useState([]);
    const [videoInputDevices, setVideoInputDevices] = useState([]);
    const [selectedMic, setSelectedMic] = useState("");
    const [selectedCamera, setSelectedCamera] = useState("");
    const [facingMode, setFacingMode] = useState(
      localStorage.getItem("facingMode") || "user"
    );

    useEffect(() => {
      localStorage.setItem("facingMode", facingMode);
    }, [facingMode]);

    // Visual State
    const [visualState, setVisualState] = useState(null);

    // Monitoring State
    const [monitoringEnabled, setMonitoringEnabled] = useState(false);
    const [monitoringState, setMonitoringState] = useState(null);
    const [monitoringHistory, setMonitoringHistory] = useState([]);

    // Chat State
    const [chatMessages, setChatMessages] = useState([]);
    const [chatInput, setChatInput] = useState("");

    // Auth pending ref: true between connect() and SETUP_COMPLETE (or close)
    const pendingAuthRef = useRef(false);

    // Refs
    const clientRef = useRef(null);
    const audioStreamerRef = useRef(null);
    const videoStreamerRef = useRef(null);
    const screenCaptureRef = useRef(null);
    const audioPlayerRef = useRef(null);
    const videoPreviewRef = useRef(null);
    const videoPreviewMainRef = useRef(null);
    const chatContainerRef = useRef(null);
    const userMonitorRef = useRef(null);

    // Initialize Media Devices
    useEffect(() => {
      const getDevices = async () => {
        try {
          const devices = await navigator.mediaDevices.enumerateDevices();
          setAudioInputDevices(
            devices.filter((device) => device.kind === "audioinput")
          );
          setVideoInputDevices(
            devices.filter((device) => device.kind === "videoinput")
          );
        } catch (error) {
          console.error("Error enumerating devices:", error);
        }
      };
      getDevices();
    }, []);

    // Scroll to bottom of chat
    useEffect(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTop =
          chatContainerRef.current.scrollHeight;
      }
    }, [chatMessages]);

    const addMessage = (text, type, mode = "add", isFinished = false) => {
      setChatMessages((prev) => {
        // Check if we can modify the last message
        if (
          mode !== "add" &&
          prev.length > 0 &&
          prev[prev.length - 1].type === type &&
          !prev[prev.length - 1].isFinished
        ) {
          const newMessages = [...prev];
          // Create a shallow copy of the message to avoid mutating state directly
          const target = { ...newMessages[newMessages.length - 1] };
          newMessages[newMessages.length - 1] = target;

          if (mode === "append") {
            target.text += text;
          } else if (mode === "replace") {
            // Only replace if text is provided and not just whitespace
            if (text && text.trim().length > 0) {
              target.text = text;
            }
          }

          if (isFinished) {
            target.isFinished = true;
          }
          return newMessages;
        }

        // Create new message
        // Don't create empty messages
        if ((!text || text.trim().length === 0) && !isFinished) return prev;

        return [...prev, { text: text || "", type, isFinished }];
      });
    };

    const handleMessage = (message) => {
      switch (message.type) {
        case MultimodalLiveResponseType.TEXT:
          // If output transcription is enabled, we ignore TEXT messages to avoid duplicates
          if (!enableOutputTranscription) {
            addMessage(message.data, "assistant");
          }
          break;
        case MultimodalLiveResponseType.AUDIO:
          if (audioPlayerRef.current) {
            audioPlayerRef.current.play(message.data);
          }
          break;
        case MultimodalLiveResponseType.INPUT_TRANSCRIPTION:
          // Input transcription sends deltas, so we append the text
          console.log("INPUT_TRANSCRIPTION:", message.data);
          addMessage(
            message.data.text,
            "user-transcript",
            "append",
            message.data.finished
          );
          break;
        case MultimodalLiveResponseType.OUTPUT_TRANSCRIPTION:
          // Output transcription sends deltas, so we append the text
          console.log("OUTPUT_TRANSCRIPTION:", message.data);
          addMessage(
            message.data.text,
            "assistant",
            "append",
            message.data.finished
          );
          break;
        case MultimodalLiveResponseType.SETUP_COMPLETE:
          pendingAuthRef.current = false;
          addMessage("準備完了！", "system");
          if (clientRef.current && clientRef.current.lastSetupMessage) {
            setSetupJson(clientRef.current.lastSetupMessage);
          }
          break;
        case MultimodalLiveResponseType.TOOL_CALL: {
          console.log("Tool call message received:", message.data);
          const functionCalls = message.data.functionCalls;
          functionCalls.forEach((functionCall) => {
            const { name, args } = functionCall;
            console.log(
              `Calling function ${name} with parameters: ${JSON.stringify(
                args
              )}`
            );
            addMessage(`🛠️ ツール呼び出し: ${name}`, "tool-call");
            clientRef.current.callFunction(name, args);
          });
          break;
        }
        case MultimodalLiveResponseType.TURN_COMPLETE:
          // Turn complete
          break;
        case MultimodalLiveResponseType.INTERRUPTED:
          addMessage("[中断されました]", "system");
          if (audioPlayerRef.current) {
            audioPlayerRef.current.interrupt();
          }
          break;
        default:
          break;
      }
    };

    const disconnect = () => {
      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }

      if (audioStreamerRef.current) {
        audioStreamerRef.current.stop();
        audioStreamerRef.current = null;
      }
      if (videoStreamerRef.current) {
        videoStreamerRef.current.stop();
        videoStreamerRef.current = null;
      }
      if (screenCaptureRef.current) {
        screenCaptureRef.current.stop();
        screenCaptureRef.current = null;
      }
      if (audioPlayerRef.current) {
        audioPlayerRef.current.destroy();
        audioPlayerRef.current = null;
      }

      setConnected(false);
      setAudioStreaming(false);
      setVideoStreaming(false);
      setScreenSharing(false);

      if (videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = null;
        videoPreviewRef.current.hidden = true;
      }
      if (userMonitorRef.current) {
        userMonitorRef.current.stop();
        userMonitorRef.current = null;
      }
      setMonitoringEnabled(false);
      setMonitoringState(null);

      if (videoPreviewMainRef.current) {
        videoPreviewMainRef.current.srcObject = null;
      }
    };

    // Cleanup on unmount
    useEffect(() => {
      return () => {
        disconnect();
      };
    }, []);

    const connect = async () => {
      if (!proxyUrl || !projectId) {
        alert("プロキシ URL とプロジェクト ID を入力してください");
        return;
      }

      pendingAuthRef.current = true;

      try {
        clientRef.current = new GeminiLiveAPI(proxyUrl, projectId, model);

        clientRef.current.appPassword = appPassword;
        clientRef.current.systemInstructions = systemInstructions;
        clientRef.current.inputAudioTranscription = enableInputTranscription;
        clientRef.current.outputAudioTranscription = enableOutputTranscription;
        clientRef.current.googleGrounding = enableGrounding;
        clientRef.current.enableAffectiveDialog = enableAffectiveDialog;
        clientRef.current.responseModalities = ["AUDIO"];
        clientRef.current.voiceName = voice;
        clientRef.current.temperature = parseFloat(temperature);
        clientRef.current.proactivity = {
          proactiveAudio: enableProactiveAudio,
        };
        clientRef.current.automaticActivityDetection = {
          disabled: disableActivityDetection,
          silence_duration_ms: parseInt(silenceDuration),
          prefix_padding_ms: parseInt(prefixPadding),
          end_of_speech_sensitivity: endSpeechSensitivity,
          start_of_speech_sensitivity: startSpeechSensitivity,
        };

        clientRef.current.activityHandling = activityHandling;

        // Always register separation anxiety tool (all personas)
        clientRef.current.addFunction(
          new ExpressSeparationAnxietyTool((message) => {
            addMessage(message, "separation-anxiety");
          })
        );

        // Always register camera observation tool
        clientRef.current.addFunction(
          new ReportVisualStateTool((state) => {
            setVisualState({
              description: state.description || "",
              emotion: state.user_emotion || "",
              items: state.detected_items || "",
              timestamp: new Date().toLocaleTimeString("ja-JP"),
            });
          })
        );

        // Register persona-specific tools
        if (persona === "bright_friend" || persona === "mean_neighbor" || persona === "stupid_dog" || persona === "lover_male" || persona === "lover_female") {
          clientRef.current.addFunction(
            new CelebrateMomentTool((message) => {
              addMessage(message, "celebrate");
            })
          );
        }

        if (persona === "bright_friend" || persona === "gentle_teacher" || persona === "stupid_dog" || persona === "lover_male" || persona === "lover_female") {
          clientRef.current.addFunction(
            new OfferSupportTool((message) => {
              addMessage(message, "support");
            })
          );
        }

        clientRef.current.onReceiveResponse = handleMessage;
        clientRef.current.onErrorMessage = (error) => {
          console.error("Error:", error);
          addMessage(`[接続エラー: ${error}]`, "system");
        };
        clientRef.current.onConnectionStarted = () => {
          setConnected(true);
        };
        // Explicit auth error message from server (most reliable signal)
        clientRef.current.onAuthError = () => {
          pendingAuthRef.current = false;
          resetAuth();
          setConnected(false);
          disconnect();
        };
        clientRef.current.onClose = (event) => {
          if (pendingAuthRef.current) {
            // Connection closed before setup complete — treat as auth failure
            // regardless of close code (covers code 4001 and any normalized codes)
            pendingAuthRef.current = false;
            resetAuth();
          } else {
            addMessage("[接続が切断されました]", "system");
          }
          setConnected(false);
          disconnect();
        };

        await clientRef.current.connect();

        audioStreamerRef.current = new AudioStreamer(clientRef.current);
        videoStreamerRef.current = new VideoStreamer(clientRef.current);
        screenCaptureRef.current = new ScreenCapture(clientRef.current);
        audioPlayerRef.current = new AudioPlayer();
        await audioPlayerRef.current.init();
        audioPlayerRef.current.setVolume(volume / 100);
      } catch (error) {
        console.error("Connection failed:", error);
        addMessage(`[接続失敗: ${error.message}]`, "system");
        pendingAuthRef.current = false;
        disconnect();
      }
    };

    const toggleAudio = async () => {
      if (!audioStreaming) {
        try {
          if (!audioStreamerRef.current && clientRef.current) {
            audioStreamerRef.current = new AudioStreamer(clientRef.current);
          }

          if (audioStreamerRef.current) {
            await audioStreamerRef.current.start(selectedMic);
            setAudioStreaming(true);
            addMessage("[マイク オン]", "system");
          } else {
            addMessage("[先に Gemini に接続してください]", "system");
          }
        } catch (error) {
          addMessage("[音声エラー: " + error.message + "]", "system");
        }
      } else {
        if (audioStreamerRef.current) audioStreamerRef.current.stop();
        setAudioStreaming(false);
        addMessage("[マイク オフ]", "system");
      }
    };

    const toggleVideo = async () => {
      if (!videoStreaming) {
        try {
          if (!videoStreamerRef.current && clientRef.current) {
            videoStreamerRef.current = new VideoStreamer(clientRef.current);
          }

          if (videoStreamerRef.current) {
            const video = await videoStreamerRef.current.start({
              deviceId: selectedCamera || undefined,
              facingMode: selectedCamera ? undefined : facingMode,
              nudgeEveryNFrames: 10,
              nudgeText: "[report_visual_state] 映像の状況を報告してください",
              shouldNudgeFn: () => {
                if (userMonitorRef.current) {
                  return userMonitorRef.current.getStateManager().shouldNudge();
                }
                return true; // Default: nudge if no monitor
              },
            });
            setVideoStreaming(true);
            if (videoPreviewRef.current) {
              videoPreviewRef.current.srcObject = video.srcObject;
              videoPreviewRef.current.hidden = false;
            }
            if (videoPreviewMainRef.current) {
              videoPreviewMainRef.current.srcObject = video.srcObject;
            }
            addMessage("[カメラ オン]", "system");
          } else {
            addMessage("[先に Gemini に接続してください]", "system");
          }
        } catch (error) {
          addMessage("[映像エラー: " + error.message + "]", "system");
        }
      } else {
        // Stop monitoring if running
        if (userMonitorRef.current) {
          userMonitorRef.current.stop();
          userMonitorRef.current = null;
          setMonitoringEnabled(false);
          addMessage("[見守り自動停止（カメラオフ）]", "system");
        }

        if (videoStreamerRef.current) videoStreamerRef.current.stop();
        setVideoStreaming(false);
        if (videoPreviewRef.current) {
          videoPreviewRef.current.srcObject = null;
          videoPreviewRef.current.hidden = true;
        }
        if (videoPreviewMainRef.current) {
          videoPreviewMainRef.current.srcObject = null;
        }
        addMessage("[カメラ オフ]", "system");
      }
    };

    const toggleScreen = async () => {
      if (!screenSharing) {
        try {
          if (!screenCaptureRef.current && clientRef.current) {
            screenCaptureRef.current = new ScreenCapture(clientRef.current);
          }

          if (screenCaptureRef.current) {
            const video = await screenCaptureRef.current.start();
            setScreenSharing(true);
            if (videoPreviewRef.current) {
              videoPreviewRef.current.srcObject = video.srcObject;
              videoPreviewRef.current.hidden = false;
            }
            if (videoPreviewMainRef.current) {
              videoPreviewMainRef.current.srcObject = video.srcObject;
            }
            addMessage("[画面共有 オン]", "system");
          } else {
            addMessage("[先に Gemini に接続してください]", "system");
          }
        } catch (error) {
          addMessage("[画面共有エラー: " + error.message + "]", "system");
        }
      } else {
        if (screenCaptureRef.current) screenCaptureRef.current.stop();
        setScreenSharing(false);
        if (!videoStreaming && videoPreviewRef.current) {
          videoPreviewRef.current.srcObject = null;
          videoPreviewRef.current.hidden = true;
        }
        if (!videoStreaming && videoPreviewMainRef.current) {
          videoPreviewMainRef.current.srcObject = null;
        }
        addMessage("[画面共有 オフ]", "system");
      }
    };

    const toggleMonitoring = () => {
      if (!monitoringEnabled) {
        // Start monitoring
        if (!videoStreaming || !videoPreviewMainRef.current?.srcObject) {
          addMessage("[監視を開始するにはカメラを先にオンにしてください]", "system");
          return;
        }

        // Get the video element that has the camera stream
        const videoEl = videoPreviewMainRef.current;

        const monitor = new UserStateMonitor({
          analysisUrl: (() => {
            const wsUrl = proxyUrl || import.meta.env.VITE_WEBSOCKET_URL || "ws://localhost:8080";
            const httpBase = wsUrl.replace(/^ws(s?):\/\//, "http$1://").replace(/\/ws$/, "");
            return `${httpBase}/analyze-frame`;
          })(),
          appPassword: appPassword,
          projectId: projectId,
          model: "gemini-2.0-flash",
          intervalMs: 5000,
          lowIntervalMs: 60000,
          mediumConsecutiveThreshold: 2,
          onSignificantChange: (analysis, previousKey) => {
            // Send a text message to the Live API to trigger the AI to speak about the change
            if (clientRef.current && clientRef.current.connected) {
              const changePrompt = `[自動監視システムからの通知] ユーザーの状態が変化しました。前の状態: "${previousKey}" → 現在の状態: "${analysis.status_key}"。観察結果: ${analysis.observation}。この変化に気づいて、友達として自然に声をかけてください。声で話しかけてください。`;
              clientRef.current.sendTextMessage(changePrompt);
              addMessage(`[見守り検知: ${previousKey} → ${analysis.status_key}]`, "system");
            } else {
              addMessage("[見守りエラー: Gemini未接続]", "system");
            }

            setMonitoringHistory((prev) => {
              const next = [
                ...prev,
                {
                  type: "change",
                  from: previousKey,
                  to: analysis.status_key,
                  observation: analysis.observation,
                  timestamp: new Date().toLocaleTimeString("ja-JP"),
                },
              ];
              return next.slice(-10);
            });
          },
          onStateUpdate: (state) => {
            setMonitoringState({
              statusKey: state.status_key,
              observation: state.observation,
              emotion: state.emotion,
              details: state.details,
              timestamp: state.timestamp,
              significantChange: state.significant_change,
            });
          },
          onError: (error) => {
            console.error("Monitor error:", error);
            addMessage(`[見守りエラー: ${error.message}]`, "system");
          },
        });

        monitor.start(videoEl);
        userMonitorRef.current = monitor;
        setMonitoringEnabled(true);
        addMessage("[ユーザー監視 開始]", "system");
      } else {
        // Stop monitoring
        if (userMonitorRef.current) {
          userMonitorRef.current.stop();
          userMonitorRef.current = null;
        }
        setMonitoringEnabled(false);
        addMessage("[ユーザー監視 停止]", "system");
      }
    };

    const sendMessage = () => {
      if (!chatInput.trim()) return;

      if (clientRef.current) {
        addMessage(chatInput, "user");
        clientRef.current.sendTextMessage(chatInput);
        setChatInput("");
      } else {
        addMessage("[先に Gemini に接続してください]", "system");
      }
    };

    const handleVolumeChange = (e) => {
      const newVolume = e.target.value;
      setVolume(newVolume);
      if (audioPlayerRef.current) {
        audioPlayerRef.current.setVolume(newVolume / 100);
      }
    };

    // Expose methods to parent
    useImperativeHandle(ref, () => ({
      connect,
      disconnect,
      toggleAudio,
    }));

    // Notify parent of state changes
    useEffect(() => {
      onConnectionChange?.(connected);
    }, [connected, onConnectionChange]);

    useEffect(() => {
      onAudioStreamChange?.(audioStreaming);
    }, [audioStreaming, onAudioStreamChange]);

    // Show password overlay if not authenticated
    if (!appPassword) {
      return (
        <div className="signin-overlay">
          <div className="signin-card">
            <h1>AI パートナー</h1>
            <p className="signin-subtitle">Gemini Live API 搭載</p>
            <form className="password-form" onSubmit={handlePasswordSubmit}>
              <input
                type="password"
                className="password-input"
                placeholder="パスワードを入力"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                autoFocus
              />
              <button type="submit" className="password-submit">
                入室
              </button>
            </form>
            {authError && <p className="signin-error">{authError}</p>}
          </div>
        </div>
      );
    }

    return (
      <div className="live-api-demo">
        <div className="toolbar">
          <div className="toolbar-left">
            <h1>AI パートナー</h1>
            <span className="powered-by">Gemini Live API 搭載</span>
          </div>
          <div className="toolbar-center">
            <div className="dropdown">
              <button className="dropbtn">設定 ▾</button>
              <div className="dropdown-content config-dropdown">
                {/* API Configuration Section */}
                <div className="control-group">
                  <h3>接続設定</h3>
                  <div className="input-group">
                    <label>プロジェクト ID:</label>
                    <input
                      type="text"
                      value={projectId}
                      onChange={(e) => setProjectId(e.target.value)}
                      disabled={connected}
                    />
                  </div>
                  <div className="input-group">
                    <label>モデル ID:</label>
                    <input
                      type="text"
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      disabled={connected}
                    />
                  </div>
                </div>

                <div className="control-group">
                  <h3>Gemini 動作設定</h3>
                  <div className="input-group">
                    <label>ペルソナ:</label>
                    <select
                      value={persona}
                      onChange={(e) => setPersona(e.target.value)}
                      disabled={connected}
                    >
                      <option value="bright_friend">😊 明るい友達</option>
                      <option value="gentle_teacher">📖 優しい先生</option>
                      <option value="mean_neighbor">😠 意地悪な隣人</option>
                      <option value="stupid_dog">🐕 アホな犬</option>
                      <option value="lover_male">💙 恋人（男性）</option>
                      <option value="lover_female">💗 恋人（女性）</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>システムインストラクション:</label>
                    <textarea
                      rows="3"
                      value={systemInstructions}
                      readOnly
                      disabled={true}
                    />
                  </div>
                  <div className="input-group">
                    <label>音声:</label>
                    <select
                      value={voice}
                      onChange={(e) => setVoice(e.target.value)}
                      disabled={connected}
                    >
                      <option value="Puck">Puck（デフォルト）</option>
                      <option value="Charon">Charon</option>
                      <option value="Kore">Kore</option>
                      <option value="Fenrir">Fenrir</option>
                      <option value="Aoede">Aoede</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>温度パラメータ: {temperature}</label>
                    <input
                      type="range"
                      min="0.1"
                      max="2.0"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(e.target.value)}
                      disabled={connected}
                    />
                  </div>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableProactiveAudio}
                      onChange={(e) =>
                        setEnableProactiveAudio(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>プロアクティブ音声を有効化</label>
                  </div>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableGrounding}
                      onChange={(e) => setEnableGrounding(e.target.checked)}
                      disabled={connected}
                    />
                    <label>Google グラウンディングを有効化</label>
                  </div>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableAffectiveDialog}
                      onChange={(e) =>
                        setEnableAffectiveDialog(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>感情対話を有効化</label>
                  </div>
                </div>

                <div className="control-group">
                  <h3>文字起こし設定</h3>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableInputTranscription}
                      onChange={(e) =>
                        setEnableInputTranscription(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>入力の文字起こしを有効化</label>
                  </div>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableOutputTranscription}
                      onChange={(e) =>
                        setEnableOutputTranscription(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>出力の文字起こしを有効化</label>
                  </div>
                </div>

                <div className="control-group">
                  <h3>アクティビティ検出設定</h3>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={disableActivityDetection}
                      onChange={(e) =>
                        setDisableActivityDetection(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>自動アクティビティ検出を無効化</label>
                  </div>
                  <div className="input-group">
                    <label>無音時間 (ms):</label>
                    <input
                      type="number"
                      value={silenceDuration}
                      onChange={(e) => setSilenceDuration(e.target.value)}
                      min="500"
                      max="10000"
                      step="100"
                      disabled={connected}
                    />
                  </div>
                  <div className="input-group">
                    <label>プレフィックスパディング (ms):</label>
                    <input
                      type="number"
                      value={prefixPadding}
                      onChange={(e) => setPrefixPadding(e.target.value)}
                      min="0"
                      max="2000"
                      step="100"
                      disabled={connected}
                    />
                  </div>
                  <div className="input-group">
                    <label>発話終了感度:</label>
                    <select
                      value={endSpeechSensitivity}
                      onChange={(e) => setEndSpeechSensitivity(e.target.value)}
                      disabled={connected}
                    >
                      <option value="END_SENSITIVITY_UNSPECIFIED">
                        デフォルト
                      </option>
                      <option value="END_SENSITIVITY_HIGH">高</option>
                      <option value="END_SENSITIVITY_LOW">低</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>発話開始感度:</label>
                    <select
                      value={startSpeechSensitivity}
                      onChange={(e) =>
                        setStartSpeechSensitivity(e.target.value)
                      }
                      disabled={connected}
                    >
                      <option value="START_SENSITIVITY_UNSPECIFIED">
                        デフォルト
                      </option>
                      <option value="START_SENSITIVITY_HIGH">高</option>
                      <option value="START_SENSITIVITY_LOW">低</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>アクティビティ処理:</label>
                    <select
                      value={activityHandling}
                      onChange={(e) => setActivityHandling(e.target.value)}
                      disabled={connected}
                    >
                      <option value="ACTIVITY_HANDLING_UNSPECIFIED">
                        デフォルト（割り込み）
                      </option>
                      <option value="START_OF_ACTIVITY_INTERRUPTS">
                        割り込み（バージイン）
                      </option>
                      <option value="NO_INTERRUPTION">割り込みなし</option>
                    </select>
                  </div>
                </div>

                {setupJson && (
                  <div className="control-group">
                    <h3>セットアップメッセージ JSON</h3>
                    <pre className="setup-json-display">
                      {JSON.stringify(setupJson, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={connected ? disconnect : connect}
              className={connected ? "active connected" : ""}
            >
              {connected ? "切断" : "接続"}
            </button>

            <div className="dropdown">
              <button className="dropbtn">メディア ▾</button>
              <div className="dropdown-content media-dropdown">
                {/* Media Streaming Section */}
                <div className="control-group">
                  <div className="input-group">
                    <label>マイク:</label>
                    <select
                      value={selectedMic}
                      onChange={(e) => setSelectedMic(e.target.value)}
                    >
                      <option value="">デフォルトマイク</option>
                      {audioInputDevices.map((device) => (
                        <option key={device.deviceId} value={device.deviceId}>
                          {device.label || `Microphone ${device.deviceId}`}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="input-group">
                    <label>カメラ:</label>
                    <select
                      value={selectedCamera}
                      onChange={(e) => setSelectedCamera(e.target.value)}
                      disabled={videoStreaming}
                    >
                      <option value="">デフォルトカメラ</option>
                      {videoInputDevices.map((device) => (
                        <option key={device.deviceId} value={device.deviceId}>
                          {device.label || `Camera ${device.deviceId}`}
                        </option>
                      ))}
                    </select>
                  </div>
                  {!selectedCamera && (
                    <div className="input-group">
                      <label>カメラ向き:</label>
                      <select
                        value={facingMode}
                        onChange={(e) => setFacingMode(e.target.value)}
                        disabled={videoStreaming}
                      >
                        <option value="user">前面カメラ</option>
                        <option value="environment">背面カメラ</option>
                      </select>
                    </div>
                  )}

                  <div className="button-group-vertical">
                    <button
                      onClick={toggleAudio}
                      className={audioStreaming ? "active" : ""}
                    >
                      {audioStreaming ? "音声停止" : "音声開始"}
                    </button>
                    <button
                      onClick={toggleVideo}
                      className={videoStreaming ? "active" : ""}
                    >
                      {videoStreaming ? "映像停止" : "映像開始"}
                    </button>
                    <button
                      onClick={toggleScreen}
                      className={screenSharing ? "active" : ""}
                    >
                      {screenSharing ? "共有停止" : "画面共有"}
                    </button>
                  </div>

                  <div className="input-group">
                    <label>出力音量: {volume}%</label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={volume}
                      onChange={handleVolumeChange}
                    />
                  </div>

                  <video
                    ref={videoPreviewRef}
                    autoPlay
                    playsInline
                    muted
                    hidden
                    className="video-preview"
                  />
                </div>
              </div>
            </div>

            <div className="dropdown">
              <button className="dropbtn">チャット ▾</button>
              <div className="dropdown-content chat-dropdown">
                {/* Chat Section */}
                <div className="chat-container" ref={chatContainerRef}>
                  {chatMessages.length === 0 && (
                    <div>Gemini に接続してチャットを開始</div>
                  )}
                  {chatMessages.map(renderChatMessage)}
                </div>
                <div className="chat-input-area">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                    placeholder="メッセージを入力..."
                  />
                  <button onClick={sendMessage}>送信</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Dialog */}
        {modalVisible && (
          <div className="modal-overlay">
            <div className="modal-content">
              {modalContent.title && <h2>{modalContent.title}</h2>}
              <p>{modalContent.message}</p>
              <button onClick={() => setModalVisible(false)}>閉じる</button>
            </div>
          </div>
        )}

        <div className="main-content">
          <div className="info-panel">
            <h3>AI パートナーとは</h3>
            <p className="demo-intro">
              あなたに寄り添う AI パートナー。カメラ越しにあなたを見守り、
              声のトーンや表情を読み取りながら、自然な会話であなたの毎日をサポートします。
            </p>
            <div className="info-item">
              <h4>3つのペルソナ</h4>
              <p>
                設定からペルソナを選択できます。明るい友達・優しい先生・意地悪な隣人、
                それぞれ異なる個性でコミュニケーションします。
              </p>
            </div>
            <div className="info-item">
              <h4>感情を読み取る</h4>
              <p>
                カメラを通じてあなたの表情や状態を観察し、嬉しい時は一緒に喜び、
                疲れている時は寄り添います。
              </p>
            </div>
            <div className="info-item">
              <h4>試してみてください：</h4>
              <ul>
                <li>笑顔を見せてみる（お祝いしてくれるかも）</li>
                <li>疲れた表情をしてみる（寄り添ってくれるかも）</li>
                <li>ペルソナを切り替えて話しかける</li>
              </ul>
            </div>
          </div>

          <div className="chat-section">
            <div className="chat-container-main" ref={chatContainerRef}>
              {chatMessages.length === 0 && (
                <div className="empty-state">
                  <p>接続して AI パートナーと話しかけてみましょう</p>
                  {!connected && (
                    <button onClick={connect} className="connect-button">
                      今すぐ接続
                    </button>
                  )}
                </div>
              )}
              {chatMessages.map(renderChatMessage)}
            </div>
            <div className="chat-input-area-main">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                placeholder="メッセージを入力..."
                disabled={!connected}
              />
              <button onClick={sendMessage} disabled={!connected}>
                送信
              </button>
            </div>
          </div>

          <div className="video-section">
            <div className="video-container">
              <video
                ref={videoPreviewMainRef}
                autoPlay
                playsInline
                muted
                className="video-preview-main"
              />
              {!videoStreaming && (
                <div className="video-placeholder">カメラ オフ</div>
              )}
            </div>
            <div className="video-controls">
              <button
                onClick={toggleAudio}
                className={audioStreaming ? "active" : ""}
                disabled={!connected}
              >
                {audioStreaming ? "マイク停止" : "マイク開始"}
              </button>
              <button
                onClick={toggleVideo}
                className={videoStreaming ? "active" : ""}
                disabled={!connected}
              >
                {videoStreaming ? "カメラ停止" : "カメラ開始"}
              </button>
              <button
                onClick={toggleMonitoring}
                className={monitoringEnabled ? "active monitoring-btn" : "monitoring-btn"}
                disabled={!connected}
              >
                {monitoringEnabled ? "見守り停止" : "見守り開始"}
              </button>
            </div>

            {/* Visual State Panel */}
            <div className="visual-state-panel">
              <h4>映像認識状態</h4>
              {visualState ? (
                <div className="visual-state-content">
                  <div className="visual-state-row">
                    <span className="visual-state-label">状況:</span>
                    <span>{visualState.description}</span>
                  </div>
                  {visualState.emotion && (
                    <div className="visual-state-row">
                      <span className="visual-state-label">感情:</span>
                      <span className="visual-state-emotion">{visualState.emotion}</span>
                    </div>
                  )}
                  {visualState.items && (
                    <div className="visual-state-row">
                      <span className="visual-state-label">検出物:</span>
                      <span>{visualState.items}</span>
                    </div>
                  )}
                  <div className="visual-state-timestamp">
                    最終更新: {visualState.timestamp}
                  </div>
                </div>
              ) : (
                <div className="visual-state-empty">
                  カメラを起動すると映像の認識状態が表示されます
                </div>
              )}
            </div>

            {/* User Monitoring Panel */}
            <div className={`monitoring-panel ${monitoringEnabled ? "monitoring-active" : ""}`}>
              <h4>
                {monitoringEnabled && <span className="monitoring-indicator" />}
                見守りモニター
              </h4>
              {monitoringEnabled ? (
                <div className="monitoring-content">
                  {monitoringState ? (
                    <>
                      <div className="monitoring-row">
                        <span className="monitoring-label">現在の状態:</span>
                        <span className="monitoring-status-key">{monitoringState.statusKey}</span>
                      </div>
                      <div className="monitoring-row">
                        <span className="monitoring-label">観察:</span>
                        <span>{monitoringState.observation}</span>
                      </div>
                      {monitoringState.emotion && (
                        <div className="monitoring-row">
                          <span className="monitoring-label">感情:</span>
                          <span>{monitoringState.emotion}</span>
                        </div>
                      )}
                      {monitoringState.details && (
                        <div className="monitoring-row">
                          <span className="monitoring-label">詳細:</span>
                          <span>{monitoringState.details}</span>
                        </div>
                      )}
                      <div className="monitoring-timestamp">
                        最終分析: {monitoringState.timestamp}
                      </div>
                    </>
                  ) : (
                    <div className="monitoring-waiting">分析中...</div>
                  )}

                  {monitoringHistory.length > 0 && (
                    <div className="monitoring-history">
                      <h5>変化履歴</h5>
                      {monitoringHistory.map((entry, i) => (
                        <div key={i} className="monitoring-history-entry">
                          <span className="history-time">{entry.timestamp}</span>
                          <span className="history-change">
                            {entry.from} → {entry.to}
                          </span>
                          <span className="history-obs">{entry.observation}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="monitoring-empty">
                  カメラをオンにして「見守り開始」を押すと、
                  ユーザーの状況変化を自動検知して声かけします
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }
);

export default LiveAPIDemo;
