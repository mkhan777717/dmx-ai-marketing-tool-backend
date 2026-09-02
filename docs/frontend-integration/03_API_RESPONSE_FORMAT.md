# API Response Format

## Overview

The backend follows a standardized response structure across all APIs using the generic `ApiResponse<T>` schema.

All successful responses return the following JSON format:

```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": {},
  "meta": {}
}
```

---

## Success Response

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Indicates whether the request was successful. Always `true`. |
| message | string | Human-readable response message. |
| data | object / array | Actual response payload. |
| meta | object | Optional metadata (pagination or additional information). Defaults to an empty object. |

Example:

```json
{
  "success": true,
  "message": "Campaign created successfully.",
  "data": {
    "id": "...",
    "name": "Summer Campaign"
  },
  "meta": {}
}
```

---

## Error Response

Failed requests return the following structure:

```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": [
    {
      "field": "name",
      "message": "This field is required."
    }
  ]
}
```

---

## Error Response Fields

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Always `false`. |
| message | string | Error summary. |
| errors | array | Optional list containing validation or business errors. |

---

## Frontend Integration Notes

- Always check the `success` field before processing the response.
- Use the `message` field to display user-friendly notifications.
- Read all API payloads from the `data` object.
- Treat the `meta` object as optional.
- Handle the `errors` array when present to display validation messages.

---

## Standard Response Flow

```
Request
      │
      ▼
Backend API
      │
      ▼
ApiResponse<T>
      │
      ├── success
      ├── message
      ├── data
      └── meta
```

---

## Current Backend Standard

All newly updated backend endpoints follow this standardized `ApiResponse<T>` contract to maintain consistent frontend integration and response handling.