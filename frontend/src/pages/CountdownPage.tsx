import { useState, useEffect } from "react";
import { Heart, Sparkles, Calendar } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";

const TARGET_DATE = new Date("2026-06-12T00:00:00");

interface TimeLeft {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
}

function calcTimeLeft(): TimeLeft {
  const now = new Date();
  const diff = TARGET_DATE.getTime() - now.getTime();
  if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0 };
  return {
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((diff / (1000 * 60)) % 60),
    seconds: Math.floor((diff / 1000) % 60),
  };
}

function TimeUnit({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative group">
        <div className="absolute -inset-1 rounded-lg bg-gradient-to-b from-pink-500/20 to-rose-600/20 blur-sm group-hover:blur-md transition-all duration-500" />
        <div className="relative w-24 h-28 sm:w-32 sm:h-36 rounded-lg border border-pink-500/30 bg-card flex items-center justify-center backdrop-blur-sm">
          <span className="text-4xl sm:text-5xl font-heading font-bold text-pink-400 tabular-nums tracking-wider">
            {String(value).padStart(2, "0")}
          </span>
        </div>
      </div>
      <span className="text-[10px] sm:text-xs tracking-[0.3em] uppercase text-pink-300/70 font-medium">
        {label}
      </span>
    </div>
  );
}

export default function CountdownPage() {
  const [timeLeft, setTimeLeft] = useState<TimeLeft>(calcTimeLeft);
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(calcTimeLeft());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Heartbeat effect
  useEffect(() => {
    const heartbeat = setInterval(() => {
      setPulse(true);
      setTimeout(() => setPulse(false), 300);
    }, 1500);
    return () => clearInterval(heartbeat);
  }, []);

  const totalDaysOriginal = Math.ceil(
    (TARGET_DATE.getTime() - new Date("2025-01-01").getTime()) / (1000 * 60 * 60 * 24)
  );
  const daysElapsed = totalDaysOriginal - timeLeft.days;
  const progress = Math.min((daysElapsed / totalDaysOriginal) * 100, 100);

  return (
    <AppLayout>
      <div className="flex flex-col items-center justify-center min-h-[80vh] relative overflow-hidden">
        {/* Floating hearts background */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          {[...Array(6)].map((_, i) => (
            <Heart
              key={i}
              className="absolute text-pink-500/10 animate-float"
              size={20 + i * 8}
              style={{
                left: `${10 + i * 15}%`,
                top: `${20 + (i % 3) * 25}%`,
                animationDelay: `${i * 0.7}s`,
                animationDuration: `${4 + i}s`,
              }}
              fill="currentColor"
            />
          ))}
        </div>

        {/* Header */}
        <div className="flex items-center gap-3 mb-2 z-10">
          <Sparkles className="h-4 w-4 text-pink-400/60" />
          <p className="text-[10px] tracking-[0.4em] uppercase text-pink-300/50 font-medium">
            Contagem Regressiva
          </p>
          <Sparkles className="h-4 w-4 text-pink-400/60" />
        </div>

        {/* Heart icon */}
        <div className="relative mb-6 z-10">
          <Heart
            className={`h-16 w-16 text-pink-500 transition-transform duration-300 ${
              pulse ? "scale-125" : "scale-100"
            }`}
            fill="currentColor"
          />
          <div
            className={`absolute inset-0 rounded-full blur-xl transition-opacity duration-300 ${
              pulse ? "opacity-60" : "opacity-20"
            }`}
            style={{ background: "radial-gradient(circle, hsl(340, 80%, 55%), transparent)" }}
          />
        </div>

        {/* Title */}
        <h1 className="text-2xl sm:text-3xl font-heading font-bold tracking-wider text-foreground uppercase mb-1 z-10">
          Dias até te ver
        </h1>
        <div className="flex items-center gap-2 mb-10 z-10">
          <Calendar className="h-3.5 w-3.5 text-pink-400/70" />
          <p className="text-sm text-pink-300/70 font-mono">12 de junho de 2026</p>
        </div>

        {/* Countdown units */}
        <div className="flex gap-3 sm:gap-5 mb-10 z-10">
          <TimeUnit value={timeLeft.days} label="Dias" />
          <div className="flex flex-col items-center justify-center h-28 sm:h-36">
            <span className="text-2xl text-pink-500/50 font-bold animate-pulse">:</span>
          </div>
          <TimeUnit value={timeLeft.hours} label="Horas" />
          <div className="flex flex-col items-center justify-center h-28 sm:h-36">
            <span className="text-2xl text-pink-500/50 font-bold animate-pulse">:</span>
          </div>
          <TimeUnit value={timeLeft.minutes} label="Minutos" />
          <div className="flex flex-col items-center justify-center h-28 sm:h-36">
            <span className="text-2xl text-pink-500/50 font-bold animate-pulse">:</span>
          </div>
          <TimeUnit value={timeLeft.seconds} label="Segundos" />
        </div>

        {/* Progress bar */}
        <div className="w-full max-w-md z-10">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] tracking-widest uppercase text-muted-foreground">
              Progresso
            </span>
            <span className="text-[10px] font-mono text-pink-400">
              {progress.toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-1000"
              style={{
                width: `${progress}%`,
                background: "linear-gradient(90deg, hsl(340, 80%, 45%), hsl(330, 70%, 55%), hsl(340, 80%, 45%))",
                backgroundSize: "200% 100%",
                animation: "shimmer 2s ease-in-out infinite",
              }}
            />
          </div>
        </div>

        {/* Quote */}
        <div className="mt-10 text-center z-10 max-w-sm">
          <p className="text-xs text-muted-foreground italic leading-relaxed">
            "A saudade é o amor que fica."
          </p>
        </div>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); opacity: 0.3; }
          50% { transform: translateY(-30px) rotate(10deg); opacity: 0.6; }
        }
        .animate-float { animation: float 5s ease-in-out infinite; }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
      `}</style>
    </AppLayout>
  );
}
