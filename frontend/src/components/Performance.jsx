export default function Performance({ data }) {
    if (!data) {
        return null;
    }

    return (
        <div className="performance-card">
            <div className="section-title">Performance</div>

            <div className="performance-grid">
                <div>
                    <span>Requests</span>
                    <strong>{data.requests}</strong>
                </div>

                <div>
                    <span>Avg Latency</span>
                    <strong>
                        {Number(data.avg_duration_ms || 0).toFixed(0)} ms
                    </strong>
                </div>

                <div>
                    <span>Avg TTFT</span>
                    <strong>
                        {Number(data.avg_ttft_ms || 0).toFixed(0)} ms
                    </strong>
                </div>

                <div>
                    <span>Min Latency</span>
                    <strong>
                        {Number(data.min_duration_ms || 0).toFixed(0)} ms
                    </strong>
                </div>

                <div>
                    <span>Max Latency</span>
                    <strong>
                        {Number(data.max_duration_ms || 0).toFixed(0)} ms
                    </strong>
                </div>
            </div>
        </div>
    );
}