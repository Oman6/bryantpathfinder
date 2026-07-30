"use client";

import { useEffect, useState } from "react";

const BRYANT_LAT = 41.9215;
const BRYANT_LON = -71.5557;

// Open-Meteo WMO weathercodes → emoji + label.
// Only the codes we actually need; fall back to a neutral icon.
const CODE_LABELS: Record<number, { icon: string; label: string }> = {
  0: { icon: "☀", label: "clear" },
  1: { icon: "🌤", label: "mostly clear" },
  2: { icon: "⛅", label: "partly cloudy" },
  3: { icon: "☁", label: "cloudy" },
  45: { icon: "🌫", label: "fog" },
  48: { icon: "🌫", label: "fog" },
  51: { icon: "🌦", label: "drizzle" },
  53: { icon: "🌦", label: "drizzle" },
  55: { icon: "🌦", label: "drizzle" },
  61: { icon: "🌧", label: "rain" },
  63: { icon: "🌧", label: "rain" },
  65: { icon: "🌧", label: "heavy rain" },
  71: { icon: "🌨", label: "snow" },
  73: { icon: "🌨", label: "snow" },
  75: { icon: "❄", label: "heavy snow" },
  77: { icon: "🌨", label: "snow grains" },
  80: { icon: "🌧", label: "showers" },
  81: { icon: "🌧", label: "showers" },
  82: { icon: "⛈", label: "violent showers" },
  95: { icon: "⛈", label: "thunderstorm" },
  96: { icon: "⛈", label: "thunderstorm" },
  99: { icon: "⛈", label: "thunderstorm" },
};

interface DayForecast {
  date: string;
  weekday: string;
  high: number;
  low: number;
  code: number;
  precipPct: number;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function WeatherStrip() {
  const [days, setDays] = useState<DayForecast[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const url = new URL("https://api.open-meteo.com/v1/forecast");
    url.searchParams.set("latitude", String(BRYANT_LAT));
    url.searchParams.set("longitude", String(BRYANT_LON));
    url.searchParams.set(
      "daily",
      "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    );
    url.searchParams.set("temperature_unit", "fahrenheit");
    url.searchParams.set("timezone", "America/New_York");
    url.searchParams.set("forecast_days", "5");

    fetch(url.toString())
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d) => {
        const dts: string[] = d?.daily?.time ?? [];
        const codes: number[] = d?.daily?.weathercode ?? [];
        const highs: number[] = d?.daily?.temperature_2m_max ?? [];
        const lows: number[] = d?.daily?.temperature_2m_min ?? [];
        const precip: number[] = d?.daily?.precipitation_probability_max ?? [];
        const out: DayForecast[] = dts.map((iso, i) => {
          const date = new Date(iso + "T00:00:00");
          return {
            date: iso,
            weekday: WEEKDAYS[date.getDay()],
            high: Math.round(highs[i]),
            low: Math.round(lows[i]),
            code: codes[i] ?? 0,
            precipPct: precip[i] ?? 0,
          };
        });
        setDays(out);
      })
      .catch(() => setError(true));
  }, []);

  if (error || !days) return null;

  return (
    <div className="rounded-2xl border border-black/5 bg-white px-6 py-3">
      <div
        className="flex items-baseline justify-between text-[10px] uppercase tracking-wide text-[#5F5D58]"
        style={{ fontFamily: "var(--font-geist-mono), monospace" }}
      >
        <span>Smithfield · 5-day forecast</span>
        <span className="text-[#5F5D58]/60">open-meteo</span>
      </div>
      <div className="mt-2 grid grid-cols-5 gap-2">
        {days.map((d) => {
          const meta = CODE_LABELS[d.code] ?? { icon: "·", label: "" };
          return (
            <div
              key={d.date}
              className="flex flex-col items-center gap-0.5 rounded-lg bg-[#FAFAF7] px-2 py-2"
              title={meta.label}
            >
              <span
                className="text-[10px] text-[#5F5D58]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                {d.weekday}
              </span>
              <span className="text-lg leading-none">{meta.icon}</span>
              <span
                className="text-[11px] text-[#1A1A1A]"
                style={{ fontFamily: "var(--font-geist-mono), monospace" }}
              >
                {d.high}°/{d.low}°
              </span>
              {d.precipPct >= 30 && (
                <span
                  className="text-[9px] text-blue-600"
                  style={{ fontFamily: "var(--font-geist-mono), monospace" }}
                >
                  {d.precipPct}%
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
