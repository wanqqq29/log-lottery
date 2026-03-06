const AUTH_TOKEN_KEY = 'auth_token'
const AUTH_USER_KEY = 'auth_user'
const SELECTED_PROJECT_ID_KEY = 'selected_project_id'
const SELECTED_PROJECT_NAME_KEY = 'selected_project_name'
const AUTH_SESSION_ISSUED_AT_KEY = 'auth_session_issued_at'
const AUTH_SESSION_EXPIRES_AT_KEY = 'auth_session_expires_at'
const DEFAULT_AUTH_TOKEN_TTL_MINUTES = 8 * 60
const AUTH_SESSION_CHECK_INTERVAL_MS = 60 * 1000

function resolveTokenTtlMinutes() {
    const envValue = Number(import.meta.env.VITE_AUTH_TOKEN_TTL_MINUTES)
    if (Number.isFinite(envValue) && envValue > 0) {
        return envValue
    }
    return DEFAULT_AUTH_TOKEN_TTL_MINUTES
}

function getAuthSessionExpiresAt() {
    const raw = localStorage.getItem(AUTH_SESSION_EXPIRES_AT_KEY)
    const expiresAt = Number(raw)
    if (!Number.isFinite(expiresAt) || expiresAt <= 0) {
        return 0
    }
    return expiresAt
}

function setAuthSessionLifetime() {
    const now = Date.now()
    const ttlMinutes = resolveTokenTtlMinutes()
    const expiresAt = now + ttlMinutes * 60 * 1000
    localStorage.setItem(AUTH_SESSION_ISSUED_AT_KEY, String(now))
    localStorage.setItem(AUTH_SESSION_EXPIRES_AT_KEY, String(expiresAt))
}

function isTokenExpired() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY)
    if (!token) {
        return false
    }

    const expiresAt = getAuthSessionExpiresAt()
    if (!expiresAt) {
        // 兼容旧版本：首次读取时补齐过期时间，不强制踢下线
        setAuthSessionLifetime()
        return false
    }

    return Date.now() >= expiresAt
}

function handleSessionExpired() {
    clearSession()
    if (window.location.pathname !== '/log-lottery/login') {
        window.location.href = '/log-lottery/login'
    }
}

export interface AuthUser {
    id: number
    username: string
    email?: string
    role?: string
    department?: number | null
    department_name?: string
}

export function getAuthToken() {
    if (isTokenExpired()) {
        clearSession()
        return ''
    }
    return localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

export function setAuthToken(token: string) {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
    setAuthSessionLifetime()
}

export function clearAuthToken() {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(AUTH_SESSION_ISSUED_AT_KEY)
    localStorage.removeItem(AUTH_SESSION_EXPIRES_AT_KEY)
}

export function getAuthUser(): AuthUser | null {
    const raw = localStorage.getItem(AUTH_USER_KEY)
    if (!raw)
        return null
    try {
        return JSON.parse(raw) as AuthUser
    }
    catch {
        return null
    }
}

export function setAuthUser(user: AuthUser) {
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
}

export function clearAuthUser() {
    localStorage.removeItem(AUTH_USER_KEY)
}

export function getSelectedProjectId() {
    return localStorage.getItem(SELECTED_PROJECT_ID_KEY) || ''
}

export function getSelectedProjectName() {
    return localStorage.getItem(SELECTED_PROJECT_NAME_KEY) || ''
}

export function setSelectedProject(projectId: string, projectName: string) {
    localStorage.setItem(SELECTED_PROJECT_ID_KEY, projectId)
    localStorage.setItem(SELECTED_PROJECT_NAME_KEY, projectName)
}

export function clearSelectedProject() {
    localStorage.removeItem(SELECTED_PROJECT_ID_KEY)
    localStorage.removeItem(SELECTED_PROJECT_NAME_KEY)
}

export function clearSession() {
    clearAuthToken()
    clearAuthUser()
    clearSelectedProject()
}

let authSessionTimer: number | null = null

export function startAuthSessionGuard() {
    if (authSessionTimer !== null) {
        return
    }

    const checkSession = () => {
        const hadToken = Boolean(localStorage.getItem(AUTH_TOKEN_KEY))
        const token = getAuthToken()
        if (hadToken && !token) {
            handleSessionExpired()
        }
    }

    checkSession()
    authSessionTimer = window.setInterval(checkSession, AUTH_SESSION_CHECK_INTERVAL_MS)
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            checkSession()
        }
    })
}
