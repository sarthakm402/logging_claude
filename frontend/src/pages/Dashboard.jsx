import { useEffect, useState } from "react";

import MetricCard from "../components/MetricCard";
import TokenChart from "../components/TokenChart";
import CostChart from "../components/CostChart";
import ModelTable from "../components/ModelTable";
import UserTable from "../components/UserTable";
import ActivityTable from "../components/ActivityTable";
import Performance from "../components/Performance";

import {
    getProjects,
    getDashboardSummary,
    getDashboardTokens,
    getDashboardCost,
    getDashboardModels,
    getDashboardUsers,
    getDashboardActivity,
    getDashboardPerformance,
    getProjectSummary,
    getProjectTokens,
    getProjectCost,
    getProjectModels,
    getProjectUsers,
    getProjectActivity,
    getProjectPerformance,
} from "../api/dashboard";

function formatTokens(value) {
    return Number(value || 0).toLocaleString();
}

function formatCost(value) {
    return `$${Number(value || 0).toFixed(4)}`;
}

export default function Dashboard() {
    const [projects, setProjects] = useState([]);
    const [selectedProject, setSelectedProject] = useState("all");

    const [summary, setSummary] = useState(null);
    const [tokens, setTokens] = useState([]);
    const [cost, setCost] = useState([]);
    const [models, setModels] = useState([]);
    const [users, setUsers] = useState([]);
    const [activity, setActivity] = useState([]);
    const [performance, setPerformance] = useState(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadProjects();
    }, []);

    useEffect(() => {
        loadDashboard();
    }, [selectedProject]);

    async function loadProjects() {
        try {
            const data = await getProjects();
            setProjects(data);
        } catch (err) {
            console.error(err);
        }
    }

    async function loadDashboard() {
        try {
            setLoading(true);
            setError(null);

            let results;

            if (selectedProject === "all") {
                results = await Promise.all([
                    getDashboardSummary(),
                    getDashboardTokens(),
                    getDashboardCost(),
                    getDashboardModels(),
                    getDashboardUsers(),
                    getDashboardActivity(),
                    getDashboardPerformance(),
                ]);
            } else {
                const id = Number(selectedProject);

                results = await Promise.all([
                    getProjectSummary(id),
                    getProjectTokens(id),
                    getProjectCost(id),
                    getProjectModels(id),
                    getProjectUsers(id),
                    getProjectActivity(id),
                    getProjectPerformance(id),
                ]);
            }

            setSummary(results[0]);
            setTokens(results[1]);
            setCost(results[2]);
            setModels(results[3]);
            setUsers(results[4]);
            setActivity(results[5]);
            setPerformance(results[6]);
        } catch (err) {
            console.error(err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    if (loading && !summary) {
        return (
            <div className="loading">
                Loading Claude usage data...
            </div>
        );
    }

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <div>
                    <div className="eyebrow">POWER BI AI USAGE MONITOR</div>
                    <h1>Claude Code Usage</h1>
                    <p>
                        Monitor Claude usage while building Power BI reports.
                    </p>
                </div>

                <div className="project-selector">
                    <label>Project</label>

                    <select
                        value={selectedProject}
                        onChange={(event) =>
                            setSelectedProject(event.target.value)
                        }
                    >
                        <option value="all">All Projects</option>

                        {projects.map((project) => (
                            <option
                                key={project.id}
                                value={project.id}
                            >
                                {project.name}
                            </option>
                        ))}
                    </select>
                </div>
            </header>

            {error && (
                <div className="error">
                    {error}
                </div>
            )}

            {summary && (
                <>
                    <section className="metric-grid">
                        <MetricCard
                            label="Total Cost"
                            value={formatCost(summary.total_cost)}
                        />

                        <MetricCard
                            label="Total Tokens"
                            value={formatTokens(summary.total_tokens)}
                        />

                        <MetricCard
                            label="Input Tokens"
                            value={formatTokens(summary.input_tokens)}
                        />

                        <MetricCard
                            label="Output Tokens"
                            value={formatTokens(summary.output_tokens)}
                        />

                        <MetricCard
                            label="Cache Read"
                            value={formatTokens(summary.cache_read_tokens)}
                        />

                        <MetricCard
                            label="Cache Creation"
                            value={formatTokens(summary.cache_creation_tokens)}
                        />

                        <MetricCard
                            label="Requests"
                            value={formatTokens(summary.requests)}
                        />

                        <MetricCard
                            label="Prompts"
                            value={formatTokens(summary.prompts)}
                        />

                        <MetricCard
                            label="Users"
                            value={formatTokens(summary.users)}
                        />

                        <MetricCard
                            label="Sessions"
                            value={formatTokens(summary.sessions)}
                        />
                    </section>

                    <section className="chart-grid">
                        <TokenChart data={tokens} />
                        <CostChart data={cost} />
                    </section>

                    <section className="two-column">
                        <ModelTable data={models} />
                        <UserTable data={users} />
                    </section>

                    <Performance data={performance} />

                    <ActivityTable data={activity} />
                </>
            )}
        </div>
    );
}