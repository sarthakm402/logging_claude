from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest
)

from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest
)

import gzip

from db import get_connection


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============================================================
# HELPERS
# ============================================================

def get_or_create_user(cur, user_identifier):

    if not user_identifier:
        return None

    cur.execute(
        """
        INSERT INTO users (user_identifier)
        VALUES (%s)
        ON CONFLICT (user_identifier)
        DO UPDATE SET user_identifier = EXCLUDED.user_identifier
        RETURNING id
        """,
        (user_identifier,)
    )

    return cur.fetchone()[0]


def get_or_create_session(
    cur,
    session_id,
    user_id,
    timestamp
):

    if not session_id:
        return None

    cur.execute(
        """
        INSERT INTO sessions (
            session_id,
            user_id,
            started_at,
            last_activity_at
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (session_id)
        DO UPDATE SET
            last_activity_at = EXCLUDED.last_activity_at
        RETURNING id
        """,
        (
            session_id,
            user_id,
            timestamp,
            timestamp
        )
    )

    return cur.fetchone()[0]


def get_attributes(record):

    result = {}

    for attr in record.attributes:

        value = attr.value

        if value.HasField("string_value"):
            result[attr.key] = value.string_value

        elif value.HasField("int_value"):
            result[attr.key] = value.int_value

        elif value.HasField("double_value"):
            result[attr.key] = value.double_value

        elif value.HasField("bool_value"):
            result[attr.key] = value.bool_value

        else:
            result[attr.key] = str(value)

    return result


def get_attribute_value(value):

    if value.HasField("string_value"):
        return value.string_value

    if value.HasField("int_value"):
        return value.int_value

    if value.HasField("double_value"):
        return value.double_value

    if value.HasField("bool_value"):
        return value.bool_value

    return str(value)


# ============================================================
# OTEL LOG INGESTION
# ============================================================

@app.post("/v1/logs")
async def logs(request: Request):

    body = await request.body()

    if request.headers.get("content-encoding") == "gzip":
        body = gzip.decompress(body)

    data = ExportLogsServiceRequest()
    data.ParseFromString(body)

    print("\n========== LOGS ==========")

    with get_connection() as conn:

        with conn.cursor() as cur:

            for resource_log in data.resource_logs:

                for scope_log in resource_log.scope_logs:

                    for record in scope_log.log_records:

                        if not record.body.HasField("string_value"):
                            continue

                        event = record.body.string_value

                        attrs = get_attributes(record)

                        print("\nEVENT:", event)
                        print("ATTRS:", attrs)

                        user_identifier = (
                            attrs.get("user.email")
                            or attrs.get("user.id")
                            or attrs.get("user.account_id")
                        )

                        session_id = attrs.get("session.id")
                        timestamp = attrs.get("event.timestamp")

                        user_id = get_or_create_user(
                            cur,
                            user_identifier
                        )

                        get_or_create_session(
                            cur,
                            session_id,
                            user_id,
                            timestamp
                        )

                        # ------------------------------------
                        # USER PROMPT
                        # ------------------------------------

                        if event == "claude_code.user_prompt":

                            cur.execute(
                                """
                                INSERT INTO prompts (
                                    prompt_id,
                                    session_id,
                                    user_id,
                                    message_uuid,
                                    prompt,
                                    prompt_length,
                                    timestamp
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    attrs.get("prompt.id"),
                                    session_id,
                                    user_id,
                                    attrs.get("message.uuid"),
                                    attrs.get("prompt"),
                                    attrs.get("prompt_length"),
                                    timestamp
                                )
                            )

                        # ------------------------------------
                        # API REQUEST
                        # ------------------------------------

                        elif event == "claude_code.api_request":

                            input_tokens = int(
                                attrs.get("input_tokens") or 0
                            )

                            output_tokens = int(
                                attrs.get("output_tokens") or 0
                            )

                            cache_read = int(
                                attrs.get("cache_read_tokens") or 0
                            )

                            cache_creation = int(
                                attrs.get("cache_creation_tokens") or 0
                            )

                            total_tokens = (
                                input_tokens
                                + output_tokens
                                + cache_read
                                + cache_creation
                            )

                            cur.execute(
                                """
                                INSERT INTO api_requests (
                                    request_id,
                                    prompt_id,
                                    session_id,
                                    user_id,
                                    model,
                                    query_source,
                                    effort,
                                    input_tokens,
                                    output_tokens,
                                    cache_read_tokens,
                                    cache_creation_tokens,
                                    total_tokens,
                                    cost_usd,
                                    duration_ms,
                                    ttft_ms,
                                    timestamp
                                )
                                VALUES (
                                    %s, %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s
                                )
                                ON CONFLICT (request_id)
                                DO NOTHING
                                """,
                                (
                                    attrs.get("request_id"),
                                    attrs.get("prompt.id"),
                                    session_id,
                                    user_id,
                                    attrs.get("model"),
                                    attrs.get("query_source"),
                                    attrs.get("effort"),
                                    input_tokens,
                                    output_tokens,
                                    cache_read,
                                    cache_creation,
                                    total_tokens,
                                    attrs.get("cost_usd"),
                                    attrs.get("duration_ms"),
                                    attrs.get("ttft_ms"),
                                    timestamp
                                )
                            )

                        # ------------------------------------
                        # ASSISTANT RESPONSE
                        # ------------------------------------

                        elif event == "claude_code.assistant_response":

                            cur.execute(
                                """
                                INSERT INTO responses (
                                    message_uuid,
                                    prompt_id,
                                    session_id,
                                    model,
                                    response,
                                    response_length,
                                    timestamp
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (message_uuid)
                                DO NOTHING
                                """,
                                (
                                    attrs.get("message.uuid"),
                                    attrs.get("prompt.id"),
                                    session_id,
                                    attrs.get("model"),
                                    attrs.get("response"),
                                    attrs.get("response_length"),
                                    timestamp
                                )
                            )

        conn.commit()

    return {}


# ============================================================
# OTEL METRICS
# ============================================================

@app.post("/v1/metrics")
async def metrics(request: Request):

    body = await request.body()

    if request.headers.get("content-encoding") == "gzip":
        body = gzip.decompress(body)

    data = ExportMetricsServiceRequest()
    data.ParseFromString(body)

    print("\n========== METRICS ==========")

    for resource_metric in data.resource_metrics:

        for scope_metric in resource_metric.scope_metrics:

            for metric in scope_metric.metrics:

                print("\nMETRIC:", metric.name)

                data_type = metric.WhichOneof("data")

                if data_type == "sum":

                    for point in metric.sum.data_points:

                        print("\n--- DATA POINT ---")

                        for attr in point.attributes:

                            print(
                                "ATTR:",
                                attr.key,
                                "=",
                                get_attribute_value(attr.value)
                            )

                        if point.HasField("as_int"):

                            print(
                                "VALUE:",
                                point.as_int
                            )

                        elif point.HasField("as_double"):

                            print(
                                "VALUE:",
                                point.as_double
                            )

                        print(
                            "TIME:",
                            point.time_unix_nano
                        )

                elif data_type == "gauge":

                    for point in metric.gauge.data_points:

                        print("\n--- DATA POINT ---")

                        for attr in point.attributes:

                            print(
                                "ATTR:",
                                attr.key,
                                "=",
                                get_attribute_value(attr.value)
                            )

                        if point.HasField("as_int"):

                            print(
                                "VALUE:",
                                point.as_int
                            )

                        elif point.HasField("as_double"):

                            print(
                                "VALUE:",
                                point.as_double
                            )

                        print(
                            "TIME:",
                            point.time_unix_nano
                        )

    return {}


# ============================================================
# PROJECTS
# ============================================================

@app.post("/api/projects")
async def create_project(data: dict):

    name = data.get("name")
    description = data.get("description")

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Project name is required"
        )

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO projects (
                    name,
                    description
                )
                VALUES (%s, %s)
                ON CONFLICT (name)
                DO UPDATE SET
                    description = EXCLUDED.description
                RETURNING id, name, description, created_at;
                """,
                (
                    name,
                    description
                )
            )

            row = cur.fetchone()

        conn.commit()

    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "created_at": row[3]
    }


@app.get("/api/projects")
async def list_projects():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.description,
                    p.created_at,
                    COUNT(s.id) AS sessions
                FROM projects p
                LEFT JOIN sessions s
                    ON s.project_id = p.id
                GROUP BY
                    p.id,
                    p.name,
                    p.description,
                    p.created_at
                ORDER BY p.created_at DESC;
                """
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "created_at": row[3],
            "sessions": int(row[4])
        }
        for row in rows
    ]


@app.get("/api/projects/{project_id}")
async def get_project(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    name,
                    description,
                    created_at
                FROM projects
                WHERE id = %s;
                """,
                (project_id,)
            )

            row = cur.fetchone()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "created_at": row[3]
    }


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE sessions
                SET project_id = NULL
                WHERE project_id = %s;
                """,
                (project_id,)
            )

            cur.execute(
                """
                DELETE FROM projects
                WHERE id = %s
                RETURNING id;
                """,
                (project_id,)
            )

            row = cur.fetchone()

        conn.commit()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return {"id": row[0]}


# ============================================================
# ASSIGN SESSION TO PROJECT
# ============================================================

@app.post("/api/sessions/{session_id}/project")
async def assign_session_to_project(
    session_id: str,
    data: dict
):

    project_id = data.get("project_id")

    if project_id is None:

        raise HTTPException(
            status_code=400,
            detail="project_id is required"
        )

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT id
                FROM projects
                WHERE id = %s;
                """,
                (project_id,)
            )

            project = cur.fetchone()

            if not project:

                raise HTTPException(
                    status_code=404,
                    detail="Project not found"
                )

            cur.execute(
                """
                UPDATE sessions
                SET project_id = %s
                WHERE session_id = %s
                RETURNING session_id, project_id;
                """,
                (
                    project_id,
                    session_id
                )
            )

            row = cur.fetchone()

        conn.commit()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return {
        "session_id": row[0],
        "project_id": row[1]
    }


# ============================================================
# REMOVE SESSION FROM PROJECT
# ============================================================

@app.delete("/api/sessions/{session_id}/project")
async def remove_session_from_project(session_id: str):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE sessions
                SET project_id = NULL
                WHERE session_id = %s
                RETURNING session_id;
                """,
                (session_id,)
            )

            row = cur.fetchone()

        conn.commit()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return {
        "session_id": row[0],
        "project_id": None
    }


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

@app.get("/api/dashboard/summary")
async def dashboard_summary():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    COALESCE(SUM(cost_usd), 0),
                    COALESCE(SUM(input_tokens), 0),
                    COALESCE(SUM(output_tokens), 0),
                    COALESCE(SUM(cache_read_tokens), 0),
                    COALESCE(SUM(cache_creation_tokens), 0),
                    COALESCE(SUM(total_tokens), 0),
                    COUNT(*),
                    COUNT(DISTINCT prompt_id),
                    COUNT(DISTINCT user_id),
                    COUNT(DISTINCT session_id)
                FROM api_requests;
                """
            )

            row = cur.fetchone()

    return {
        "total_cost": float(row[0]),
        "input_tokens": int(row[1]),
        "output_tokens": int(row[2]),
        "cache_read_tokens": int(row[3]),
        "cache_creation_tokens": int(row[4]),
        "total_tokens": int(row[5]),
        "requests": int(row[6]),
        "prompts": int(row[7]),
        "users": int(row[8]),
        "sessions": int(row[9])
    }


# ============================================================
# TOKEN USAGE
# ============================================================

@app.get("/api/dashboard/tokens")
async def token_usage():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    DATE(timestamp) AS date,
                    SUM(input_tokens),
                    SUM(output_tokens),
                    SUM(cache_read_tokens),
                    SUM(cache_creation_tokens),
                    SUM(total_tokens)
                FROM api_requests
                WHERE timestamp IS NOT NULL
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp);
                """
            )

            rows = cur.fetchall()

    return [
        {
            "date": row[0],
            "input_tokens": int(row[1] or 0),
            "output_tokens": int(row[2] or 0),
            "cache_read_tokens": int(row[3] or 0),
            "cache_creation_tokens": int(row[4] or 0),
            "total_tokens": int(row[5] or 0)
        }
        for row in rows
    ]


# ============================================================
# COST
# ============================================================

@app.get("/api/dashboard/cost")
async def cost_usage():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    DATE(timestamp) AS date,
                    SUM(cost_usd),
                    COUNT(*)
                FROM api_requests
                WHERE timestamp IS NOT NULL
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp);
                """
            )

            rows = cur.fetchall()

    return [
        {
            "date": row[0],
            "cost": float(row[1] or 0),
            "requests": int(row[2])
        }
        for row in rows
    ]


# ============================================================
# MODEL USAGE
# ============================================================

@app.get("/api/dashboard/models")
async def model_usage():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    model,
                    COUNT(*) AS requests,
                    SUM(total_tokens) AS tokens,
                    SUM(cost_usd) AS cost,
                    AVG(duration_ms) AS avg_latency_ms,
                    AVG(ttft_ms) AS avg_ttft_ms
                FROM api_requests
                WHERE model IS NOT NULL
                GROUP BY model
                ORDER BY requests DESC;
                """
            )

            rows = cur.fetchall()

    return [
        {
            "model": row[0],
            "requests": int(row[1]),
            "tokens": int(row[2] or 0),
            "cost": float(row[3] or 0),
            "avg_latency_ms": float(row[4] or 0),
            "avg_ttft_ms": float(row[5] or 0)
        }
        for row in rows
    ]


# ============================================================
# USER USAGE
# ============================================================

@app.get("/api/dashboard/users")
async def user_usage():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    u.user_identifier,
                    COUNT(a.id) AS requests,
                    COALESCE(SUM(a.total_tokens), 0) AS tokens,
                    COALESCE(SUM(a.cost_usd), 0) AS cost,
                    COUNT(DISTINCT a.session_id) AS sessions,
                    AVG(a.duration_ms) AS avg_latency_ms
                FROM users u
                LEFT JOIN api_requests a
                    ON a.user_id = u.id
                GROUP BY
                    u.id,
                    u.user_identifier
                ORDER BY requests DESC;
                """
            )

            rows = cur.fetchall()

    return [
        {
            "user": row[0],
            "requests": int(row[1]),
            "tokens": int(row[2]),
            "cost": float(row[3]),
            "sessions": int(row[4]),
            "avg_latency_ms": float(row[5] or 0)
        }
        for row in rows
    ]


# ============================================================
# RECENT ACTIVITY
# ============================================================

@app.get("/api/dashboard/activity")
async def recent_activity():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    a.timestamp,
                    u.user_identifier,
                    a.session_id,
                    a.prompt_id,
                    a.model,
                    a.input_tokens,
                    a.output_tokens,
                    a.cache_read_tokens,
                    a.cache_creation_tokens,
                    a.total_tokens,
                    a.cost_usd,
                    a.duration_ms,
                    a.ttft_ms
                FROM api_requests a
                LEFT JOIN users u
                    ON a.user_id = u.id
                ORDER BY a.timestamp DESC
                LIMIT 100;
                """
            )

            rows = cur.fetchall()

    return [
        {
            "timestamp": row[0],
            "user": row[1],
            "session_id": row[2],
            "prompt_id": row[3],
            "model": row[4],
            "input_tokens": int(row[5] or 0),
            "output_tokens": int(row[6] or 0),
            "cache_read_tokens": int(row[7] or 0),
            "cache_creation_tokens": int(row[8] or 0),
            "total_tokens": int(row[9] or 0),
            "cost": float(row[10] or 0),
            "duration_ms": float(row[11] or 0),
            "ttft_ms": float(row[12] or 0)
        }
        for row in rows
    ]


# ============================================================
# SESSION USAGE
# ============================================================

@app.get("/api/dashboard/sessions")
async def session_usage():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    s.session_id,
                    u.user_identifier,
                    s.started_at,
                    s.last_activity_at,
                    s.project_id,
                    COUNT(a.id) AS requests,
                    COALESCE(SUM(a.total_tokens), 0) AS tokens,
                    COALESCE(SUM(a.cost_usd), 0) AS cost,
                    (
                        SELECT pr.prompt
                        FROM prompts pr
                        WHERE pr.session_id = s.session_id
                        ORDER BY pr.timestamp ASC
                        LIMIT 1
                    ) AS first_prompt
                FROM sessions s
                LEFT JOIN users u
                    ON s.user_id = u.id
                LEFT JOIN api_requests a
                    ON a.session_id = s.session_id
                GROUP BY
                    s.session_id,
                    u.user_identifier,
                    s.started_at,
                    s.last_activity_at,
                    s.project_id
                ORDER BY s.last_activity_at DESC;
                """
            )

            rows = cur.fetchall()

    return [
        {
            "session_id": row[0],
            "user": row[1],
            "started_at": row[2],
            "last_activity_at": row[3],
            "project_id": row[4],
            "requests": int(row[5]),
            "tokens": int(row[6]),
            "cost": float(row[7]),
            "first_prompt": row[8]
        }
        for row in rows
    ]


# ============================================================
# PROMPT DETAIL
# ============================================================

@app.get("/api/dashboard/prompts/{prompt_id}")
async def prompt_detail(prompt_id: str):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    prompt_id,
                    session_id,
                    prompt,
                    prompt_length,
                    timestamp
                FROM prompts
                WHERE prompt_id = %s
                ORDER BY timestamp;
                """,
                (prompt_id,)
            )

            prompt_rows = cur.fetchall()

            cur.execute(
                """
                SELECT
                    request_id,
                    model,
                    query_source,
                    effort,
                    input_tokens,
                    output_tokens,
                    cache_read_tokens,
                    cache_creation_tokens,
                    total_tokens,
                    cost_usd,
                    duration_ms,
                    ttft_ms,
                    timestamp
                FROM api_requests
                WHERE prompt_id = %s
                ORDER BY timestamp;
                """,
                (prompt_id,)
            )

            request_rows = cur.fetchall()

            cur.execute(
                """
                SELECT
                    message_uuid,
                    model,
                    response,
                    response_length,
                    timestamp
                FROM responses
                WHERE prompt_id = %s
                ORDER BY timestamp;
                """,
                (prompt_id,)
            )

            response_rows = cur.fetchall()

    if not prompt_rows:

        raise HTTPException(
            status_code=404,
            detail="Prompt not found"
        )

    return {
        "prompt": {
            "prompt_id": prompt_rows[0][0],
            "session_id": prompt_rows[0][1],
            "text": prompt_rows[0][2],
            "length": prompt_rows[0][3],
            "timestamp": prompt_rows[0][4]
        },

        "requests": [
            {
                "request_id": row[0],
                "model": row[1],
                "query_source": row[2],
                "effort": row[3],
                "input_tokens": int(row[4] or 0),
                "output_tokens": int(row[5] or 0),
                "cache_read_tokens": int(row[6] or 0),
                "cache_creation_tokens": int(row[7] or 0),
                "total_tokens": int(row[8] or 0),
                "cost": float(row[9] or 0),
                "duration_ms": float(row[10] or 0),
                "ttft_ms": float(row[11] or 0),
                "timestamp": row[12]
            }
            for row in request_rows
        ],

        "responses": [
            {
                "message_uuid": row[0],
                "model": row[1],
                "response": row[2],
                "length": row[3],
                "timestamp": row[4]
            }
            for row in response_rows
        ]
    }


# ============================================================
# PERFORMANCE
# ============================================================

@app.get("/api/dashboard/performance")
async def performance():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    COUNT(*) AS requests,
                    AVG(duration_ms),
                    MIN(duration_ms),
                    MAX(duration_ms),
                    AVG(ttft_ms),
                    MIN(ttft_ms),
                    MAX(ttft_ms)
                FROM api_requests
                WHERE duration_ms IS NOT NULL;
                """
            )

            row = cur.fetchone()

    return {
        "requests": int(row[0]),
        "avg_duration_ms": float(row[1] or 0),
        "min_duration_ms": float(row[2] or 0),
        "max_duration_ms": float(row[3] or 0),
        "avg_ttft_ms": float(row[4] or 0),
        "min_ttft_ms": float(row[5] or 0),
        "max_ttft_ms": float(row[6] or 0)
    }


# ============================================================
# PROJECT SUMMARY
# ============================================================

@app.get("/api/dashboard/projects/{project_id}/summary")
async def project_summary(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    COALESCE(SUM(a.cost_usd), 0),
                    COALESCE(SUM(a.input_tokens), 0),
                    COALESCE(SUM(a.output_tokens), 0),
                    COALESCE(SUM(a.cache_read_tokens), 0),
                    COALESCE(SUM(a.cache_creation_tokens), 0),
                    COALESCE(SUM(a.total_tokens), 0),
                    COUNT(a.id),
                    COUNT(DISTINCT a.prompt_id),
                    COUNT(DISTINCT a.user_id),
                    COUNT(DISTINCT a.session_id)
                FROM api_requests a
                JOIN sessions s
                    ON a.session_id = s.session_id
                WHERE s.project_id = %s;
                """,
                (project_id,)
            )

            row = cur.fetchone()

    return {
        "total_cost": float(row[0]),
        "input_tokens": int(row[1]),
        "output_tokens": int(row[2]),
        "cache_read_tokens": int(row[3]),
        "cache_creation_tokens": int(row[4]),
        "total_tokens": int(row[5]),
        "requests": int(row[6]),
        "prompts": int(row[7]),
        "users": int(row[8]),
        "sessions": int(row[9])
    }


# ============================================================
# PROJECT SESSIONS
# ============================================================

@app.get("/api/dashboard/projects/{project_id}/sessions")
async def project_sessions(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    s.session_id,
                    u.user_identifier,
                    s.started_at,
                    s.last_activity_at,
                    COUNT(a.id) AS requests,
                    COALESCE(SUM(a.total_tokens), 0) AS tokens,
                    COALESCE(SUM(a.cost_usd), 0) AS cost
                FROM sessions s
                LEFT JOIN users u
                    ON s.user_id = u.id
                LEFT JOIN api_requests a
                    ON a.session_id = s.session_id
                WHERE s.project_id = %s
                GROUP BY
                    s.session_id,
                    u.user_identifier,
                    s.started_at,
                    s.last_activity_at
                ORDER BY s.last_activity_at DESC;
                """
            , (project_id,))

            rows = cur.fetchall()

    return [
        {
            "session_id": row[0],
            "user": row[1],
            "started_at": row[2],
            "last_activity_at": row[3],
            "requests": int(row[4]),
            "tokens": int(row[5]),
            "cost": float(row[6])
        }
        for row in rows
    ]
# ============================================================
# PROJECT TOKEN USAGE
# ============================================================

@app.get("/api/dashboard/projects/{project_id}/tokens")
async def project_token_usage(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    DATE(a.timestamp) AS date,
                    SUM(a.input_tokens),
                    SUM(a.output_tokens),
                    SUM(a.cache_read_tokens),
                    SUM(a.cache_creation_tokens),
                    SUM(a.total_tokens)
                FROM api_requests a
                JOIN sessions s
                    ON a.session_id = s.session_id
                WHERE s.project_id = %s
                  AND a.timestamp IS NOT NULL
                GROUP BY DATE(a.timestamp)
                ORDER BY DATE(a.timestamp);
                """,
                (project_id,)
            )

            rows = cur.fetchall()

    return [
        {
            "date": row[0],
            "input_tokens": int(row[1] or 0),
            "output_tokens": int(row[2] or 0),
            "cache_read_tokens": int(row[3] or 0),
            "cache_creation_tokens": int(row[4] or 0),
            "total_tokens": int(row[5] or 0)
        }
        for row in rows
    ]


# ============================================================
# PROJECT COST
# ============================================================

@app.get("/api/dashboard/projects/{project_id}/cost")
async def project_cost_usage(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    DATE(a.timestamp) AS date,
                    SUM(a.cost_usd),
                    COUNT(a.id)
                FROM api_requests a
                JOIN sessions s
                    ON a.session_id = s.session_id
                WHERE s.project_id = %s
                  AND a.timestamp IS NOT NULL
                GROUP BY DATE(a.timestamp)
                ORDER BY DATE(a.timestamp);
                """,
                (project_id,)
            )

            rows = cur.fetchall()

    return [
        {
            "date": row[0],
            "cost": float(row[1] or 0),
            "requests": int(row[2])
        }
        for row in rows
    ]


# ============================================================
# PROJECT MODEL USAGE
# ============================================================

@app.get("/api/dashboard/projects/{project_id}/models")
async def project_model_usage(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    a.model,
                    COUNT(*) AS requests,
                    COALESCE(SUM(a.total_tokens), 0) AS tokens,
                    COALESCE(SUM(a.cost_usd), 0) AS cost,
                    AVG(a.duration_ms) AS avg_latency_ms,
                    AVG(a.ttft_ms) AS avg_ttft_ms
                FROM api_requests a
                JOIN sessions s
                    ON a.session_id = s.session_id
                WHERE s.project_id = %s
                  AND a.model IS NOT NULL
                GROUP BY a.model
                ORDER BY requests DESC;
                """,
                (project_id,)
            )

            rows = cur.fetchall()

    return [
        {
            "model": row[0],
            "requests": int(row[1]),
            "tokens": int(row[2]),
            "cost": float(row[3]),
            "avg_latency_ms": float(row[4] or 0),
            "avg_ttft_ms": float(row[5] or 0)
        }
        for row in rows
    ]


# ============================================================
# PROJECT USER USAGE
# ============================================================

@app.get("/api/dashboard/projects/{project_id}/users")
async def project_user_usage(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    u.user_identifier,
                    COUNT(a.id) AS requests,
                    COALESCE(SUM(a.total_tokens), 0) AS tokens,
                    COALESCE(SUM(a.cost_usd), 0) AS cost,
                    COUNT(DISTINCT a.session_id) AS sessions,
                    AVG(a.duration_ms) AS avg_latency_ms
                FROM users u
                JOIN api_requests a
                    ON a.user_id = u.id
                JOIN sessions s
                    ON a.session_id = s.session_id
                WHERE s.project_id = %s
                GROUP BY
                    u.id,
                    u.user_identifier
                ORDER BY requests DESC;
                """,
                (project_id,)
            )

            rows = cur.fetchall()

    return [
        {
            "user": row[0],
            "requests": int(row[1]),
            "tokens": int(row[2]),
            "cost": float(row[3]),
            "sessions": int(row[4]),
            "avg_latency_ms": float(row[5] or 0)
        }
        for row in rows
    ]


# ============================================================
# PROJECT RECENT ACTIVITY
# ============================================================

@app.get("/api/dashboard/projects/{project_id}/activity")
async def project_recent_activity(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    a.timestamp,
                    u.user_identifier,
                    a.session_id,
                    a.prompt_id,
                    a.model,
                    a.query_source,
                    a.effort,
                    a.input_tokens,
                    a.output_tokens,
                    a.cache_read_tokens,
                    a.cache_creation_tokens,
                    a.total_tokens,
                    a.cost_usd,
                    a.duration_ms,
                    a.ttft_ms
                FROM api_requests a
                LEFT JOIN users u
                    ON a.user_id = u.id
                JOIN sessions s
                    ON a.session_id = s.session_id
                WHERE s.project_id = %s
                ORDER BY a.timestamp DESC
                LIMIT 100;
                """,
                (project_id,)
            )

            rows = cur.fetchall()

    return [
        {
            "timestamp": row[0],
            "user": row[1],
            "session_id": row[2],
            "prompt_id": row[3],
            "model": row[4],
            "query_source": row[5],
            "effort": row[6],
            "input_tokens": int(row[7] or 0),
            "output_tokens": int(row[8] or 0),
            "cache_read_tokens": int(row[9] or 0),
            "cache_creation_tokens": int(row[10] or 0),
            "total_tokens": int(row[11] or 0),
            "cost": float(row[12] or 0),
            "duration_ms": float(row[13] or 0),
            "ttft_ms": float(row[14] or 0)
        }
        for row in rows
    ]


# ============================================================
# PROJECT PERFORMANCE
# ============================================================

@app.get("/api/dashboard/projects/{project_id}/performance")
async def project_performance(project_id: int):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    COUNT(*) AS requests,
                    AVG(a.duration_ms),
                    MIN(a.duration_ms),
                    MAX(a.duration_ms),
                    AVG(a.ttft_ms),
                    MIN(a.ttft_ms),
                    MAX(a.ttft_ms)
                FROM api_requests a
                JOIN sessions s
                    ON a.session_id = s.session_id
                WHERE s.project_id = %s
                  AND a.duration_ms IS NOT NULL;
                """,
                (project_id,)
            )

            row = cur.fetchone()

    return {
        "requests": int(row[0]),
        "avg_duration_ms": float(row[1] or 0),
        "min_duration_ms": float(row[2] or 0),
        "max_duration_ms": float(row[3] or 0),
        "avg_ttft_ms": float(row[4] or 0),
        "min_ttft_ms": float(row[5] or 0),
        "max_ttft_ms": float(row[6] or 0)
    }