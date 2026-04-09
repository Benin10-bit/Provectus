import { useState, useEffect, useCallback, useRef } from "react";
import { Timer, Clock, Play, Pause, RotateCcw, Maximize, Minimize } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";

interface TimerState {
  mode: "timer" | "stopwatch";
  timerSeconds: number;
  elapsed: number;
  running: boolean;
  lastTick: number | null;
  finished: boolean;
}

let persisted: TimerState = {
  mode: "timer",
  timerSeconds: 300,
  elapsed: 0,
  running: false,
  lastTick: null,
  finished: false,
};

function playAlarm() {
  const ctx = new AudioContext();
  const beep = (time: number) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "square";
    osc.frequency.value = 1200;
    gain.gain.setValueAtTime(0.25, time);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.08);
    osc.connect(gain).connect(ctx.destination);
    osc.start(time);
    osc.stop(time + 0.08);
  };
  for (let i = 0; i < 12; i++) {
    beep(ctx.currentTime + i * 0.12);
  }
}

function CircularProgress({
  progress,
  size = 280,
  stroke = 4,
  children,
}: {
  progress: number;
  size?: number;
  stroke?: number;
  children: React.ReactNode;
}) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - Math.min(Math.max(progress, 0), 1));

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="hsl(var(--border))" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="hsl(var(--accent))" strokeWidth={stroke}
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round" className="transition-all duration-200"
        />
      </svg>
      {progress > 0 && progress < 1 && (
        <div
          className="absolute w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-accent"
          style={{
            top: size / 2 - r * Math.cos(2 * Math.PI * progress) - 6,
            left: size / 2 + r * Math.sin(2 * Math.PI * progress) - 6,
            boxShadow: "0 0 8px hsl(var(--accent) / 0.6)",
          }}
        />
      )}
      <div className="absolute inset-0 flex items-center justify-center">{children}</div>
    </div>
  );
}

function fmtTimer(ms: number) {
  const totalSec = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function fmtStopwatch(ms: number) {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function TimerPage() {
  const [mode, setMode] = useState<"timer" | "stopwatch">(persisted.mode);
  const [timerSeconds, setTimerSeconds] = useState(persisted.timerSeconds);
  const [elapsed, setElapsed] = useState(persisted.elapsed);
  const [running, setRunning] = useState(persisted.running);
  const [finished, setFinished] = useState(persisted.finished);
  const lastTickRef = useRef<number | null>(persisted.lastTick);
  const alarmPlayed = useRef(persisted.finished);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    if (persisted.running && persisted.lastTick) {
      const delta = Date.now() - persisted.lastTick;
      const newElapsed = persisted.elapsed + delta;
      if (mode === "timer") {
        const totalMs = timerSeconds * 1000;
        if (newElapsed >= totalMs) {
          setElapsed(totalMs);
          setRunning(false);
          setFinished(true);
          if (!alarmPlayed.current) { playAlarm(); alarmPlayed.current = true; }
        } else {
          setElapsed(newElapsed);
        }
      } else {
        setElapsed(newElapsed);
      }
      lastTickRef.current = Date.now();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    persisted = { mode, timerSeconds, elapsed, running, lastTick: lastTickRef.current, finished };
    if (running || elapsed > 0) {
      const display = mode === "timer" ? fmtTimer(timerSeconds * 1000 - elapsed) : fmtStopwatch(elapsed);
      document.title = `${display} - Provectus`;
    } else {
      document.title = "Provectus";
    }
  });

  useEffect(() => {
    return () => {
      if (!persisted.running && persisted.elapsed === 0) document.title = "Provectus";
    };
  }, []);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      const now = Date.now();
      const delta = lastTickRef.current ? now - lastTickRef.current : 16;
      lastTickRef.current = now;
      setElapsed((prev) => {
        const next = prev + delta;
        if (mode === "timer") {
          const totalMs = timerSeconds * 1000;
          if (next >= totalMs) {
            setRunning(false);
            setFinished(true);
            if (!alarmPlayed.current) { playAlarm(); alarmPlayed.current = true; }
            return totalMs;
          }
        }
        return next;
      });
    }, 50);
    return () => clearInterval(id);
  }, [running, mode, timerSeconds]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.code === "Space" && e.target === document.body) {
        e.preventDefault();
        toggleRunning();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, finished]);

  const toggleRunning = useCallback(() => {
    if (finished && mode === "timer") return;
    setRunning((r) => { if (!r) lastTickRef.current = Date.now(); return !r; });
  }, [finished, mode]);

  const reset = useCallback(() => {
    setRunning(false); setElapsed(0); setFinished(false);
    lastTickRef.current = null; alarmPlayed.current = false;
  }, []);

  const switchMode = useCallback((m: "timer" | "stopwatch") => {
    if (m === mode) return;
    reset(); setMode(m);
  }, [mode, reset]);

  const addTime = useCallback((sec: number) => {
    if (running) return;
    setTimerSeconds((t) => t + sec);
    setElapsed(0); setFinished(false); alarmPlayed.current = false;
  }, [running]);

  const setPreset = useCallback((sec: number) => {
    if (running) return;
    setTimerSeconds(sec);
    setElapsed(0); setFinished(false); alarmPlayed.current = false;
  }, [running]);

  const totalMs = timerSeconds * 1000;
  const progress = mode === "timer" ? (totalMs > 0 ? elapsed / totalMs : 0) : (elapsed % 60000) / 60000;
  const displayTime = mode === "timer" ? fmtTimer(totalMs - elapsed) : fmtStopwatch(elapsed);

  const presets = [
    { label: "0:30", sec: 30 },
    { label: "1:00", sec: 60 },
    { label: "5:00", sec: 300 },
    { label: "10:00", sec: 600 },
    { label: "25:00", sec: 1500 },
    { label: "45:00", sec: 2700 },
  ];

  const circleSize = fullscreen ? 320 : 240;

  const content = (
    <div className={`flex flex-col items-center gap-6 sm:gap-8 py-4 sm:py-6 px-4 ${fullscreen ? "justify-center min-h-screen" : ""}`}>
      {/* Mode tabs */}
      <div className="flex items-center gap-1 p-1 rounded-lg bg-muted">
        <button
          onClick={() => switchMode("timer")}
          className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-md text-xs sm:text-sm font-medium transition-all duration-200 ${
            mode === "timer" ? "bg-primary text-primary-foreground hud-glow" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Timer className="h-4 w-4" />
          <span>Timer</span>
        </button>
        <button
          onClick={() => switchMode("stopwatch")}
          className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-md text-xs sm:text-sm font-medium transition-all duration-200 ${
            mode === "stopwatch" ? "bg-primary text-primary-foreground hud-glow" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Clock className="h-4 w-4" />
          <span>Cronômetro</span>
        </button>
      </div>

      <CircularProgress progress={progress} size={circleSize}>
        <span className={`text-4xl sm:text-5xl md:text-6xl font-heading font-bold tabular-nums tracking-wider ${
          finished ? "text-accent animate-pulse" : "text-foreground"
        }`}>
          {displayTime}
        </span>
      </CircularProgress>

      {mode === "timer" && !running && !finished && (
        <div className="flex flex-col items-center gap-3 w-full max-w-sm">
          <div className="flex flex-wrap justify-center gap-1.5 sm:gap-2">
            {presets.map((p) => (
              <button
                key={p.label}
                onClick={() => setPreset(p.sec)}
                className={`px-2.5 sm:px-3 py-1.5 rounded-lg text-[10px] sm:text-xs font-medium border transition-all duration-200 ${
                  timerSeconds === p.sec
                    ? "border-accent text-accent bg-accent/10"
                    : "border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            {[{ label: "+0:30", sec: 30 }, { label: "+1:00", sec: 60 }, { label: "+5:00", sec: 300 }].map((a) => (
              <button
                key={a.label}
                onClick={() => addTime(a.sec)}
                className="px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium border border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground bg-card transition-all duration-200"
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {finished && mode === "timer" && (
        <p className="text-sm text-accent font-medium tracking-wider uppercase animate-pulse">
          Tempo esgotado!
        </p>
      )}

      <div className="flex gap-3 w-full max-w-sm">
        <button
          onClick={toggleRunning}
          disabled={finished && mode === "timer"}
          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-semibold transition-all duration-200 ${
            finished && mode === "timer"
              ? "bg-muted text-muted-foreground cursor-not-allowed"
              : running
              ? "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              : "bg-primary text-primary-foreground hover:bg-primary/90 hud-glow"
          } active:scale-[0.98]`}
        >
          {running ? <><Pause className="h-4 w-4 sm:h-5 sm:w-5" /> Pausar</> : <><Play className="h-4 w-4 sm:h-5 sm:w-5" /> Iniciar</>}
        </button>
        <button
          onClick={reset}
          className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-semibold bg-card border border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground transition-all duration-200 active:scale-[0.98]"
        >
          <RotateCcw className="h-4 w-4 sm:h-5 sm:w-5" /> Resetar
        </button>
      </div>

      <button
        onClick={() => setFullscreen((f) => !f)}
        className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium border border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground bg-card transition-all duration-200"
      >
        {fullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
        {fullscreen ? "Sair da tela cheia" : "Tela cheia"}
      </button>

      <p className="text-[9px] sm:text-[10px] tracking-widest uppercase text-muted-foreground">
        Pressione <kbd className="px-1.5 py-0.5 rounded-md bg-muted border border-border text-foreground text-[10px] font-mono">Space</kbd> para pausar / continuar
      </p>
    </div>
  );

  if (fullscreen) {
    return <div className="fixed inset-0 z-50 bg-background animate-fade-in">{content}</div>;
  }

  return <AppLayout>{content}</AppLayout>;
}
