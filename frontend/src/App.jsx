import { useState, useEffect, useMemo } from 'react'
import {
  getHealth,
  getRoles,
  createSession,
  getSession,
  startInterview,
  getQuestions,
  submitAnswer,
  completeInterview,
  getSummary,
  listSessions,
  deleteSession,
} from './api'
import './App.css'

export default function App() {
  // Navigation / stage state: 'upload' | 'interview' | 'results'
  const [stage, setStage] = useState('upload')

  // Error and loading state
  const [errorMessage, setErrorMessage] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingAction, setLoadingAction] = useState('')

  // Backend connection health
  const [backendHealthy, setBackendHealthy] = useState(null)

  // Stage 1: Upload & role selection
  const [roles, setRoles] = useState([])
  const [rolesLoading, setRolesLoading] = useState(true)
  const [selectedRole, setSelectedRole] = useState('')
  const [file, setFile] = useState(null)
  const [fileError, setFileError] = useState(null)
  const [session, setSession] = useState(null)

  // Stage 2: Interview questions & answers
  const [questions, setQuestions] = useState([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [savedQuestions, setSavedQuestions] = useState({})

  // Stage 3: Results summary
  const [summary, setSummary] = useState(null)

  // Past sessions drawer / history
  const [pastSessions, setPastSessions] = useState([])
  const [showPastSessions, setShowPastSessions] = useState(false)
  const [pastSessionsLoading, setPastSessionsLoading] = useState(false)

  // Fetch health and roles on mount
  useEffect(() => {
    let ignore = false

    async function loadInitialData() {
      try {
        const [healthRes, rolesRes] = await Promise.allSettled([
          getHealth(),
          getRoles(),
        ])

        if (ignore) return

        if (healthRes.status === 'fulfilled') {
          setBackendHealthy(true)
        } else {
          setBackendHealthy(false)
        }

        if (rolesRes.status === 'fulfilled') {
          const fetchedRoles = rolesRes.value || []
          setRoles(fetchedRoles)
          if (fetchedRoles.length > 0) {
            setSelectedRole((prev) => prev || fetchedRoles[0].id)
          }
        } else {
          throw rolesRes.reason
        }
      } catch (err) {
        if (!ignore) {
          setErrorMessage(
            err.message || 'Unable to connect to backend server on http://localhost:8000'
          )
        }
      } finally {
        if (!ignore) {
          setRolesLoading(false)
        }
      }
    }

    loadInitialData()

    return () => {
      ignore = true
    }
  }, [])

  // Retry loading roles manual trigger
  const handleRetryRoles = async () => {
    setRolesLoading(true)
    setErrorMessage(null)
    try {
      const [healthRes, rolesRes] = await Promise.allSettled([
        getHealth(),
        getRoles(),
      ])
      setBackendHealthy(healthRes.status === 'fulfilled')
      if (rolesRes.status === 'fulfilled') {
        const fetchedRoles = rolesRes.value || []
        setRoles(fetchedRoles)
        if (fetchedRoles.length > 0 && !selectedRole) {
          setSelectedRole(fetchedRoles[0].id)
        }
      } else {
        throw rolesRes.reason
      }
    } catch (err) {
      setErrorMessage(
        err.message || 'Unable to connect to backend server on http://localhost:8000'
      )
    } finally {
      setRolesLoading(false)
    }
  }

  // File picker handler with client-side extension validation (.pdf, .txt, .md only)
  const handleFileChange = (e) => {
    const selected = e.target.files?.[0]
    if (!selected) {
      setFile(null)
      return
    }

    const extMatch = selected.name.match(/\.[^.]+$/)
    const ext = extMatch ? extMatch[0].toLowerCase() : ''
    const allowed = ['.pdf', '.txt', '.md']

    if (!allowed.includes(ext)) {
      setFile(null)
      setFileError(
        `Invalid file type "${ext || 'none'}". Only .pdf, .txt, and .md files are allowed.`
      )
      return
    }

    setFileError(null)
    setFile(selected)
  }

  // Format file size nicely
  const formatFileSize = (bytes) => {
    if (bytes === undefined || bytes === null) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  // Stage 1: Upload resume & create session
  const handleCreateSession = async (e) => {
    e.preventDefault()
    if (!file) {
      setFileError('Please select a resume file (.pdf, .txt, or .md).')
      return
    }
    if (!selectedRole) {
      setErrorMessage('Please select a target role.')
      return
    }

    setLoading(true)
    setLoadingAction('Parsing resume and creating interview session...')
    setErrorMessage(null)

    try {
      const res = await createSession(file, selectedRole)
      setSession(res)
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create session')
    } finally {
      setLoading(false)
      setLoadingAction('')
    }
  }

  // Stage 1 -> Stage 2: Start Interview
  const handleStartInterview = async () => {
    if (!session?.session_id) return

    setLoading(true)
    setLoadingAction('Generating RAG-grounded interview questions...')
    setErrorMessage(null)

    try {
      const res = await startInterview(session.session_id)
      let qs = res?.questions
      if (!qs || qs.length === 0) {
        qs = await getQuestions(session.session_id)
      }
      setQuestions(qs || [])
      setCurrentQuestionIndex(0)
      setAnswers({})
      setSavedQuestions({})
      setStage('interview')
    } catch (err) {
      setErrorMessage(err.message || 'Failed to start interview')
    } finally {
      setLoading(false)
      setLoadingAction('')
    }
  }

  // Current question object
  const currentQuestion = questions[currentQuestionIndex]

  // Extract combined source chunks from source_chunks and trace.chunk_ids
  const currentSourceChunks = useMemo(() => {
    if (!currentQuestion) return []
    const fromSource = Array.isArray(currentQuestion.source_chunks)
      ? currentQuestion.source_chunks
      : []
    const fromTrace = Array.isArray(currentQuestion.trace?.chunk_ids)
      ? currentQuestion.trace.chunk_ids
      : []
    return Array.from(new Set([...fromSource, ...fromTrace])).filter(Boolean)
  }, [currentQuestion])

  // Answer change handler
  const handleAnswerChange = (val) => {
    if (!currentQuestion) return
    setAnswers((prev) => ({
      ...prev,
      [currentQuestion.id]: val,
    }))
  }

  // Stage 2: Save answer (and optionally advance to next question)
  const handleSaveAnswer = async (advanceNext = false) => {
    if (!session?.session_id || !currentQuestion) return

    const currentText = answers[currentQuestion.id] || ''
    setLoading(true)
    setLoadingAction('Saving your answer...')
    setErrorMessage(null)

    try {
      await submitAnswer(session.session_id, currentQuestion.id, currentText)
      setSavedQuestions((prev) => ({
        ...prev,
        [currentQuestion.id]: true,
      }))

      if (advanceNext && currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex((prev) => prev + 1)
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to save answer')
    } finally {
      setLoading(false)
      setLoadingAction('')
    }
  }

  // Stage 2 -> Stage 3: Finish interview and fetch summary
  const handleFinishInterview = async () => {
    if (!session?.session_id) return

    setLoading(true)
    setLoadingAction('Evaluating interview responses & generating summary...')
    setErrorMessage(null)

    try {
      // If current question has unsaved text, submit it first
      if (currentQuestion && answers[currentQuestion.id] && !savedQuestions[currentQuestion.id]) {
        await submitAnswer(session.session_id, currentQuestion.id, answers[currentQuestion.id])
        setSavedQuestions((prev) => ({
          ...prev,
          [currentQuestion.id]: true,
        }))
      }

      const res = await completeInterview(session.session_id)
      let summaryData = res?.summary
      if (!summaryData) {
        summaryData = await getSummary(session.session_id)
      }
      setSummary(summaryData)
      setStage('results')
    } catch (err) {
      setErrorMessage(err.message || 'Failed to finish interview and get summary')
    } finally {
      setLoading(false)
      setLoadingAction('')
    }
  }

  // Reset all state back to stage 1
  const handleStartNewSession = () => {
    setStage('upload')
    setSession(null)
    setFile(null)
    setFileError(null)
    setQuestions([])
    setCurrentQuestionIndex(0)
    setAnswers({})
    setSavedQuestions({})
    setSummary(null)
    setErrorMessage(null)
  }

  // Load past sessions list
  const handleTogglePastSessions = async () => {
    if (showPastSessions) {
      setShowPastSessions(false)
      return
    }
    setShowPastSessions(true)
    setPastSessionsLoading(true)
    setErrorMessage(null)
    try {
      const data = await listSessions()
      setPastSessions(Array.isArray(data) ? data : [])
    } catch (err) {
      setErrorMessage(err.message || 'Failed to fetch sessions list')
    } finally {
      setPastSessionsLoading(false)
    }
  }

  // Delete a session
  const handleDeleteSession = async (id, e) => {
    e.stopPropagation()
    setErrorMessage(null)
    try {
      await deleteSession(id)
      setPastSessions((prev) => prev.filter((s) => s.id !== id && s.session_id !== id))
      if (session?.session_id === id) {
        handleStartNewSession()
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to delete session')
    }
  }

  // Resume or view a past session
  const handleResumePastSession = async (s) => {
    const id = s.id || s.session_id
    if (!id) return
    setLoading(true)
    setLoadingAction('Loading session details...')
    setErrorMessage(null)
    try {
      const sessionData = await getSession(id)
      setSession(sessionData)
      setSelectedRole(sessionData.role || '')

      if (sessionData.status === 'completed') {
        const sum = await getSummary(id)
        setSummary(sum)
        setStage('results')
      } else if (sessionData.status === 'in_progress') {
        const qs = await getQuestions(id)
        setQuestions(qs || [])
        setCurrentQuestionIndex(0)
        setStage('interview')
      } else {
        setStage('upload')
      }
      setShowPastSessions(false)
    } catch (err) {
      setErrorMessage(err.message || 'Failed to resume session')
    } finally {
      setLoading(false)
      setLoadingAction('')
    }
  }

  return (
    <div className="app-container">
      {/* App Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-logo-badge">RAG</div>
          <div>
            <h1 className="brand-title">Resume RAG Interviewer</h1>
            <p className="brand-subtitle">
              Retrieval-grounded technical interview simulator
            </p>
          </div>
        </div>
        <div className="header-actions">
          <span
            className={`status-indicator ${
              backendHealthy === true
                ? 'status-online'
                : backendHealthy === false
                ? 'status-offline'
                : 'status-checking'
            }`}
            title={
              backendHealthy === true
                ? 'Backend API reachable (http://localhost:8000)'
                : 'Backend API unreachable'
            }
          >
            ● {backendHealthy === true ? 'Backend Connected' : backendHealthy === false ? 'Backend Offline' : 'Connecting...'}
          </span>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleTogglePastSessions}
            disabled={loading}
          >
            {showPastSessions ? 'Close History' : 'Past Sessions'}
          </button>

          {stage !== 'upload' && (
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={handleStartNewSession}
              disabled={loading}
            >
              Start new session
            </button>
          )}
        </div>
      </header>

      {/* Dismissible Error Banner */}
      {errorMessage && (
        <div className="error-banner" role="alert">
          <div className="error-content">
            <span className="error-icon" aria-hidden="true">⚠️</span>
            <div className="error-text">
              <strong>Error:</strong> {errorMessage}
            </div>
          </div>
          <button
            type="button"
            className="error-dismiss"
            onClick={() => setErrorMessage(null)}
            aria-label="Dismiss error banner"
          >
            ✕
          </button>
        </div>
      )}

      {/* Past Sessions Drawer/Modal */}
      {showPastSessions && (
        <div className="card past-sessions-card">
          <div className="card-header">
            <h3>Saved Interview Sessions</h3>
            <button
              type="button"
              className="btn-icon"
              onClick={() => setShowPastSessions(false)}
            >
              ✕
            </button>
          </div>
          {pastSessionsLoading ? (
            <div className="loading-row">
              <span className="spinner" /> Loading saved sessions...
            </div>
          ) : pastSessions.length === 0 ? (
            <p className="muted-text">No saved sessions found on backend.</p>
          ) : (
            <div className="past-sessions-list">
              {pastSessions.map((s) => {
                const sid = s.id || s.session_id
                return (
                  <div key={sid} className="past-session-item">
                    <div
                      className="session-info-clickable"
                      onClick={() => handleResumePastSession(s)}
                    >
                      <div className="session-id-title">
                        <strong>Session {sid}</strong>
                        <span className={`badge badge-status status-${s.status}`}>
                          {s.status}
                        </span>
                      </div>
                      <div className="session-meta">Role: {s.role || 'N/A'}</div>
                    </div>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={(e) => handleDeleteSession(sid, e)}
                    >
                      Delete
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Main Content Card Flow */}
      <main className="main-content">
        {/* ================= STAGE 1: UPLOAD & ROLE SELECTION ================= */}
        {stage === 'upload' && (
          <div className="stage-container">
            <div className="stage-header">
              <div className="stage-pill">Stage 1 of 3</div>
              <h2>Target Role & Resume Upload</h2>
              <p className="stage-desc">
                Choose the technical role you want to practice for and upload your resume.
                Our RAG engine will extract your key competencies and align interview questions with role knowledge.
              </p>
            </div>

            {/* Role Selection */}
            <div className="card form-section">
              <h3 className="section-title">1. Select Target Role</h3>
              {rolesLoading ? (
                <div className="loading-row">
                  <span className="spinner" /> Fetching available roles...
                </div>
              ) : roles.length === 0 ? (
                <div className="empty-notice">
                  <p>No roles available from server.</p>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={handleRetryRoles}
                  >
                    Retry Loading Roles
                  </button>
                </div>
              ) : (
                <div className="role-cards-grid">
                  {roles.map((r) => {
                    const isSelected = selectedRole === r.id
                    return (
                      <label
                        key={r.id}
                        className={`role-card ${isSelected ? 'role-card-selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name="role"
                          value={r.id}
                          checked={isSelected}
                          onChange={() => setSelectedRole(r.id)}
                          className="role-radio-input"
                        />
                        <div className="role-card-content">
                          <div className="role-card-header">
                            <span className="role-label">{r.label}</span>
                            <span className="role-kb-badge">
                              {r.kb_chunks} KB chunks
                            </span>
                          </div>
                          <p className="role-description">{r.description}</p>
                        </div>
                      </label>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Resume Upload Form */}
            <div className="card form-section">
              <h3 className="section-title">2. Upload Resume</h3>
              <form onSubmit={handleCreateSession} className="upload-form">
                <div className="file-drop-area">
                  <label htmlFor="resume-file" className="file-input-label">
                    <span className="upload-icon">📄</span>
                    <span className="file-cta">
                      <strong>Choose a file</strong> or drag and drop here
                    </span>
                    <span className="file-types-hint">Supported formats: .pdf, .txt, .md</span>
                  </label>
                  <input
                    id="resume-file"
                    type="file"
                    accept=".pdf,.txt,.md"
                    onChange={handleFileChange}
                    className="file-input-hidden"
                    disabled={loading}
                  />

                  {file && (
                    <div className="selected-file-badge">
                      <span className="file-name">{file.name}</span>
                      <span className="file-size">({formatFileSize(file.size)})</span>
                    </div>
                  )}

                  {fileError && <div className="field-error">{fileError}</div>}
                </div>

                {!session && (
                  <div className="form-action-row">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={!file || !selectedRole || loading || rolesLoading}
                    >
                      {loading ? (
                        <>
                          <span className="spinner" /> {loadingAction || 'Creating session...'}
                        </>
                      ) : (
                        'Upload resume & create session'
                      )}
                    </button>
                  </div>
                )}
              </form>
            </div>

            {/* Parsed Profile Display (once session created) */}
            {session?.parsed_profile && (
              <div className="card parsed-profile-card">
                <div className="parsed-profile-header">
                  <div>
                    <h3 className="section-title">Parsed Candidate Profile</h3>
                    <p className="profile-subtitle">
                      Session ID: <code>{session.session_id}</code> &middot; Role:{' '}
                      <strong>{session.role}</strong>
                    </p>
                  </div>
                  {session.parsed_profile.years_experience_hint && (
                    <div className="experience-badge">
                      <span className="exp-label">Experience</span>
                      <span className="exp-value">
                        {session.parsed_profile.years_experience_hint}
                      </span>
                    </div>
                  )}
                </div>

                <div className="chips-section">
                  <h4>Skills</h4>
                  <div className="chips-wrap">
                    {session.parsed_profile.skills?.length > 0 ? (
                      session.parsed_profile.skills.map((s, idx) => (
                        <span key={idx} className="chip chip-skill">
                          {s}
                        </span>
                      ))
                    ) : (
                      <span className="muted-text">None detected</span>
                    )}
                  </div>
                </div>

                <div className="chips-section">
                  <h4>Technologies</h4>
                  <div className="chips-wrap">
                    {session.parsed_profile.technologies?.length > 0 ? (
                      session.parsed_profile.technologies.map((t, idx) => (
                        <span key={idx} className="chip chip-tech">
                          {t}
                        </span>
                      ))
                    ) : (
                      <span className="muted-text">None detected</span>
                    )}
                  </div>
                </div>

                <div className="chips-section">
                  <h4>Domains</h4>
                  <div className="chips-wrap">
                    {session.parsed_profile.domains?.length > 0 ? (
                      session.parsed_profile.domains.map((d, idx) => (
                        <span key={idx} className="chip chip-domain">
                          {d}
                        </span>
                      ))
                    ) : (
                      <span className="muted-text">None detected</span>
                    )}
                  </div>
                </div>

                <div className="start-interview-box">
                  <button
                    type="button"
                    className="btn btn-success btn-lg"
                    onClick={handleStartInterview}
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="spinner" /> {loadingAction || 'Starting interview...'}
                      </>
                    ) : (
                      'Start interview'
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================= STAGE 2: INTERVIEW ================= */}
        {stage === 'interview' && (
          <div className="stage-container">
            <div className="stage-header">
              <div className="stage-pill">Stage 2 of 3</div>
              <h2>Technical Interview In Progress</h2>
              <p className="stage-desc">
                Answer each question thoroughly. Questions are grounded in the role knowledge base and tailored to your resume.
              </p>
            </div>

            {/* Question Progress Tracker */}
            <div className="card progress-tracker-card">
              <div className="progress-info-row">
                <span className="progress-text">
                  Question <strong>{currentQuestionIndex + 1}</strong> of{' '}
                  <strong>{questions.length || 5}</strong>
                </span>
                <span className="answered-count-text">
                  {Object.keys(savedQuestions).length} of {questions.length} answered
                </span>
              </div>

              <div className="question-nav-strip">
                {questions.map((q, idx) => {
                  const isCurrent = idx === currentQuestionIndex
                  const isAnswered = !!savedQuestions[q.id]
                  return (
                    <button
                      key={q.id || idx}
                      type="button"
                      className={`q-step-btn ${isCurrent ? 'active' : ''} ${
                        isAnswered ? 'answered' : ''
                      }`}
                      onClick={() => setCurrentQuestionIndex(idx)}
                      disabled={loading}
                    >
                      <span className="q-step-num">Q{idx + 1}</span>
                      {isAnswered ? (
                        <span className="q-step-check" title="Answer saved">
                          ✓
                        </span>
                      ) : (
                        <span className="q-step-pending" />
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Question Card */}
            {currentQuestion ? (
              <div className="card question-card">
                <div className="question-header">
                  <div className="badges-row">
                    {currentQuestion.topic && (
                      <span className="badge badge-topic">{currentQuestion.topic}</span>
                    )}
                    {currentQuestion.difficulty && (
                      <span
                        className={`badge badge-difficulty difficulty-${currentQuestion.difficulty.toLowerCase()}`}
                      >
                        {currentQuestion.difficulty}
                      </span>
                    )}
                  </div>

                  <div className="grounded-line">
                    <span className="grounded-title">Grounded in:</span>{' '}
                    <strong>{currentQuestion.topic || 'Role Knowledge'}</strong>
                    {currentSourceChunks.length > 0 && (
                      <span className="grounded-chunks">
                        {' '}&middot; Source chunks:{' '}
                        {currentSourceChunks.map((c, i) => (
                          <code key={i} className="chunk-id-tag">
                            {c}
                          </code>
                        ))}
                      </span>
                    )}
                  </div>
                </div>

                <div className="question-prompt">
                  <h3>{currentQuestion.text}</h3>
                </div>

                {/* Answer Area */}
                <div className="answer-section">
                  <label htmlFor="interview-answer" className="answer-label">
                    Your Response
                    {savedQuestions[currentQuestion.id] && (
                      <span className="saved-indicator"> (Saved)</span>
                    )}
                  </label>
                  <textarea
                    id="interview-answer"
                    rows={7}
                    className="answer-textarea"
                    placeholder="Type your detailed technical answer here..."
                    value={answers[currentQuestion.id] || ''}
                    onChange={(e) => handleAnswerChange(e.target.value)}
                    disabled={loading}
                  />
                </div>

                {/* Question Actions */}
                <div className="question-actions-row">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setCurrentQuestionIndex((prev) => Math.max(0, prev - 1))}
                    disabled={currentQuestionIndex === 0 || loading}
                  >
                    Back
                  </button>

                  <div className="action-buttons-group">
                    {currentQuestionIndex < questions.length - 1 ? (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => handleSaveAnswer(true)}
                        disabled={loading}
                      >
                        {loading ? (
                          <>
                            <span className="spinner" /> {loadingAction || 'Saving...'}
                          </>
                        ) : (
                          'Save & Next'
                        )}
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => handleSaveAnswer(false)}
                          disabled={loading}
                        >
                          {loading ? (
                            <>
                              <span className="spinner" /> Saving...
                            </>
                          ) : (
                            'Save answer'
                          )}
                        </button>

                        {savedQuestions[currentQuestion.id] && (
                          <button
                            type="button"
                            className="btn btn-success"
                            onClick={handleFinishInterview}
                            disabled={loading}
                          >
                            {loading ? (
                              <>
                                <span className="spinner" /> {loadingAction || 'Completing...'}
                              </>
                            ) : (
                              'Finish & get summary'
                            )}
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="card empty-notice">
                <p>No questions found for this session.</p>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleStartNewSession}
                >
                  Start new session
                </button>
              </div>
            )}
          </div>
        )}

        {/* ================= STAGE 3: RESULTS SUMMARY ================= */}
        {stage === 'results' && (
          <div className="stage-container">
            <div className="stage-header">
              <div className="stage-pill stage-pill-success">Stage 3 of 3</div>
              <h2>Interview Evaluation & Results</h2>
              <p className="stage-desc">
                Review your overall performance assessment, highlighted technical strengths, identified knowledge gaps, and targeted next steps.
              </p>
            </div>

            {summary ? (
              <div className="results-container">
                {/* Overall Assessment */}
                <div className="card overall-assessment-card">
                  <h3 className="section-title">Overall Assessment</h3>
                  <p className="overall-assessment-text">
                    {summary.overall_assessment || 'Assessment completed.'}
                  </p>
                </div>

                {/* Strengths & Gaps Two-Column Grid */}
                <div className="two-col-grid">
                  <div className="card strengths-card">
                    <h3 className="section-title text-success">
                      <span className="icon-indicator">✓</span> Key Strengths
                    </h3>
                    {summary.strengths?.length > 0 ? (
                      <ul className="bullet-list strengths-list">
                        {summary.strengths.map((str, idx) => (
                          <li key={idx}>{str}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted-text">No specific strengths recorded.</p>
                    )}
                  </div>

                  <div className="card gaps-card">
                    <h3 className="section-title text-warning">
                      <span className="icon-indicator">!</span> Areas for Growth / Gaps
                    </h3>
                    {summary.gaps?.length > 0 ? (
                      <ul className="bullet-list gaps-list">
                        {summary.gaps.map((gap, idx) => (
                          <li key={idx}>{gap}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted-text">No significant gaps detected.</p>
                    )}
                  </div>
                </div>

                {/* Topics Covered */}
                {summary.topics_covered?.length > 0 && (
                  <div className="card topics-covered-card">
                    <h3 className="section-title">Topics Covered</h3>
                    <div className="chips-wrap">
                      {summary.topics_covered.map((topic, idx) => (
                        <span key={idx} className="chip chip-topic">
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Per-Question Breakdown */}
                <div className="card per-question-section">
                  <h3 className="section-title">Per-Question Breakdown</h3>
                  {summary.per_question?.length > 0 ? (
                    <div className="per-question-list">
                      {summary.per_question.map((item, idx) => (
                        <div key={item.question_id || idx} className="question-review-card">
                          <div className="review-header">
                            <span className="review-num">Question {idx + 1}</span>
                            <span className="review-qid">{item.question_id}</span>
                          </div>

                          <h4 className="review-question-text">{item.question}</h4>

                          <div className="review-answer-box">
                            <span className="review-label">Your Response:</span>
                            <p className="review-answer-text">
                              {item.answer ? item.answer : <em>(No answer submitted)</em>}
                            </p>
                          </div>

                          <div className="review-eval-box">
                            <span className="review-label">Assessment:</span>
                            <p className="review-eval-text">{item.assessment}</p>
                          </div>

                          <div className="review-points-grid">
                            <div className="points-col points-covered">
                              <span className="points-label text-success">Key Points Covered:</span>
                              {item.key_points_covered?.length > 0 ? (
                                <ul>
                                  {item.key_points_covered.map((pt, i) => (
                                    <li key={i}>{pt}</li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="muted-text">None covered</p>
                              )}
                            </div>

                            <div className="points-col points-missed">
                              <span className="points-label text-danger">Key Points Missed:</span>
                              {item.key_points_missed?.length > 0 ? (
                                <ul>
                                  {item.key_points_missed.map((pt, i) => (
                                    <li key={i}>{pt}</li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="muted-text">None missed</p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="muted-text">No per-question evaluations available.</p>
                  )}
                </div>

                {/* Recommended Next Steps */}
                {summary.recommended_next_steps?.length > 0 && (
                  <div className="card next-steps-card">
                    <h3 className="section-title">Recommended Next Steps</h3>
                    <ol className="ordered-steps-list">
                      {summary.recommended_next_steps.map((step, idx) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Restart / New Session Button */}
                <div className="results-actions-card">
                  <button
                    type="button"
                    className="btn btn-primary btn-lg"
                    onClick={handleStartNewSession}
                  >
                    Start new session
                  </button>
                </div>
              </div>
            ) : (
              <div className="card empty-notice">
                <p>Summary could not be loaded.</p>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleStartNewSession}
                >
                  Start new session
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>
          Resume RAG Interviewer &mdash; Grounded in technical knowledge bases & resume retrieval.
        </p>
      </footer>
    </div>
  )
}
