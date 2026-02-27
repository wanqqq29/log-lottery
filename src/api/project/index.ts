import request from '../request'

export interface ProjectItem {
    id: string
    code: string
    name: string
    department: number
    region: string
    description: string
    is_active: boolean
    created_at: string
    updated_at: string
}

export function apiProjectList() {
    return request<ProjectItem[]>({
        url: '/projects/',
        method: 'GET',
    })
}
