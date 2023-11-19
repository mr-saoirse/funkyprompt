---
description: Building on the power of a standard for observability
---

# Open Telemetry

We believe that [OpenTelemetry](https://opentelemetry.io/) is one of the most important initiatives in tech today. Observability is become increasingly important as software ecosystems evolve and standardization is particular important here. By leveraging OpenTelemetry, funkyprompt gets a lot of powerful auditing functionality for free while also allowing for metrics, logging and traces to be exported to third party collectors.&#x20;

For example, when you run an interpreter session, metrics about the use of functions and data and the agents confidence are audited using this standard. This allows for retrospective analysis about what works and what does not without having to do any custom instrumentation.&#x20;

If you run a session e.g.

```python
import funkyprompt
#replace the question for any functions or stores you have loaded
funkyprompt.agent("what function can you used for books")
```

For free we trace the basic execution calls - a bare bones one is shown here just to illustrate how the spans are chained. We can enrich this as weill be discussed below. In this case we run an interpreter session which spans a span child to invoke functions which in turn runs a vector search. You can see the shared trace id and the parent child relationships between span ids. We also shown one custom attribute on the parent i.e. the `funky_session_id` and this will be linked to the audited agent conversation (that is stored in the InterpreterSession vector store).

```python
#the default beahviour is to wait a long time using the console logger
#and then flush it at the end
#at scale these events would be sent to the configured exporters e.g. on K8s
funkyprompt.tracer.span_processor.force_flush()
```

```json
{
    "name": "vector_store_search",
    "context": {
        "trace_id": "0x88ddebf14b68fd1f6586f6b810f8a102",
        "span_id": "0xb11e8e26816a6d6a",
        "trace_state": "[]"
    },
    "kind": "SpanKind.INTERNAL",
    "parent_id": "0x86086836e78fdf2a",
    "start_time": "2023-11-19T19:03:53.597995Z",
    "end_time": "2023-11-19T19:03:53.843412Z",
    "status": {
        "status_code": "UNSET"
    },
    "attributes": {},
    "events": [],
    "links": [],
    "resource": {
        "attributes": {
            "service.name": "funkyprompt"
        },
        "schema_url": ""
    }
}
{
    "name": "agent_invoke_function",
    "context": {
        "trace_id": "0x88ddebf14b68fd1f6586f6b810f8a102",
        "span_id": "0x86086836e78fdf2a",
        "trace_state": "[]"
    },
    "kind": "SpanKind.INTERNAL",
    "parent_id": "0xcfa5321ce149d686",
    "start_time": "2023-11-19T19:03:53.594418Z",
    "end_time": "2023-11-19T19:03:54.321380Z",
    "status": {
        "status_code": "UNSET"
    },
    "attributes": {},
    "events": [],
    "links": [],
    "resource": {
        "attributes": {
            "service.name": "funkyprompt"
        },
        "schema_url": ""
    }
}
{
    "name": "run_interpreter",
    "context": {
        "trace_id": "0x88ddebf14b68fd1f6586f6b810f8a102",
        "span_id": "0xcfa5321ce149d686",
        "trace_state": "[]"
    },
    "kind": "SpanKind.INTERNAL",
    "parent_id": null,
    "start_time": "2023-11-19T19:03:50.330146Z",
    "end_time": "2023-11-19T19:04:09.089549Z",
    "status": {
        "status_code": "UNSET"
    },
    "attributes": {
        "funky_session_id": "fprF01DBB604F"
    },
    "events": [],
    "links": [],
    "resource": {
        "attributes": {
            "service.name": "funkyprompt"
        },
        "schema_url": ""
    }
}
```

This is very powerful. As you talk to FunkyPrompt all these data can be collected and analyzed. For best results we show you how to set up on Observability Stack but there are some local testing work arounds too.&#x20;

{% hint style="info" %}
One of the top few investments we are making in FunkyPrompt is auditing. This is because we believe AI Whispering is more art than science right now and collecting data is important for turning it into science and achieving predictability.&#x20;
{% endhint %}

