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

const baseOptions = {
  responsive: true,
  plugins: {
    legend: { labels: { color: "#ccc" } },
  },
  scales: {
    x: { ticks: { color: "#aaa" }, grid: { color: "#333" } },
    y: { ticks: { color: "#aaa" }, grid: { color: "#333" } },
  },
};

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
        options={{ ...baseOptions, plugins: { ...baseOptions.plugins, title: { display: false } } }}
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
      <Bar data={data} options={baseOptions} />
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
      <Bar data={data} options={baseOptions} />
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
          ...baseOptions,
          scales: {
            x: { ...baseOptions.scales.x, stacked: true },
            y: { ...baseOptions.scales.y, stacked: true },
          },
        }}
      />
    </div>
  );
}
