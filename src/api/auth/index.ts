import request from '../request'

export interface LoginReq {
    username: string
    password: string
}

export interface LoginResp {
    token: string
    user: {
        id: number
        username: string
        email?: string
        role?: string
        department?: number | null
        department_name?: string
    }
}

export interface DepartmentItem {
    id: number
    code: string
    name: string
    region: string
}

export function apiLogin(data: LoginReq) {
    return request<LoginResp>({
        url: '/auth/login',
        method: 'POST',
        data,
    })
}

export function apiLogout() {
    return request<{ message: string }>({
        url: '/auth/logout',
        method: 'POST',
    })
}

export function apiMe() {
    return request<LoginResp['user']>({
        url: '/auth/me',
        method: 'GET',
    })
}

export function apiDepartmentList() {
    return request<DepartmentItem[]>({
        url: '/auth/departments/',
        method: 'GET',
    })
}
