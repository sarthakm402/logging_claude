
from fastapi import FastAPI, Request
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
import gzip


app = FastAPI()


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


@app.post("/v1/logs")
async def logs(request: Request):

    body = await request.body()

    if request.headers.get("content-encoding") == "gzip":
        body = gzip.decompress(body)

    data = ExportLogsServiceRequest()
    data.ParseFromString(body)

    print("\n========== LOGS ==========")

    events_seen = set()

    for resource_log in data.resource_logs:

        for scope_log in resource_log.scope_logs:

            for record in scope_log.log_records:

                if not record.body.HasField("string_value"):
                    continue

                event = record.body.string_value

                events_seen.add(event)

                attrs = get_attributes(record)

                if event == "claude_code.user_prompt":

                    print("\n========== USER PROMPT ==========")

                    print("Timestamp :", attrs.get("event.timestamp"))
                    print("Session   :", attrs.get("session.id"))
                    print("Prompt ID :", attrs.get("prompt.id"))
                    print("Message ID:", attrs.get("message.uuid"))
                    print("Length    :", attrs.get("prompt_length"))
                    print("Prompt    :", attrs.get("prompt"))

                elif event == "claude_code.api_request":

                    print("\n========== API REQUEST ==========")

                    print("Timestamp           :", attrs.get("event.timestamp"))
                    print("Session             :", attrs.get("session.id"))
                    print("Prompt ID           :", attrs.get("prompt.id"))
                    print("Request ID          :", attrs.get("request_id"))
                    print("Model               :", attrs.get("model"))
                    print("Input tokens        :", attrs.get("input_tokens"))
                    print("Output tokens       :", attrs.get("output_tokens"))
                    print("Cache read tokens   :", attrs.get("cache_read_tokens"))
                    print("Cache creation      :", attrs.get("cache_creation_tokens"))
                    print("Cost USD             :", attrs.get("cost_usd"))
                    print("Duration ms          :", attrs.get("duration_ms"))
                    print("TTFT ms              :", attrs.get("ttft_ms"))

                elif event == "claude_code.assistant_response":

                    print("\n========== ASSISTANT RESPONSE ==========")

                    print("Timestamp :", attrs.get("event.timestamp"))
                    print("Session   :", attrs.get("session.id"))
                    print("Prompt ID :", attrs.get("prompt.id"))
                    print("Message ID:", attrs.get("message.uuid"))
                    print("Model     :", attrs.get("model"))
                    print("Length    :", attrs.get("response_length"))
                    print("Response  :", attrs.get("response"))

    print("\n========== EVENTS SEEN ==========")

    for event in sorted(events_seen):
        print(event)

    return {}


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
                            print("VALUE:", point.as_int)

                        elif point.HasField("as_double"):
                            print("VALUE:", point.as_double)

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
                            print("VALUE:", point.as_int)

                        elif point.HasField("as_double"):
                            print("VALUE:", point.as_double)

                        print(
                            "TIME:",
                            point.time_unix_nano
                        )

    return {}
