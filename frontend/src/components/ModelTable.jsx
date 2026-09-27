export default function ModelTable({ data }) {
    return (
        <div className="table-card">
            <div className="section-title">Model Usage</div>

            <table>
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Requests</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                        <th>Avg Latency</th>
                    </tr>
                </thead>

                <tbody>
                    {data.map((row, index) => (
                        <tr key={row.model || index}>
                            <td>{row.model || "-"}</td>
                            <td>{row.requests}</td>
                            <td>{row.tokens?.toLocaleString()}</td>
                            <td>${Number(row.cost || 0).toFixed(4)}</td>
                            <td>{Number(row.avg_latency_ms || 0).toFixed(0)} ms</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}