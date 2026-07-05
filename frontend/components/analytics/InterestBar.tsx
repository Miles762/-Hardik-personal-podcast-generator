"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_INK, SERIES_BLUE } from "@/lib/chartTheme";
import type { NameValue } from "@/types/dashboard";

// Magnitude by category → horizontal bars, sorted. Single measure = single hue
// (color is not carrying identity here, the axis labels do). One axis. Rounded
// data-ends anchored to baseline (dataviz mark spec).
export function InterestBar({ data }: { data: NameValue[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Top Interests</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(160, data.length * 34)}>
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
            <CartesianGrid stroke={CHART_INK.grid} horizontal={false} />
            <XAxis type="number" stroke={CHART_INK.axis} tick={{ fontSize: 11, fill: CHART_INK.text }} allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="name"
              stroke={CHART_INK.axis}
              tick={{ fontSize: 12, fill: CHART_INK.text }}
              width={90}
            />
            <Tooltip
              cursor={{ fill: "#ffffff10" }}
              contentStyle={{
                background: CHART_INK.surface,
                border: `1px solid ${CHART_INK.grid}`,
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Bar dataKey="value" fill={SERIES_BLUE} radius={[0, 4, 4, 0]} barSize={16} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
