const AUTH_TOKEN_KEY = 'auth_token'
const AUTH_USER_KEY = 'auth_user'
const SELECTED_PROJECT_ID_KEY = 'selected_project_id'
const SELECTED_PROJECT_NAME_KEY = 'selected_project_name'

export interface AuthUser {
    id: number
    username: string
    email?: string
    role?: string
    department?: number | null
    department_name?: string
}

export function getAuthToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

export function setAuthToken(token: string) {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export function clearAuthToken() {
    localStorage.removeItem(AUTH_TOKEN_KEY)
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
