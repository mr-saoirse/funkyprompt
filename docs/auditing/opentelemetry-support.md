---
description: Building on the power of a standard for observability
---

# OpenTelemetry support

We believe that [OpenTelemetry](https://opentelemetry.io/) is one of the most important initiatives in tech today. Observability is become increasingly important as software ecosystems evolve and standardization is particular important here. By leveraging OpenTelemetry, funkyprompt gets a lot of powerful auditing functionality for free while also allowing for metrics, logging and traces to be exported to third party collectors.&#x20;

For example, when you run an interpreter session, metrics about the use of functions and data and the agents confidence are audited using this standard. This allows for retrospective analysis about what works and what does not without having to do any custom instrumentation.&#x20;

If you run a session e.g.

```python
import funkyprompt
#replace the question for any functions or stores you have loaded
funkyprompt.agent("what function can you use for books")
```

For free we trace the basic execution calls - a bare bones one is shown here just to illustrate how the spans are chained. We can enrich this as will be discussed below. In this case we run an interpreter session which spans a span child to invoke functions which in turn runs a vector search. You can see the shared trace id and the parent child relationships between span ids. We also shown some custom attribute on the parent i.e. the `funky_session_id`  as well as questions and store names. The `funky_session_id` will be linked to the audited agent conversation that is stored in the InterpreterSession vector store with a much richer textual representation including the agent response.

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
        "trace_id": "0xdefba26fe2f9db5d99bbf22b885a438b",
        "span_id": "0xde50e061a6a79bf5",
        "trace_state": "[]"
    },
    "kind": "SpanKind.INTERNAL",
    "parent_id": "0x781dcf57688f931a",
    "start_time": "2023-11-19T19:38:26.337120Z",
    "end_time": "2023-11-19T19:38:26.570434Z",
    "status": {
        "status_code": "UNSET"
    },
    "attributes": {
        "store_name": "default/function-registry"
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
{
    "name": "agent_invoke_function",
    "context": {
        "trace_id": "0xdefba26fe2f9db5d99bbf22b885a438b",
        "span_id": "0x781dcf57688f931a",
        "trace_state": "[]"
    },
    "kind": "SpanKind.INTERNAL",
    "parent_id": "0x61eebc7af4879ff0",
    "start_time": "2023-11-19T19:38:26.333026Z",
    "end_time": "2023-11-19T19:38:26.987353Z",
    "status": {
        "status_code": "UNSET"
    },
    "attributes": {
        "function_name": "search_functions"
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
{
    "name": "run_interpreter",
    "context": {
        "trace_id": "0xdefba26fe2f9db5d99bbf22b885a438b",
        "span_id": "0x61eebc7af4879ff0",
        "trace_state": "[]"
    },
    "kind": "SpanKind.INTERNAL",
    "parent_id": null,
    "start_time": "2023-11-19T19:38:24.374679Z",
    "end_time": "2023-11-19T19:38:33.952425Z",
    "status": {
        "status_code": "UNSET"
    },
    "attributes": {
        "funky_session_id": "fpr8CD8272BCD",
        "question": "what function can you use for books"
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

This is very powerful. As you talk to `FunkyPrompt` all these data can be collected and analyzed. For best results we show you how to set up an Observability Stack on K8s in the next section but there are some local workarounds too.&#x20;

{% hint style="info" %}
One of the top few investments we are making in FunkyPrompt is auditing. This is because we believe AI Whispering is more art than science right now and collecting data is important for turning it into science and achieving predictability.&#x20;
{% endhint %}

