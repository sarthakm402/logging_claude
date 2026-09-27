export default function ActivityTable({ data }) {
    return (
        <div className="table-card">
            <div className="section-title">Recent API Activity</div>

            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Source</th>
                        <th>Model</th>
                        <th>Effort</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                        <th>Latency</th>
                    </tr>
                </thead>

                <tbody>
                    {data.map((row, index) => (
                        <tr key={row.request_id || index}>
                            <td>
                                {new Date(row.timestamp).toLocaleString()}
                            </td>
                            <td>{row.query_source || "-"}</td>
                            <td>{row.model || "-"}</td>
                            <td>{row.effort || "-"}</td>
                            <td>{row.total_tokens?.toLocaleString()}</td>
                            <td>${Number(row.cost || 0).toFixed(4)}</td>
                            <td>{Number(row.duration_ms || 0).toFixed(0)} ms</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}