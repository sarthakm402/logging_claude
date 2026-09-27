import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
} from "recharts";

export default function CostChart({ data }) {
    return (
        <div className="chart-card">
            <div className="section-title">Cost Over Time</div>

            <ResponsiveContainer width="100%" height={320}>
                <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />

                    <Line
                        type="monotone"
                        dataKey="cost"
                        name="Cost"
                        stroke="#8b5cf6"
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}