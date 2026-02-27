import request from '../request'

export interface BackendProjectMember {
    id: number
    project: string
    uid: string
    name: string
    phone: string
    is_active: boolean
    created_at: string
    updated_at: string
}

export interface BackendPrize {
    id: string
    project: string
    name: string
    sort: number
    is_all: boolean
    total_count: number
    used_count: number
    separate_count: {
        enable?: boolean
        countList?: Array<{ id: string, count: number, isUsedCount: number }>
    }
    description: string
    is_active: boolean
    created_at: string
    updated_at: string
}

export interface BackendDrawWinner {
    id: string
    batch: string
    project: string
    prize: string
    uid: string
    name: string
    phone: string
    status: 'PENDING' | 'CONFIRMED' | 'VOID'
    confirmed_at: string | null
    void_reason: string
    created_at: string
}

export interface BackendDrawBatch {
    id: string
    project: string
    prize: string
    requested_by: number
    draw_count: number
    status: 'PENDING' | 'CONFIRMED' | 'VOID'
    draw_scope: Record<string, any>
    void_reason: string
    created_at: string
    updated_at: string
    winners: BackendDrawWinner[]
}

export interface PreviewDrawReq {
    project_id: string
    prize_id: string
    count: number
    scope?: {
        include_uids?: string[]
        include_phones?: string[]
    }
}

export function apiProjectMemberList(projectId: string) {
    return request<BackendProjectMember[]>({
        url: '/project-members/',
        method: 'GET',
        params: {
            project_id: projectId,
        },
    })
}

export function apiPrizeList(projectId: string) {
    return request<BackendPrize[]>({
        url: '/prizes/',
        method: 'GET',
        params: {
            project_id: projectId,
        },
    })
}

export function apiDrawBatchList(params: { project_id: string, prize_id?: string, status?: 'PENDING' | 'CONFIRMED' | 'VOID' }) {
    return request<BackendDrawBatch[]>({
        url: '/draw-batches/',
        method: 'GET',
        params,
    })
}

export function apiPreviewDraw(data: PreviewDrawReq) {
    return request<BackendDrawBatch>({
        url: '/draw-batches/preview/',
        method: 'POST',
        data,
    })
}

export function apiConfirmDraw(batchId: string) {
    return request<BackendDrawBatch>({
        url: `/draw-batches/${batchId}/confirm/`,
        method: 'POST',
    })
}

export function apiVoidDraw(batchId: string, reason: string) {
    return request<BackendDrawBatch>({
        url: `/draw-batches/${batchId}/void/`,
        method: 'POST',
        data: {
            reason,
        },
    })
}
