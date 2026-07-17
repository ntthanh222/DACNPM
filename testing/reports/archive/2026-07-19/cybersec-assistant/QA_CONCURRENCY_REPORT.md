# QA concurrency report

Checked: `2026-07-18T21:03:22.557478+00:00`

| Scenario | Requests | Pass | Fail | Status |
|---|---:|---:|---:|---|
| concurrent authenticated chat creates | 20 | 20 | 0 | PASS |
| owner-isolated listing after concurrent writes | 2 | 2 | 0 | PASS |
| p95 create latency ms | 127 |  |  | PASS |

Raw results:

```json
[
  {
    "username": "qa_user_a",
    "index": 0,
    "status": 201,
    "latency_ms": 28,
    "id": "e55177c1-a6b8-46ad-b370-3ffafdda9960",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:0",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:0",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "e55177c1-a6b8-46ad-b370-3ffafdda9960",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.019104Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 1,
    "status": 201,
    "latency_ms": 38,
    "id": "170d954c-10b1-4778-ab51-32ff333116e9",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:1",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:1",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "170d954c-10b1-4778-ab51-32ff333116e9",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.032463Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 2,
    "status": 201,
    "latency_ms": 99,
    "id": "f453532c-9839-47ad-b1bb-05a0d3a17e0c",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:2",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:2",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "f453532c-9839-47ad-b1bb-05a0d3a17e0c",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.067842Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 3,
    "status": 201,
    "latency_ms": 77,
    "id": "c45391b4-cdeb-4326-9897-7c92dce308cc",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:3",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:3",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "c45391b4-cdeb-4326-9897-7c92dce308cc",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.052644Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 4,
    "status": 201,
    "latency_ms": 86,
    "id": "63e8e320-8b15-444e-b768-06d18fb4c48a",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:4",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:4",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "63e8e320-8b15-444e-b768-06d18fb4c48a",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.059005Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 5,
    "status": 201,
    "latency_ms": 102,
    "id": "b06a1557-39eb-4477-bb76-f4a82ce92231",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:5",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:5",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "b06a1557-39eb-4477-bb76-f4a82ce92231",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.076351Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 6,
    "status": 201,
    "latency_ms": 109,
    "id": "1e3e617b-6c0a-4406-9556-dc868a1c4bc4",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:6",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:6",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "1e3e617b-6c0a-4406-9556-dc868a1c4bc4",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.088110Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 7,
    "status": 201,
    "latency_ms": 127,
    "id": "26d2b69a-6a81-4166-a119-a66ec7bdccbc",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:7",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:7",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "26d2b69a-6a81-4166-a119-a66ec7bdccbc",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.116269Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 8,
    "status": 201,
    "latency_ms": 113,
    "id": "1b1bde78-5d3c-4460-8703-6d58a3d3789b",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:8",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:8",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "1b1bde78-5d3c-4460-8703-6d58a3d3789b",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.097086Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 9,
    "status": 201,
    "latency_ms": 134,
    "id": "cf0d72db-17e4-4b7f-a11d-b6ae0108fac6",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_a:message:9",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_a:response:9",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "cf0d72db-17e4-4b7f-a11d-b6ae0108fac6",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:03:22.126450Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 0,
    "status": 201,
    "latency_ms": 111,
    "id": "62aa527f-905a-406d-9b0c-58ab853c1ef5",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:0",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:0",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "62aa527f-905a-406d-9b0c-58ab853c1ef5",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.107872Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 1,
    "status": 201,
    "latency_ms": 122,
    "id": "c129e032-623a-4da7-a68c-75231b51b07e",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:1",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:1",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "c129e032-623a-4da7-a68c-75231b51b07e",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.135018Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 2,
    "status": 201,
    "latency_ms": 96,
    "id": "1f21e267-4144-470e-90c3-74eb4748a14e",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:2",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:2",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "1f21e267-4144-470e-90c3-74eb4748a14e",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.149641Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 3,
    "status": 201,
    "latency_ms": 96,
    "id": "f8be6036-b87d-488e-8867-4cf871593dd5",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:3",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:3",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "f8be6036-b87d-488e-8867-4cf871593dd5",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.158370Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 4,
    "status": 201,
    "latency_ms": 92,
    "id": "df5b16c9-bc9f-49f7-b64a-1288cac94257",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:4",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:4",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "df5b16c9-bc9f-49f7-b64a-1288cac94257",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.167253Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 5,
    "status": 201,
    "latency_ms": 84,
    "id": "68a77c71-9b0f-4259-bb1d-2298e1227e8b",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:5",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:5",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "68a77c71-9b0f-4259-bb1d-2298e1227e8b",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.175182Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 6,
    "status": 201,
    "latency_ms": 81,
    "id": "1aafbd02-5436-498c-b606-56dd10bace30",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:6",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:6",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "1aafbd02-5436-498c-b606-56dd10bace30",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.184583Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 7,
    "status": 201,
    "latency_ms": 79,
    "id": "a935dda0-a4f0-460b-b6b6-cf638290c1ef",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:7",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:7",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "a935dda0-a4f0-460b-b6b6-cf638290c1ef",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.193966Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 8,
    "status": 201,
    "latency_ms": 74,
    "id": "b004675a-a1fe-44c2-8389-df3bd456a849",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:8",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:8",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "b004675a-a1fe-44c2-8389-df3bd456a849",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.202196Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 9,
    "status": 201,
    "latency_ms": 69,
    "id": "45d21a80-df0c-4824-a0a2-ec08111a3440",
    "body": {
      "user_message": "qa-concurrency-bb769a64829d:qa_user_b:message:9",
      "bot_response": "qa-concurrency-bb769a64829d:qa_user_b:response:9",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "45d21a80-df0c-4824-a0a2-ec08111a3440",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:03:22.207070Z"
    }
  }
]
```
