"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CATEGORICAL, CHART_INK } from "@/lib/chartTheme";
import type { NameValue } from "@/types/dashboard";

// Identity across categories → donut with categorical hues in FIXED order and a
// legend (identity never color-alone). Slices separated by a surface gap. Small
// N (<= 4 voices) keeps this readable.
export function VoiceDonut({ data }: { data: NameValue[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Preferred Voices</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={2}
              stroke={CHART_INK.surface}
              strokeWidth={2}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={CATEGORICAL[i % CATEGORICAL.length]} />
              ))}
            </Pie>
            <Legend
              formatter={(v) => <span style={{ color: CHART_INK.text, textTransform: "capitalize" }}>{v}</span>}
            />
            <Tooltip
              contentStyle={{
                background: CHART_INK.surface,
                border: `1px solid ${CHART_INK.grid}`,
                borderRadius: 8,
                fontSize: 12,
                textTransform: "capitalize",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
