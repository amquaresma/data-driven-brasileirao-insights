import { useMemo } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const CHART_COLORS = {
  green: "#2e7d32",
  red: "#c0392b",
  gray: "#999999",
  blue: "#635bff",
  teal: "#00897b",
};

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

// Lido a cada renderização: acompanha o tema (claro ou escuro) sem cor fixa no código.
function getBaseOptions() {
  const text = cssVar("--text-secondary", "#aaa");
  const grid = cssVar("--border", "#333");
  return {
    responsive: true,
    aspectRatio: window.innerWidth < 640 ? 1 : 2,
    plugins: {
      legend: { labels: { color: text } },
    },
    scales: {
      x: {
        ticks: { color: text, autoSkip: false, maxRotation: 90, minRotation: 45, font: { size: 11 } },
        grid: { color: grid },
      },
      y: { ticks: { color: text }, grid: { color: grid } },
    },
  };
}

export function GoalsChart({ entries }) {
  const sorted = useMemo(
    () => [...entries].sort((a, b) => a.position - b.position),
    [entries],
  );

  const data = {
    labels: sorted.map((e) => e.team.short_name || e.team.name),
    datasets: [
      {
        label: "Gols Pró",
        data: sorted.map((e) => e.goals_for),
        backgroundColor: CHART_COLORS.green,
      },
      {
        label: "Gols Contra",
        data: sorted.map((e) => e.goals_against),
        backgroundColor: CHART_COLORS.red,
      },
    ],
  };

  return (
    <div className="chart-card">
      <h3>Gols marcados vs sofridos</h3>
      <Bar
        data={data}
        options={{ ...getBaseOptions(), plugins: { ...getBaseOptions().plugins, title: { display: false } } }}
      />
    </div>
  );
}

export function EfficiencyChart({ entries }) {
  const sorted = useMemo(
    () => [...entries].sort((a, b) => (b.efficiency ?? 0) - (a.efficiency ?? 0)),
    [entries],
  );

  const data = {
    labels: sorted.map((e) => e.team.short_name || e.team.name),
    datasets: [
      {
        label: "Aproveitamento (%)",
        data: sorted.map((e) => e.efficiency),
        backgroundColor: CHART_COLORS.blue,
      },
    ],
  };

  return (
    <div className="chart-card">
      <h3>Aproveitamento por time</h3>
      <Bar data={data} options={getBaseOptions()} />
    </div>
  );
}

export function GoalDifferenceChart({ entries }) {
  const sorted = useMemo(
    () => [...entries].sort((a, b) => (b.goal_difference ?? 0) - (a.goal_difference ?? 0)),
    [entries],
  );

  const data = {
    labels: sorted.map((e) => e.team.short_name || e.team.name),
    datasets: [
      {
        label: "Saldo de gols",
        data: sorted.map((e) => e.goal_difference),
        backgroundColor: sorted.map((e) =>
          (e.goal_difference ?? 0) >= 0 ? CHART_COLORS.teal : CHART_COLORS.red,
        ),
      },
    ],
  };

  return (
    <div className="chart-card">
      <h3>Saldo de gols</h3>
      <Bar data={data} options={getBaseOptions()} />
    </div>
  );
}

export function ResultsDistributionChart({ entries }) {
  const sorted = useMemo(
    () => [...entries].sort((a, b) => a.position - b.position),
    [entries],
  );

  const data = {
    labels: sorted.map((e) => e.team.short_name || e.team.name),
    datasets: [
      {
        label: "Vitórias",
        data: sorted.map((e) => e.wins),
        backgroundColor: CHART_COLORS.green,
      },
      {
        label: "Empates",
        data: sorted.map((e) => e.draws),
        backgroundColor: CHART_COLORS.gray,
      },
      {
        label: "Derrotas",
        data: sorted.map((e) => e.losses),
        backgroundColor: CHART_COLORS.red,
      },
    ],
  };

  return (
    <div className="chart-card">
      <h3>Distribuição de resultados (V/E/D)</h3>
      <Bar
        data={data}
        options={{
          ...getBaseOptions(),
          scales: {
            x: { ...getBaseOptions().scales.x, stacked: true },
            y: { ...getBaseOptions().scales.y, stacked: true },
          },
        }}
      />
    </div>
  );
}
