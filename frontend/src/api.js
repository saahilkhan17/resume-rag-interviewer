/**
 * API client for Resume RAG Interviewer backend.
 * All functions throw a JS Error with the backend 'detail' string
 * (or sensible fallback) on non-2xx responses.
 */

async function handleResponse(response) {
  if (response.ok) {
    if (response.status === 204) {
      return null;
    }
    return response.json();
  }

  let errorMessage = `HTTP error ${response.status}: ${response.statusText || 'Request failed'}`;
  try {
    const errorData = await response.json();
    if (errorData && errorData.detail) {
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail
          .map((item) => (typeof item === 'object' && item.msg ? item.msg : String(item)))
          .join('; ');
      } else if (typeof errorData.detail === 'object') {
        errorMessage = errorData.detail.msg || JSON.stringify(errorData.detail);
      }
    } else if (errorData && errorData.message) {
      errorMessage = errorData.message;
    }
  } catch {
    try {
      const text = await response.text();
      if (text && text.trim().length > 0) {
        errorMessage = text.trim();
      }
    } catch {
      // Fallback message preserved
    }
  }

  throw new Error(errorMessage);
}

export async function getHealth() {
  const response = await fetch('/health');
  return handleResponse(response);
}

export async function getRoles() {
  const response = await fetch('/api/roles');
  return handleResponse(response);
}

export async function createSession(file, role) {
  const formData = new FormData();
  formData.append('resume', file);
  formData.append('role', role);

  const response = await fetch('/api/sessions', {
    method: 'POST',
    body: formData,
  });
  return handleResponse(response);
}

export async function getSession(id) {
  const response = await fetch(`/api/sessions/${encodeURIComponent(id)}`);
  return handleResponse(response);
}

export async function startInterview(id) {
  const response = await fetch(`/api/sessions/${encodeURIComponent(id)}/start`, {
    method: 'POST',
  });
  return handleResponse(response);
}

export async function getQuestions(id) {
  const response = await fetch(`/api/sessions/${encodeURIComponent(id)}/questions`);
  return handleResponse(response);
}

export async function submitAnswer(id, questionId, answerText) {
  const response = await fetch(`/api/sessions/${encodeURIComponent(id)}/answers`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question_id: questionId,
      answer_text: answerText,
    }),
  });
  return handleResponse(response);
}

export async function completeInterview(id) {
  const response = await fetch(`/api/sessions/${encodeURIComponent(id)}/complete`, {
    method: 'POST',
  });
  return handleResponse(response);
}

export async function getSummary(id) {
  const response = await fetch(`/api/sessions/${encodeURIComponent(id)}/summary`);
  return handleResponse(response);
}

export async function listSessions() {
  const response = await fetch('/api/sessions');
  return handleResponse(response);
}

export async function deleteSession(id) {
  const response = await fetch(`/api/sessions/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
  return handleResponse(response);
}
