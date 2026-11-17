#!/usr/bin/env bash
set -euo pipefail

# Resolve project root
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Step 1: create virtual environment if missing
if [[ ! -d "$ROOT/.venv" ]]; then
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/python" -m pip install --upgrade pip > /dev/null
fi
# Always install requirements
"$ROOT/.venv/bin/python" -m pip install -q -r "$ROOT/backend/requirements.txt"

# Step 2: run pytest
PYTEST_OUTPUT=$("$ROOT/.venv/bin/python" -m pytest "$ROOT/backend/tests/" -q 2>&1) || true
# Extract pass count line
PASS_LINE=$(echo "$PYTEST_OUTPUT" | grep -E "[0-9]+ passed")
if [[ -z "$PASS_LINE" ]] || echo "$PYTEST_OUTPUT" | grep -qE "([0-9]+ failed|ERROR)"; then
  echo "Pytest failed or no pass line found"
  echo "$PYTEST_OUTPUT"
  exit 1
else
  echo "$PASS_LINE"
fi

# Step 3: start uvicorn server in background
TMP_LOG=$(mktemp)
DATABASE_URL="sqlite:///$ROOT/backend/data/verify.db" \
  "$ROOT/.venv/bin/python" -m uvicorn app.main:app \
  --app-dir "$ROOT/backend" --host 127.0.0.1 --port 8000 \
  >"$TMP_LOG" 2>&1 &
SERVER_PID=$!
# Ensure server is killed on exit
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

# Wait for health endpoint (up to 30 seconds)
for i in {1..30}; do
  if curl -sf http://127.0.0.1:8000/health > /dev/null; then
    break
  fi
  sleep 1
done
if ! curl -sf http://127.0.0.1:8000/health | grep -q '"status":"ok"'; then
  echo "Server health check failed. Log tail:" >&2
  tail -n 20 "$TMP_LOG" >&2
  exit 1
fi

# Step 4: full API smoke flow
# Create session
CREATE_RESP=$(curl -s -X POST -F "resume=@$ROOT/backend/tests/fixtures/sample_resume.txt;filename=sample_resume.txt" -F "role=ai-ml-engineer" http://127.0.0.1:8000/api/sessions)
SESSION_ID=$(echo "$CREATE_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
if [[ -z "$SESSION_ID" ]]; then echo "Failed to create session"; exit 1; fi

# Get roles
curl -s -f http://127.0.0.1:8000/api/roles > /dev/null || { echo "GET /api/roles failed"; exit 1; }

# Start session
START_RESP=$(curl -s -X POST http://127.0.0.1:8000/api/sessions/$SESSION_ID/start)
QUESTION_IDS=$(echo "$START_RESP" | python3 -c "import sys, json; data=json.load(sys.stdin); print(' '.join([q['id'] for q in data.get('questions', [])]))")
if [[ -z "$QUESTION_IDS" ]]; then echo "No questions returned"; exit 1; fi

# Answer each question
ANSWER_TEXT="Gradient descent updates parameters using the negative gradient scaled by the learning rate; mini-batch is the practical standard and Adam adds momentum with adaptive rates."
for QID in $QUESTION_IDS; do
  RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "{\"question_id\": \"$QID\", \"answer_text\": \"$ANSWER_TEXT\"}" http://127.0.0.1:8000/api/sessions/$SESSION_ID/answers)
  if [[ "$RESP" != "201" ]]; then echo "Answer POST failed for $QID (status $RESP)"; exit 1; fi
done

# Complete session
COMPLETE_RESP=$(curl -s -X POST http://127.0.0.1:8000/api/sessions/$SESSION_ID/complete)
OVERALL=$(echo "$COMPLETE_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['summary'].get('overall_assessment',''))")
PER_Q=$(echo "$COMPLETE_RESP" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['summary'].get('per_question',[])))")
if [[ -z "$OVERALL" ]] || [[ "$PER_Q" -ne $(echo "$QUESTION_IDS" | wc -w) ]]; then echo "Summary validation failed"; exit 1; fi

# Get summary
curl -f -s http://127.0.0.1:8000/api/sessions/$SESSION_ID/summary > /dev/null || { echo "GET summary failed"; exit 1; }
# Get session detail and verify question count
curl -s http://127.0.0.1:8000/api/sessions/$SESSION_ID | python3 -c "import sys, json; data=json.load(sys.stdin); assert data.get('question_count')==5, 'question_count mismatch'"

# Delete session
curl -f -s -X DELETE http://127.0.0.1:8000/api/sessions/$SESSION_ID > /dev/null || { echo "DELETE session failed"; exit 1; }

echo "SMOKE OK"

# Step 5: cleanup
rm -f "$ROOT/backend/data/verify.db" "$ROOT/backend/data/verify.db-journal" "$ROOT/backend/data/verify.db-wal"

echo "VERIFY OK"
exit 0
