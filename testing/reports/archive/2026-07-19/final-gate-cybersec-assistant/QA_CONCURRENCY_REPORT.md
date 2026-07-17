# QA concurrency report

Checked: `2026-07-18T21:38:33.550175+00:00`

| Scenario | Requests | Pass | Fail | Status |
|---|---:|---:|---:|---|
| concurrent authenticated chat creates | 20 | 20 | 0 | PASS |
| owner-isolated listing after concurrent writes | 2 | 2 | 0 | PASS |
| p95 create latency ms | 165 |  |  | PASS |

Raw results:

```json
[
  {
    "username": "qa_user_a",
    "index": 0,
    "status": 201,
    "latency_ms": 48,
    "id": "d4a139c8-a541-4d7a-a323-4852a7e32cc6",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:0",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:0",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "d4a139c8-a541-4d7a-a323-4852a7e32cc6",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.796075Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 1,
    "status": 201,
    "latency_ms": 81,
    "id": "1a570c20-390f-4ba6-bb68-712ab1e051a3",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:1",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:1",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "1a570c20-390f-4ba6-bb68-712ab1e051a3",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.809354Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 2,
    "status": 201,
    "latency_ms": 143,
    "id": "28c60a0b-e74e-4dfd-b686-f65aee4ba3ea",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:2",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:2",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "28c60a0b-e74e-4dfd-b686-f65aee4ba3ea",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.865584Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 3,
    "status": 201,
    "latency_ms": 125,
    "id": "dac4b664-1ef3-4764-83c1-def85c6dd9bc",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:3",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:3",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "dac4b664-1ef3-4764-83c1-def85c6dd9bc",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.854939Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 4,
    "status": 201,
    "latency_ms": 144,
    "id": "b7034d65-df84-41cd-807a-2a5d591bd92c",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:4",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:4",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "b7034d65-df84-41cd-807a-2a5d591bd92c",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.882909Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 5,
    "status": 201,
    "latency_ms": 153,
    "id": "c6fa4eb9-7166-41fb-9f87-e42056484a9b",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:5",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:5",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "c6fa4eb9-7166-41fb-9f87-e42056484a9b",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.894248Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 6,
    "status": 201,
    "latency_ms": 158,
    "id": "7830d563-ed54-4bc3-ac7a-499fe0f03892",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:6",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:6",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "7830d563-ed54-4bc3-ac7a-499fe0f03892",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.918110Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 7,
    "status": 201,
    "latency_ms": 163,
    "id": "4b022e52-f160-426d-badc-686386bb3cd9",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:7",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:7",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "4b022e52-f160-426d-badc-686386bb3cd9",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.926695Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 8,
    "status": 201,
    "latency_ms": 178,
    "id": "b82fb0d0-0930-4f06-85a4-4ebea47d12b7",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:8",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:8",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "b82fb0d0-0930-4f06-85a4-4ebea47d12b7",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.959624Z"
    }
  },
  {
    "username": "qa_user_a",
    "index": 9,
    "status": 201,
    "latency_ms": 159,
    "id": "976045c1-2bc4-46a3-a06d-38c7a235247c",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_a:message:9",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_a:response:9",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "976045c1-2bc4-46a3-a06d-38c7a235247c",
      "user_id": "1df03f07-c4e7-43d1-af69-425b537f552e",
      "created_at": "2026-07-18T21:38:32.938459Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 0,
    "status": 201,
    "latency_ms": 165,
    "id": "6efc8b75-9c42-4e1e-b271-a2289d2ffc59",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:0",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:0",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "6efc8b75-9c42-4e1e-b271-a2289d2ffc59",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:32.950281Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 1,
    "status": 201,
    "latency_ms": 145,
    "id": "bb3a9c41-2452-4292-ba99-0fdc76be52d7",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:1",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:1",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "bb3a9c41-2452-4292-ba99-0fdc76be52d7",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:32.972065Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 2,
    "status": 201,
    "latency_ms": 142,
    "id": "4e661486-510c-4d34-94a4-22d6fb9cb93a",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:2",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:2",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "4e661486-510c-4d34-94a4-22d6fb9cb93a",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:32.997031Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 3,
    "status": 201,
    "latency_ms": 139,
    "id": "0a6692a7-5f05-443a-b4dd-a0d70fefd471",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:3",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:3",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "0a6692a7-5f05-443a-b4dd-a0d70fefd471",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:33.012852Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 4,
    "status": 201,
    "latency_ms": 138,
    "id": "1f3b9061-ad5a-4728-b4d8-602e9a2a8b0e",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:4",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:4",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "1f3b9061-ad5a-4728-b4d8-602e9a2a8b0e",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:33.023346Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 5,
    "status": 201,
    "latency_ms": 137,
    "id": "8508e01a-c66c-4a10-b08b-274e1782994d",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:5",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:5",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "8508e01a-c66c-4a10-b08b-274e1782994d",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:33.044489Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 6,
    "status": 201,
    "latency_ms": 134,
    "id": "671ae5d6-47f6-42cb-b4a1-60bba3cbc75b",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:6",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:6",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "671ae5d6-47f6-42cb-b4a1-60bba3cbc75b",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:33.058339Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 7,
    "status": 201,
    "latency_ms": 126,
    "id": "110db599-07ba-4ad0-a5f0-93e655e96a7b",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:7",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:7",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "110db599-07ba-4ad0-a5f0-93e655e96a7b",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:33.067452Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 8,
    "status": 201,
    "latency_ms": 115,
    "id": "4397a7b0-8a57-4ec0-a41d-6653ca522fb8",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:8",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:8",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "4397a7b0-8a57-4ec0-a41d-6653ca522fb8",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:33.076426Z"
    }
  },
  {
    "username": "qa_user_b",
    "index": 9,
    "status": 201,
    "latency_ms": 108,
    "id": "378db53e-c453-4d8c-a68c-63150e1201d2",
    "body": {
      "user_message": "qa-concurrency-88688706dcce:qa_user_b:message:9",
      "bot_response": "qa-concurrency-88688706dcce:qa_user_b:response:9",
      "intent": "qa_concurrency",
      "entities": null,
      "id": "378db53e-c453-4d8c-a68c-63150e1201d2",
      "user_id": "407754bc-a225-47d1-9552-c5c8fba31d3a",
      "created_at": "2026-07-18T21:38:33.086656Z"
    }
  }
]
```
