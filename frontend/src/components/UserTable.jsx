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
                    {data.map((row) => (
                        <tr key={row.user_identifier}>
                            <td>{row.user_identifier}</td>
                            <td>{row.requests}</td>
                            <td>{row.total_tokens?.toLocaleString()}</td>
                            <td>${Number(row.cost_usd || 0).toFixed(4)}</td>
                            <td>{row.sessions}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}