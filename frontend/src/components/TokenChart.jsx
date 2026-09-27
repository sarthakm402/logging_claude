import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
} from "recharts";

export default function TokenChart({ data }) {
    return (
        <div className="chart-card">
            <div className="section-title">Token Usage</div>

            <ResponsiveContainer width="100%" height={320}>
                <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />

                    <Line
                        type="monotone"
                        dataKey="input_tokens"
                        name="Input"
                        stroke="#6366f1"
                    />

                    <Line
                        type="monotone"
                        dataKey="output_tokens"
                        name="Output"
                        stroke="#22c55e"
                    />

                    <Line
                        type="monotone"
                        dataKey="cache_read_tokens"
                        name="Cache Read"
                        stroke="#f59e0b"
                    />

                    <Line
                        type="monotone"
                        dataKey="cache_creation_tokens"
                        name="Cache Creation"
                        stroke="#ef4444"
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}