export default function UserTable({ data }) {
    return (
        <div className="table-card">
            <div className="section-title">User Usage</div>

            <table>
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Requests</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                        <th>Sessions</th>
                    </tr>
                </thead>

                <tbody>
                    {data.map((row, index) => (
                        <tr key={row.user || index}>
                            <td>{row.user || "-"}</td>
                            <td>{row.requests}</td>
                            <td>{row.tokens?.toLocaleString()}</td>
                            <td>${Number(row.cost || 0).toFixed(4)}</td>
                            <td>{row.sessions}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}