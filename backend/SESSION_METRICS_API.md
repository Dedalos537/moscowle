# SessionMetrics API Documentation

## Overview
The SessionMetrics API manages performance metrics for therapeutic game sessions. It tracks student performance data including accuracy, timing, failed attempts, and level progression for Machine Learning analysis.

## Base URL
```
/api/session-metrics
```

## Authentication
All endpoints require JWT Bearer token authentication.

**Header**: `Authorization: Bearer {access_token}`

---

## Endpoints

### 1. Get All Session Metrics
**GET** `/api/session-metrics/`

Get all session metrics with optional filtering and pagination.

**Query Parameters:**
- `patient_id` (integer, optional): Filter by patient ID
- `game_name` (string, optional): Filter by game name (supports partial matching)
- `limit` (integer, default: 50): Number of records to return
- `offset` (integer, default: 0): Number of records to skip

**Response (200):**
```json
{
  "data": [
    {
      "id": 1,
      "patient_id": 5,
      "game_name": "Memory Match",
      "accuracy_rate": 87.5,
      "average_time": 2.3,
      "failed_attempts": 2,
      "previous_level": 2,
      "predicted_next_level": 3,
      "cluster_id": 1,
      "created_at": "2025-12-03T10:30:00"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

---

### 2. Get Specific Session Metric
**GET** `/api/session-metrics/{metric_id}`

Get details of a specific session metric.

**Path Parameters:**
- `metric_id` (integer, required): ID of the session metric

**Response (200):**
```json
{
  "id": 1,
  "patient_id": 5,
  "game_name": "Memory Match",
  "accuracy_rate": 87.5,
  "average_time": 2.3,
  "failed_attempts": 2,
  "previous_level": 2,
  "predicted_next_level": 3,
  "cluster_id": 1,
  "created_at": "2025-12-03T10:30:00"
}
```

**Response (404):**
```json
{"msg": "Session metric not found"}
```

---

### 3. Get Patient Metrics
**GET** `/api/session-metrics/patient/{patient_id}`

Get all metrics for a specific patient.

**Path Parameters:**
- `patient_id` (integer, required): ID of the patient

**Query Parameters:**
- `limit` (integer, default: 100): Number of records to return
- `offset` (integer, default: 0): Number of records to skip

**Response (200):**
```json
{
  "data": [
    {
      "id": 1,
      "patient_id": 5,
      "game_name": "Memory Match",
      "accuracy_rate": 87.5,
      "average_time": 2.3,
      "failed_attempts": 2,
      "previous_level": 2,
      "predicted_next_level": 3,
      "cluster_id": 1,
      "created_at": "2025-12-03T10:30:00"
    }
  ],
  "total": 25,
  "patient_id": 5,
  "limit": 100,
  "offset": 0
}
```

---

### 4. Create Session Metric
**POST** `/api/session-metrics/`

Create a new session metric record.

**Request Body:**
```json
{
  "patient_id": 5,
  "game_name": "Memory Match",
  "accuracy_rate": 87.5,
  "average_time": 2.3,
  "failed_attempts": 2,
  "previous_level": 2,
  "predicted_next_level": 3,
  "cluster_id": 1
}
```

**Field Validation:**
- `patient_id` (required): Integer, must exist in patients table
- `game_name` (required): String, 1-255 characters
- `accuracy_rate` (required): Float, 0-100
- `average_time` (required): Float, >= 0
- `failed_attempts` (required): Integer, >= 0
- `previous_level` (required): Integer, 1-3
- `predicted_next_level` (optional): Integer, 0-3 or null
- `cluster_id` (optional): Integer, >= 0 or null

**Response (201):**
```json
{
  "id": 1,
  "patient_id": 5,
  "game_name": "Memory Match",
  "accuracy_rate": 87.5,
  "average_time": 2.3,
  "failed_attempts": 2,
  "previous_level": 2,
  "predicted_next_level": 3,
  "cluster_id": 1,
  "created_at": "2025-12-03T10:30:00"
}
```

**Response (400):**
```json
{
  "msg": "Validation failed",
  "errors": {
    "accuracy_rate": ["Must be between 0 and 100"]
  }
}
```

**Response (404):**
```json
{"msg": "Patient with id 5 not found"}
```

---

### 5. Update Session Metric
**PUT** `/api/session-metrics/{metric_id}`

Update an existing session metric.

**Path Parameters:**
- `metric_id` (integer, required): ID of the session metric

**Request Body:** (all fields optional)
```json
{
  "accuracy_rate": 92.3,
  "average_time": 2.1,
  "failed_attempts": 1,
  "predicted_next_level": 3,
  "cluster_id": 2
}
```

**Response (200):**
```json
{
  "id": 1,
  "patient_id": 5,
  "game_name": "Memory Match",
  "accuracy_rate": 92.3,
  "average_time": 2.1,
  "failed_attempts": 1,
  "previous_level": 2,
  "predicted_next_level": 3,
  "cluster_id": 2,
  "created_at": "2025-12-03T10:30:00"
}
```

---

### 6. Delete Session Metric
**DELETE** `/api/session-metrics/{metric_id}`

Delete a session metric record.

**Path Parameters:**
- `metric_id` (integer, required): ID of the session metric

**Response (200):**
```json
{"msg": "Session metric deleted successfully"}
```

**Response (404):**
```json
{"msg": "Session metric not found"}
```

---

### 7. Get Patient Metrics Summary
**GET** `/api/session-metrics/patient/{patient_id}/summary`

Get aggregated metrics summary for a patient across all games.

**Path Parameters:**
- `patient_id` (integer, required): ID of the patient

**Response (200):**
```json
{
  "patient_id": 5,
  "total_sessions": 25,
  "games_played": ["Memory Match", "Shape Sorting", "Puzzle Builder"],
  "summary": {
    "Memory Match": {
      "count": 10,
      "avg_accuracy": 84.3,
      "avg_time": 2.45,
      "total_failed": 15,
      "levels": [1, 2, 3],
      "clusters": [1, 2]
    },
    "Shape Sorting": {
      "count": 8,
      "avg_accuracy": 91.2,
      "avg_time": 1.8,
      "total_failed": 5,
      "levels": [2, 3],
      "clusters": [2]
    }
  }
}
```

**Response (404):**
```json
{"msg": "No metrics found for this patient"}
```

---

## Field Descriptions

### Performance Metrics
- **accuracy_rate**: Percentage of correct answers (0-100)
- **average_time**: Average time per attempt in seconds
- **failed_attempts**: Total number of failed attempts in session

### Level System
- **previous_level**: Current difficulty level (1=Easy, 2=Medium, 3=Hard)
- **predicted_next_level**: ML-predicted next level (0=Maintain, 1=Easy, 2=Medium, 3=Hard)

### Machine Learning
- **cluster_id**: K-Means cluster assignment for student grouping
  - Used to identify learning patterns
  - Can be recalculated by ML pipeline
  - NULL if not yet assigned

---

## Database Schema

```sql
CREATE TABLE session_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    game_name VARCHAR(255) NOT NULL,
    accuracy_rate FLOAT DEFAULT 0.0,
    average_time FLOAT DEFAULT 0.0,
    failed_attempts INT DEFAULT 0,
    previous_level INT DEFAULT 1,
    predicted_next_level INT,
    cluster_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    INDEX idx_patient_id (patient_id),
    INDEX idx_game_name (game_name),
    INDEX idx_created_at (created_at),
    INDEX idx_patient_game (patient_id, game_name),
    INDEX idx_cluster_date (cluster_id, created_at)
);
```

---

## Example Usage

### Create a session metric after game completion
```bash
curl -X POST http://localhost:5001/api/session-metrics/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 5,
    "game_name": "Memory Match",
    "accuracy_rate": 87.5,
    "average_time": 2.3,
    "failed_attempts": 2,
    "previous_level": 2,
    "predicted_next_level": 3
  }'
```

### Get all metrics for a patient
```bash
curl http://localhost:5001/api/session-metrics/patient/5 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get patient metrics summary for ML analysis
```bash
curl http://localhost:5001/api/session-metrics/patient/5/summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update metric with ML cluster assignment
```bash
curl -X PUT http://localhost:5001/api/session-metrics/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cluster_id": 2}'
```

---

## Error Handling

All endpoints return standard error responses:

```json
{
  "msg": "Error description",
  "errors": {}  // Optional: validation errors
}
```

**Common Status Codes:**
- `200`: Success
- `201`: Resource created
- `400`: Validation error
- `401`: Unauthorized (missing/invalid token)
- `404`: Resource not found
- `500`: Server error

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- Pagination uses limit/offset pattern (not cursor-based)
- Cascade delete: Deleting a patient removes all their metrics
- The `predicted_next_level` is typically set by ML pipeline, not user input
- For performance queries with many records, use filters and pagination
