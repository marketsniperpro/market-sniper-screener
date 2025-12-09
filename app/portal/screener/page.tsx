"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import PageTransition from "../dashboard/components/PageTransition";
import { theme } from "@/styles/theme";
import PortalHeader from "../components/PortalHeader";

const ADMIN_EMAILS = ["alexcole.usa@gmail.com"];

interface ScreenerPick {
  id: string;
  ticker: string;
  company_name: string | null;
  pick_date: string;
  entry_price: number;
  current_price: number | null;
  exit_price: number | null;
  exit_date: string | null;
  gain_loss_pct: number | null;
  vix: number | null;
  rsi: number | null;
  adx: number | null;
  correction_pct: number | null;
  volume_ratio: number | null;
  volume_spike: boolean | null;
  pe_ratio: number | null;
  roe: number | null;
  debt_equity: number | null;
  signal_score: number | null;
  signal_strength: string;
  signal_factors: string[] | null;
  status: string;
  notes: string | null;
}

const STATUS_FILTERS = [
  { id: "active", label: "Active" },
  { id: "closed", label: "Closed" },
  { id: "all", label: "All" },
];

const SIGNAL_STRENGTHS = [
  { id: "strong", label: "Strong", color: "#00C853" },
  { id: "medium", label: "Medium", color: "#FFB300" },
  { id: "weak", label: "Weak", color: "#FF5252" },
];

export default function ScreenerPage() {
  const router = useRouter();
  const supabase = createClient();
  const [profile, setProfile] = useState<any>(null);
  const [picks, setPicks] = useState<ScreenerPick[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("active");
  const [accessDenied, setAccessDenied] = useState(false);
  const [selectedPick, setSelectedPick] = useState<ScreenerPick | null>(null);
  const [signalFilters, setSignalFilters] = useState<string[]>(["strong", "medium"]);
  const [currentVix, setCurrentVix] = useState<number | null>(null);

  const [accountSize, setAccountSize] = useState<string>("10000");
  const [riskPerTrade, setRiskPerTrade] = useState<string>("2");

  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    if (selectedPick) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [selectedPick]);

  const handleRescan = async () => {
    setScanning(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/stock-screener?mode=scan`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY}`,
          },
        }
      );

      const data = await response.json();
      console.log("Scan complete:", data);

      if (data.vix) {
        setCurrentVix(data.vix);
      }

      await new Promise((resolve) => setTimeout(resolve, 500));

      const { data: picksData, error } = await supabase
        .from("screener_picks")
        .select("*")
        .order("pick_date", { ascending: false });

      if (!error && picksData) {
        const latestByTicker = new Map<string, ScreenerPick>();
        for (const pick of picksData) {
          const existing = latestByTicker.get(pick.ticker);
          if (!existing || new Date(pick.pick_date) > new Date(existing.pick_date)) {
            latestByTicker.set(pick.ticker, pick);
          }
        }
        setPicks(Array.from(latestByTicker.values()));
      }
    } catch (error) {
      console.error("Rescan error:", error);
    }
    setScanning(false);
  };

  const toggleSignalFilter = (signal: string) => {
    if (signalFilters.includes(signal)) {
      if (signalFilters.length > 1) {
        setSignalFilters(signalFilters.filter((s) => s !== signal));
      }
    } else {
      setSignalFilters([...signalFilters, signal]);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      const { data: userData } = await supabase.auth.getUser();

      if (!userData.user) {
        router.push("/signup");
        return;
      }

      const email = userData.user.email?.toLowerCase() || "";

      const isAdmin = ADMIN_EMAILS.map((e) => e.toLowerCase()).includes(email);
      if (!isAdmin) {
        setAccessDenied(true);
        setLoading(false);
        return;
      }

      const { data: profiles } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", userData.user.id);

      if (profiles?.[0]) {
        setProfile(profiles[0]);
      }

      const { data: picksData, error } = await supabase
        .from("screener_picks")
        .select("*")
        .order("pick_date", { ascending: false });

      if (!error && picksData) {
        const latestByTicker = new Map<string, ScreenerPick>();
        for (const pick of picksData) {
          const existing = latestByTicker.get(pick.ticker);
          if (!existing || new Date(pick.pick_date) > new Date(existing.pick_date)) {
            latestByTicker.set(pick.ticker, pick);
          }
        }
        setPicks(Array.from(latestByTicker.values()));

        // Get latest VIX from picks
        const latestWithVix = picksData.find((p) => p.vix);
        if (latestWithVix?.vix) {
          setCurrentVix(latestWithVix.vix);
        }
      }

      setLoading(false);
    };

    fetchData();
  }, []);

  const filteredPicks = picks.filter((p) => {
    const statusMatch = statusFilter === "all" || p.status === statusFilter;
    const signalMatch = signalFilters.includes(p.signal_strength);
    return statusMatch && signalMatch;
  });

  const account = parseFloat(accountSize) || 0;
  const riskPct = parseFloat(riskPerTrade) || 2;
  const positionSize = (account * riskPct) / 100;

  const calculateGainLoss = (pick: ScreenerPick) => {
    if (pick.status === "closed" && pick.gain_loss_pct !== null) {
      return pick.gain_loss_pct;
    }
    if (pick.current_price && pick.entry_price) {
      return ((pick.current_price - pick.entry_price) / pick.entry_price) * 100;
    }
    return null;
  };

  const calculateShares = (pick: ScreenerPick) => {
    return Math.floor(positionSize / pick.entry_price);
  };

  // Stats
  const signalFilteredPicks = picks.filter((p) => signalFilters.includes(p.signal_strength));
  const closedPicks = signalFilteredPicks.filter(
    (p) => p.status === "closed" && p.gain_loss_pct !== null
  );
  const stats = {
    totalActive: signalFilteredPicks.filter((p) => p.status === "active").length,
    totalClosed: closedPicks.length,
    avgGain:
      closedPicks.length > 0
        ? closedPicks.reduce((acc, p) => acc + (p.gain_loss_pct || 0), 0) / closedPicks.length
        : 0,
    winRate:
      closedPicks.length > 0
        ? (closedPicks.filter((p) => (p.gain_loss_pct || 0) > 0).length / closedPicks.length) * 100
        : 0,
  };

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: theme.colors.background.primary,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: theme.colors.text.primary,
        }}
      >
        Loading...
      </div>
    );
  }

  if (accessDenied) {
    return (
      <PageTransition>
        <PortalHeader>
          <div style={{ textAlign: "center", padding: "3rem 1rem" }}>
            <div
              style={{
                width: "80px",
                height: "80px",
                background: `rgba(${theme.colors.primaryRgb}, 0.1)`,
                borderRadius: theme.borderRadius.full,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 1.5rem",
                fontSize: "2.5rem",
              }}
            >
              🔒
            </div>
            <h1
              style={{
                color: theme.colors.text.primary,
                fontSize: "1.75rem",
                fontWeight: theme.typography.fontWeight.bold,
                marginBottom: "1rem",
              }}
            >
              Access Restricted
            </h1>
            <Link
              href="/portal"
              style={{
                display: "inline-block",
                background: theme.colors.primary,
                color: "#000",
                padding: "0.875rem 2rem",
                borderRadius: theme.borderRadius.none,
                textDecoration: "none",
                fontWeight: theme.typography.fontWeight.semibold,
              }}
            >
              Back to Portal
            </Link>
          </div>
        </PortalHeader>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <PortalHeader>
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "0.5rem",
          }}
        >
          <h1
            style={{
              color: theme.colors.text.primary,
              fontSize: "1.5rem",
              fontWeight: theme.typography.fontWeight.bold,
              margin: 0,
            }}
          >
            VIX Screener
          </h1>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={handleRescan}
              disabled={scanning}
              style={{
                background: scanning ? theme.colors.background.secondary : theme.colors.primary,
                color: scanning ? theme.colors.text.secondary : "#000",
                fontSize: "0.85rem",
                padding: "0.5rem 1rem",
                border: "none",
                cursor: scanning ? "not-allowed" : "pointer",
                fontWeight: 600,
              }}
            >
              {scanning ? "Scanning..." : "Scan Now"}
            </button>
            <Link
              href="/portal"
              style={{
                color: theme.colors.primary,
                fontSize: "0.85rem",
                textDecoration: "none",
                padding: "0.5rem 1rem",
                border: `1px solid ${theme.colors.primary}`,
              }}
            >
              Portal
            </Link>
          </div>
        </div>

        {/* VIX Status */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            marginBottom: "1.5rem",
          }}
        >
          <p style={{ color: theme.colors.text.secondary, fontSize: "0.9rem", margin: 0 }}>
            Buy when VIX 20-35 + RSI recovering + ADX trending
          </p>
          {currentVix && (
            <span
              style={{
                padding: "0.25rem 0.75rem",
                background:
                  currentVix >= 20 && currentVix <= 35
                    ? "rgba(0, 200, 83, 0.1)"
                    : "rgba(255, 82, 82, 0.1)",
                border: `1px solid ${
                  currentVix >= 20 && currentVix <= 35 ? "#00C853" : "#FF5252"
                }`,
                color: currentVix >= 20 && currentVix <= 35 ? "#00C853" : "#FF5252",
                fontSize: "0.8rem",
                fontWeight: 600,
              }}
            >
              VIX: {currentVix.toFixed(1)}{" "}
              {currentVix >= 20 && currentVix <= 35 ? "✓ BUY ZONE" : "○ WAIT"}
            </span>
          )}
        </div>

        {/* Stats */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "0.75rem",
            marginBottom: "1.5rem",
          }}
        >
          <StatBox label="Active" value={stats.totalActive.toString()} />
          <StatBox label="Closed" value={stats.totalClosed.toString()} />
          <StatBox
            label="Avg Gain"
            value={stats.totalClosed > 0 ? `${stats.avgGain.toFixed(1)}%` : "—"}
            highlight={stats.avgGain > 0}
          />
          <StatBox
            label="Win Rate"
            value={stats.totalClosed > 0 ? `${stats.winRate.toFixed(0)}%` : "—"}
            highlight={stats.winRate > 50}
          />
        </div>

        {/* Position Sizing */}
        <div
          style={{
            background: theme.colors.background.secondary,
            border: `1px solid ${theme.colors.border.default}`,
            padding: "1rem",
            marginBottom: "1.5rem",
          }}
        >
          <div style={{ display: "flex", gap: "1rem", alignItems: "flex-end" }}>
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.7rem",
                  color: theme.colors.text.secondary,
                  textTransform: "uppercase",
                  marginBottom: "0.25rem",
                }}
              >
                Account ($)
              </label>
              <input
                type="number"
                value={accountSize}
                onChange={(e) => setAccountSize(e.target.value)}
                style={{
                  width: "120px",
                  padding: "0.5rem",
                  background: theme.colors.background.primary,
                  border: `1px solid ${theme.colors.border.default}`,
                  color: theme.colors.text.primary,
                  fontSize: "0.9rem",
                }}
              />
            </div>
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.7rem",
                  color: theme.colors.text.secondary,
                  textTransform: "uppercase",
                  marginBottom: "0.25rem",
                }}
              >
                Risk (%)
              </label>
              <input
                type="number"
                value={riskPerTrade}
                onChange={(e) => setRiskPerTrade(e.target.value)}
                style={{
                  width: "80px",
                  padding: "0.5rem",
                  background: theme.colors.background.primary,
                  border: `1px solid ${theme.colors.border.default}`,
                  color: theme.colors.text.primary,
                  fontSize: "0.9rem",
                }}
              />
            </div>
            <div style={{ fontSize: "0.85rem", color: theme.colors.text.secondary }}>
              Position:{" "}
              <strong style={{ color: theme.colors.primary }}>
                ${positionSize.toLocaleString()}
              </strong>
              /trade
            </div>
          </div>
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
          <div>
            <div
              style={{
                fontSize: "0.7rem",
                color: theme.colors.text.secondary,
                textTransform: "uppercase",
                marginBottom: "0.5rem",
              }}
            >
              Status
            </div>
            <div style={{ display: "flex", gap: "0.25rem" }}>
              {STATUS_FILTERS.map((filter) => (
                <button
                  key={filter.id}
                  onClick={() => setStatusFilter(filter.id)}
                  style={{
                    padding: "0.4rem 0.75rem",
                    background:
                      statusFilter === filter.id ? theme.colors.primary : "transparent",
                    color: statusFilter === filter.id ? "#000" : theme.colors.text.secondary,
                    border: `1px solid ${
                      statusFilter === filter.id
                        ? theme.colors.primary
                        : theme.colors.border.default
                    }`,
                    cursor: "pointer",
                    fontSize: "0.8rem",
                  }}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div
              style={{
                fontSize: "0.7rem",
                color: theme.colors.text.secondary,
                textTransform: "uppercase",
                marginBottom: "0.5rem",
              }}
            >
              Signal
            </div>
            <div style={{ display: "flex", gap: "0.25rem" }}>
              {SIGNAL_STRENGTHS.map((signal) => {
                const isSelected = signalFilters.includes(signal.id);
                return (
                  <button
                    key={signal.id}
                    onClick={() => toggleSignalFilter(signal.id)}
                    style={{
                      padding: "0.4rem 0.6rem",
                      background: isSelected ? `${signal.color}20` : "transparent",
                      color: isSelected ? signal.color : theme.colors.text.secondary,
                      border: `1px solid ${isSelected ? signal.color : theme.colors.border.default}`,
                      cursor: "pointer",
                      fontSize: "0.75rem",
                    }}
                  >
                    {signal.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Picks Table */}
        {filteredPicks.length === 0 ? (
          <div
            style={{
              background: theme.colors.background.secondary,
              border: `1px solid ${theme.colors.border.default}`,
              padding: "3rem",
              textAlign: "center",
            }}
          >
            <p style={{ color: theme.colors.text.secondary, margin: 0 }}>
              {currentVix && (currentVix < 20 || currentVix > 35)
                ? `VIX ${currentVix.toFixed(1)} outside buy zone (20-35). Waiting for fear...`
                : "No picks match the current filters."}
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                background: theme.colors.background.secondary,
                border: `1px solid ${theme.colors.border.default}`,
              }}
            >
              <thead>
                <tr style={{ borderBottom: `1px solid ${theme.colors.border.default}` }}>
                  <th style={thStyle}>Ticker</th>
                  <th style={thStyle}>Date</th>
                  <th style={thStyle}>Entry</th>
                  <th style={thStyle}>Return</th>
                  <th style={thStyle}>VIX</th>
                  <th style={thStyle}>RSI</th>
                  <th style={thStyle}>ADX</th>
                  <th style={thStyle}>Correction</th>
                  <th style={thStyle}>Volume</th>
                  <th style={thStyle}>P/E</th>
                  <th style={thStyle}>Score</th>
                </tr>
              </thead>
              <tbody>
                {filteredPicks.map((pick) => {
                  const gainLoss = calculateGainLoss(pick);
                  const isPositive = gainLoss !== null && gainLoss > 0;
                  const isNegative = gainLoss !== null && gainLoss < 0;

                  return (
                    <tr
                      key={pick.id}
                      onClick={() => setSelectedPick(pick)}
                      style={{
                        borderBottom: `1px solid ${theme.colors.border.default}`,
                        cursor: "pointer",
                      }}
                      onMouseOver={(e) =>
                        (e.currentTarget.style.background = `rgba(${theme.colors.primaryRgb}, 0.05)`)
                      }
                      onMouseOut={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <td style={tdStyle}>
                        <span style={{ fontWeight: 600, color: theme.colors.text.primary }}>
                          {pick.ticker}
                        </span>
                      </td>
                      <td style={tdStyle}>
                        {new Date(pick.pick_date).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                        })}
                      </td>
                      <td style={tdStyle}>${pick.entry_price.toFixed(2)}</td>
                      <td
                        style={{
                          ...tdStyle,
                          color: isPositive
                            ? "#00C853"
                            : isNegative
                            ? "#FF5252"
                            : theme.colors.text.secondary,
                          fontWeight: 600,
                        }}
                      >
                        {gainLoss !== null
                          ? `${gainLoss >= 0 ? "+" : ""}${gainLoss.toFixed(1)}%`
                          : "—"}
                      </td>
                      <td style={tdStyle}>
                        <span
                          style={{
                            color:
                              pick.vix && pick.vix >= 20 && pick.vix <= 35
                                ? "#00C853"
                                : theme.colors.text.secondary,
                          }}
                        >
                          {pick.vix?.toFixed(1) || "—"}
                        </span>
                      </td>
                      <td style={tdStyle}>{pick.rsi?.toFixed(0) || "—"}</td>
                      <td style={tdStyle}>{pick.adx?.toFixed(0) || "—"}</td>
                      <td style={tdStyle}>
                        {pick.correction_pct ? `${pick.correction_pct.toFixed(0)}%` : "—"}
                      </td>
                      <td style={tdStyle}>
                        {pick.volume_spike ? (
                          <span style={{ color: "#FF8C00", fontWeight: 600 }}>
                            {pick.volume_ratio?.toFixed(1)}x ↑
                          </span>
                        ) : (
                          <span style={{ color: theme.colors.text.secondary }}>
                            {pick.volume_ratio?.toFixed(1)}x
                          </span>
                        )}
                      </td>
                      <td style={tdStyle}>
                        {pick.pe_ratio !== null ? (
                          <span
                            style={{
                              color:
                                pick.pe_ratio > 0 && pick.pe_ratio < 25
                                  ? "#6495ED"
                                  : theme.colors.text.secondary,
                            }}
                          >
                            {pick.pe_ratio.toFixed(1)}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td style={tdStyle}>
                        <SignalScore score={pick.signal_score} strength={pick.signal_strength} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Strategy Note */}
        <div
          style={{
            marginTop: "1.5rem",
            padding: "1rem",
            background: `rgba(${theme.colors.primaryRgb}, 0.05)`,
            border: `1px solid rgba(${theme.colors.primaryRgb}, 0.2)`,
            fontSize: "0.8rem",
            color: theme.colors.text.secondary,
          }}
        >
          <strong style={{ color: theme.colors.text.primary }}>VIX Strategy:</strong> Buy when
          market fear is elevated (VIX 20-35) but not panicking ({"<"}35).
          <br />
          <strong style={{ color: "#00C853" }}>Entry:</strong> RSI recovering from oversold
          (35-55), ADX {">"} 18 (trending), 20-55% below 52-week high
          <br />
          <strong style={{ color: theme.colors.primary }}>Score:</strong>{" "}
          <span style={{ color: "#00C853" }}>Strong ≥75</span> |{" "}
          <span style={{ color: "#FFB300" }}>Medium ≥50</span> |{" "}
          <span style={{ color: "#FF5252" }}>Weak {"<"}50</span>
          <br />
          <strong style={{ color: theme.colors.text.primary }}>Backtest:</strong> 62% win rate,
          +$316k P&L (2019-2024)
        </div>

        {/* Detail Modal */}
        {selectedPick &&
          typeof document !== "undefined" &&
          createPortal(
            <div
              style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: "rgba(0,0,0,0.85)",
                zIndex: 9999,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "1rem",
              }}
              onClick={() => setSelectedPick(null)}
            >
              <div
                style={{
                  background: theme.colors.background.secondary,
                  border: `1px solid ${theme.colors.border.default}`,
                  width: "100%",
                  maxWidth: "900px",
                  maxHeight: "90vh",
                  overflow: "hidden",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {/* Modal Header */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "1rem",
                    borderBottom: `1px solid ${theme.colors.border.default}`,
                  }}
                >
                  <div>
                    <h2
                      style={{
                        margin: 0,
                        color: theme.colors.text.primary,
                        fontSize: "1.25rem",
                      }}
                    >
                      {selectedPick.ticker}
                      <span
                        style={{
                          color: theme.colors.text.secondary,
                          fontWeight: 400,
                          marginLeft: "0.5rem",
                          fontSize: "0.9rem",
                        }}
                      >
                        {selectedPick.company_name}
                      </span>
                    </h2>
                  </div>
                  <button
                    onClick={() => setSelectedPick(null)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: theme.colors.text.secondary,
                      fontSize: "1.5rem",
                      cursor: "pointer",
                    }}
                  >
                    ×
                  </button>
                </div>

                {/* TradingView Chart */}
                <div style={{ height: "400px", background: "#131722" }}>
                  <iframe
                    src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol=${selectedPick.ticker}&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=0&toolbarbg=f1f3f6&theme=dark&style=1&timezone=America%2FNew_York&withdateranges=1&hide_volume=true`}
                    style={{ width: "100%", height: "100%", border: "none" }}
                    allowFullScreen
                  />
                </div>

                {/* Pick Details */}
                <div
                  style={{
                    padding: "1rem",
                    borderTop: `1px solid ${theme.colors.border.default}`,
                  }}
                >
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(5, 1fr)",
                      gap: "1rem",
                      marginBottom: "1rem",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "0.65rem", color: theme.colors.text.secondary }}>
                        Entry
                      </div>
                      <div style={{ color: theme.colors.text.primary, fontWeight: 600 }}>
                        ${selectedPick.entry_price.toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "0.65rem", color: theme.colors.text.secondary }}>
                        VIX at Entry
                      </div>
                      <div
                        style={{
                          color:
                            selectedPick.vix && selectedPick.vix >= 20 && selectedPick.vix <= 35
                              ? "#00C853"
                              : theme.colors.text.primary,
                          fontWeight: 600,
                        }}
                      >
                        {selectedPick.vix?.toFixed(1) || "—"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "0.65rem", color: theme.colors.text.secondary }}>
                        RSI
                      </div>
                      <div style={{ color: theme.colors.text.primary, fontWeight: 600 }}>
                        {selectedPick.rsi?.toFixed(0) || "—"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "0.65rem", color: theme.colors.text.secondary }}>
                        ADX
                      </div>
                      <div style={{ color: theme.colors.text.primary, fontWeight: 600 }}>
                        {selectedPick.adx?.toFixed(0) || "—"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "0.65rem", color: theme.colors.text.secondary }}>
                        Correction
                      </div>
                      <div style={{ color: theme.colors.text.primary, fontWeight: 600 }}>
                        {selectedPick.correction_pct?.toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  {/* Signal Factors */}
                  {selectedPick.signal_factors && selectedPick.signal_factors.length > 0 && (
                    <div
                      style={{
                        paddingTop: "1rem",
                        borderTop: `1px dashed ${theme.colors.border.default}`,
                      }}
                    >
                      <div
                        style={{
                          fontSize: "0.65rem",
                          color: theme.colors.text.secondary,
                          marginBottom: "0.5rem",
                        }}
                      >
                        Signal Factors:
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                        {selectedPick.signal_factors.map((factor, i) => (
                          <span
                            key={i}
                            style={{
                              fontSize: "0.75rem",
                              padding: "0.25rem 0.5rem",
                              background: `rgba(${theme.colors.primaryRgb}, 0.1)`,
                              color: theme.colors.text.primary,
                            }}
                          >
                            {factor}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Position Sizing */}
                {account > 0 && (
                  <div
                    style={{
                      padding: "1rem",
                      borderTop: `1px solid ${theme.colors.border.default}`,
                      background: `rgba(${theme.colors.primaryRgb}, 0.05)`,
                      display: "flex",
                      gap: "2rem",
                    }}
                  >
                    <div>
                      <span style={{ fontSize: "0.8rem", color: theme.colors.text.secondary }}>
                        Position:{" "}
                      </span>
                      <span style={{ color: theme.colors.primary, fontWeight: 600 }}>
                        ${positionSize.toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span style={{ fontSize: "0.8rem", color: theme.colors.text.secondary }}>
                        Shares:{" "}
                      </span>
                      <span style={{ color: theme.colors.primary, fontWeight: 600 }}>
                        {calculateShares(selectedPick)}
                      </span>
                    </div>
                    <div>
                      <span style={{ fontSize: "0.8rem", color: theme.colors.text.secondary }}>
                        Return:{" "}
                      </span>
                      <span
                        style={{
                          fontWeight: 600,
                          color:
                            (calculateGainLoss(selectedPick) || 0) >= 0 ? "#00C853" : "#FF5252",
                        }}
                      >
                        {calculateGainLoss(selectedPick) !== null
                          ? `${calculateGainLoss(selectedPick)! >= 0 ? "+" : ""}${calculateGainLoss(
                              selectedPick
                            )!.toFixed(1)}%`
                          : "—"}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>,
            document.body
          )}
      </PortalHeader>
    </PageTransition>
  );
}

const thStyle: React.CSSProperties = {
  padding: "0.75rem 0.5rem",
  textAlign: "left",
  fontSize: "0.7rem",
  fontWeight: 600,
  color: theme.colors.text.secondary,
  textTransform: "uppercase",
};

const tdStyle: React.CSSProperties = {
  padding: "0.75rem 0.5rem",
  fontSize: "0.85rem",
  color: theme.colors.text.primary,
};

function StatBox({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      style={{
        background: theme.colors.background.secondary,
        border: `1px solid ${theme.colors.border.default}`,
        padding: "1rem",
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: "0.7rem",
          color: theme.colors.text.secondary,
          textTransform: "uppercase",
          marginBottom: "0.25rem",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "1.25rem",
          fontWeight: 700,
          color: highlight ? theme.colors.primary : theme.colors.text.primary,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function SignalScore({ score, strength }: { score: number | null; strength: string }) {
  const colors: Record<string, string> = {
    strong: "#00C853",
    medium: "#FFB300",
    weak: "#FF5252",
  };

  const color = colors[strength] || colors.medium;

  if (score === null) {
    return (
      <span
        style={{
          padding: "0.25rem 0.5rem",
          fontSize: "0.7rem",
          fontWeight: 600,
          textTransform: "uppercase",
          background: `${color}20`,
          color,
        }}
      >
        {strength}
      </span>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <div
        style={{
          width: "40px",
          height: "6px",
          background: `${color}30`,
          borderRadius: "3px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${score}%`,
            height: "100%",
            background: color,
            borderRadius: "3px",
          }}
        />
      </div>
      <span style={{ fontSize: "0.75rem", fontWeight: 600, color }}>{score}</span>
    </div>
  );
}
