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

export interface BackendProjectMemberPayload {
    project: string
    uid: string
    name: string
    phone: string
    is_active?: boolean
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

export interface BackendPrizePayload {
    project: string
    name: string
    sort: number
    is_all: boolean
    total_count: number
    separate_count?: {
        enable?: boolean
        countList?: Array<{ id: string, count: number, isUsedCount: number }>
    }
    description?: string
    is_active?: boolean
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

export interface BackendExclusionRule {
    id: string
    source_project: string
    source_prize: string | null
    target_project: string
    target_prize: string | null
    mode: string
    is_enabled: boolean
    description: string
    created_at: string
    updated_at: string
}

export interface BackendExportJob {
    id: string
    project: string
    requested_by: number
    filters: Record<string, any>
    status: 'PENDING' | 'SUCCESS' | 'FAILED'
    file_path: string
    error_message: string
    created_at: string
    updated_at: string
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

export function apiProjectMemberCreate(data: BackendProjectMemberPayload) {
    return request<BackendProjectMember>({
        url: '/project-members/',
        method: 'POST',
        data,
    })
}

export function apiProjectMemberDelete(memberId: number) {
    return request<void>({
        url: `/project-members/${memberId}/`,
        method: 'DELETE',
    })
}

export function apiProjectMemberBulkUpsert(data: {
    project_id: string
    members: Array<{ uid: string, name: string, phone: string, is_active?: boolean }>
}) {
    return request<{ project_id: string, created_count: number, updated_count: number, total: number }>({
        url: '/project-members/bulk-upsert/',
        method: 'POST',
        data,
    })
}

export function apiClearProjectMembers(data: { project_id: string, reason?: string }) {
    return request<{
        project_id: string
        deleted_member_count: number
        winner_affected: number
        batch_affected: number
    }>({
        url: '/project-members/clear-project/',
        method: 'POST',
        data,
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

export function apiPrizeCreate(data: BackendPrizePayload) {
    return request<BackendPrize>({
        url: '/prizes/',
        method: 'POST',
        data,
    })
}

export function apiPrizeUpdate(prizeId: string, data: Partial<BackendPrizePayload>) {
    return request<BackendPrize>({
        url: `/prizes/${prizeId}/`,
        method: 'PATCH',
        data,
    })
}

export function apiPrizeDelete(prizeId: string) {
    return request<void>({
        url: `/prizes/${prizeId}/`,
        method: 'DELETE',
    })
}

export function apiDrawBatchList(params: { project_id: string, prize_id?: string, status?: 'PENDING' | 'CONFIRMED' | 'VOID' }) {
    return request<BackendDrawBatch[]>({
        url: '/draw-batches/',
        method: 'GET',
        params,
    })
}

export function apiDrawWinnerList(params: {
    project_id: string
    prize_id?: string
    status?: 'PENDING' | 'CONFIRMED' | 'VOID'
}) {
    return request<BackendDrawWinner[]>({
        url: '/draw-winners/',
        method: 'GET',
        params,
    })
}

export function apiRevokeWinner(winnerId: string, reason?: string) {
    return request<BackendDrawWinner>({
        url: `/draw-winners/${winnerId}/revoke/`,
        method: 'POST',
        data: {
            reason,
        },
    })
}

export function apiResetProjectWinners(data: { project_id: string, reason?: string }) {
    return request<{ project_id: string, winner_affected: number, batch_affected: number }>({
        url: '/draw-winners/reset-project/',
        method: 'POST',
        data,
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

export function apiExclusionRuleList(projectId: string) {
    return request<BackendExclusionRule[]>({
        url: '/exclusion-rules/',
        method: 'GET',
        params: {
            project_id: projectId,
        },
    })
}

export function apiExclusionRuleCreate(data: {
    source_project: string
    source_prize?: string | null
    target_project: string
    target_prize?: string | null
    mode?: string
    is_enabled?: boolean
    description?: string
}) {
    return request<BackendExclusionRule>({
        url: '/exclusion-rules/',
        method: 'POST',
        data,
    })
}

export function apiExclusionRuleUpdate(ruleId: string, data: Partial<{
    source_project: string
    source_prize: string | null
    target_project: string
    target_prize: string | null
    mode: string
    is_enabled: boolean
    description: string
}>) {
    return request<BackendExclusionRule>({
        url: `/exclusion-rules/${ruleId}/`,
        method: 'PATCH',
        data,
    })
}

export function apiExclusionRuleDelete(ruleId: string) {
    return request<void>({
        url: `/exclusion-rules/${ruleId}/`,
        method: 'DELETE',
    })
}

export function apiExportJobList(projectId: string) {
    return request<BackendExportJob[]>({
        url: '/export-jobs/',
        method: 'GET',
        params: {
            project_id: projectId,
        },
    })
}

export function apiExportJobCreate(data: { project_id: string, prize_id?: string, status?: 'PENDING' | 'CONFIRMED' | 'VOID' }) {
    return request<BackendExportJob>({
        url: '/export-jobs/',
        method: 'POST',
        data,
    })
}

export function apiExportJobDownload(jobId: string) {
    return request<Blob>({
        url: `/export-jobs/${jobId}/download/`,
        method: 'GET',
        responseType: 'blob',
    })
}
