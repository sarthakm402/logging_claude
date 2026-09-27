import { useState } from "react";

import {
    createProject,
    deleteProject,
    assignSessionToProject,
    unassignSessionFromProject,
} from "../api/dashboard";

function shortId(id) {
    return id ? `${id.slice(0, 8)}…` : "-";
}

export default function ProjectManager({ projects, sessions, onChange }) {
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [error, setError] = useState(null);

    async function handleCreate(event) {
        event.preventDefault();

        if (!name.trim()) {
            return;
        }

        try {
            setError(null);
            await createProject(name.trim(), description.trim());
            setName("");
            setDescription("");
            onChange();
        } catch (err) {
            setError(err.message);
        }
    }

    async function handleDelete(projectId, projectName) {
        if (
            !window.confirm(
                `Delete project "${projectName}"? Its sessions will become unassigned.`
            )
        ) {
            return;
        }

        try {
            setError(null);
            await deleteProject(projectId);
            onChange();
        } catch (err) {
            setError(err.message);
        }
    }

    async function handleAssign(sessionId, projectId) {
        try {
            setError(null);

            if (projectId === "") {
                await unassignSessionFromProject(sessionId);
            } else {
                await assignSessionToProject(sessionId, Number(projectId));
            }

            onChange();
        } catch (err) {
            setError(err.message);
        }
    }

    return (
        <div className="table-card project-manager">
            <div className="section-title">Manage Projects</div>

            {error && <div className="error">{error}</div>}

            <form className="project-form" onSubmit={handleCreate}>
                <input
                    type="text"
                    placeholder="Project name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                />

                <input
                    type="text"
                    placeholder="Description (optional)"
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                />

                <button type="submit" className="btn btn-primary">
                    Create Project
                </button>
            </form>

            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Description</th>
                        <th></th>
                    </tr>
                </thead>

                <tbody>
                    {projects.length === 0 && (
                        <tr>
                            <td colSpan={3} className="empty-row">
                                No projects yet — create one above.
                            </td>
                        </tr>
                    )}

                    {projects.map((project) => (
                        <tr key={project.id}>
                            <td>{project.name}</td>
                            <td>{project.description || "-"}</td>
                            <td>
                                <button
                                    className="btn btn-danger"
                                    onClick={() =>
                                        handleDelete(project.id, project.name)
                                    }
                                >
                                    Delete
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <div className="subsection-title">Sessions</div>

            <table>
                <thead>
                    <tr>
                        <th>Session</th>
                        <th>User</th>
                        <th>Last Activity</th>
                        <th>Project</th>
                    </tr>
                </thead>

                <tbody>
                    {sessions.map((session) => (
                        <tr key={session.session_id}>
                            <td title={session.session_id}>
                                {shortId(session.session_id)}
                            </td>
                            <td>{session.user || "-"}</td>
                            <td>
                                {new Date(
                                    session.last_activity_at
                                ).toLocaleString()}
                            </td>
                            <td>
                                <select
                                    className="session-select"
                                    value={session.project_id ?? ""}
                                    onChange={(event) =>
                                        handleAssign(
                                            session.session_id,
                                            event.target.value
                                        )
                                    }
                                >
                                    <option value="">Unassigned</option>

                                    {projects.map((project) => (
                                        <option
                                            key={project.id}
                                            value={project.id}
                                        >
                                            {project.name}
                                        </option>
                                    ))}
                                </select>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
