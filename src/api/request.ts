import type { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import axios from 'axios'
import openModal from '@/components/ErrorModal'
import { clearSession, getAuthToken, getSelectedProjectId } from '@/utils/session'

const FIELD_LABELS: Record<string, string> = {
    username: '用户名',
    password: '密码',
    department: '部门',
    project: '项目',
    project_id: '项目',
    source_project: '来源项目',
    target_project: '目标项目',
    source_prize: '来源奖项',
    target_prize: '目标奖项',
    prize: '奖项',
    prize_id: '奖项',
    name: '名称',
    code: '编码',
    uid: '编号',
    phone: '手机号',
    members: '名单',
    count: '抽取人数',
    total_count: '总人数',
    sort: '排序',
    status: '状态',
    reason: '原因',
    description: '说明',
    arrival_state: '到访领奖状态',
    days: '统计天数',
    is_prize_claimed: '领奖状态',
    claim_note: '领奖备注',
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function flattenErrorValue(value: unknown): string[] {
    if (value === null || value === undefined) {
        return []
    }
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        return [String(value)]
    }
    if (Array.isArray(value)) {
        return value.flatMap(item => flattenErrorValue(item))
    }
    if (isRecord(value)) {
        return Object.values(value).flatMap(item => flattenErrorValue(item))
    }
    return []
}

function translateBackendMessage(message: string): string {
    const msg = message.trim()
    if (!msg) {
        return msg
    }

    if (msg === 'This field is required.') return '该字段为必填项'
    if (msg === 'This field may not be blank.') return '该字段不能为空'
    if (msg === 'This field may not be null.') return '该字段不能为空'
    if (msg === 'A valid integer is required.') return '请输入有效整数'
    if (msg === 'A valid boolean is required.') return '请输入有效的布尔值'
    if (msg === 'A valid UUID is required.') return '请输入有效的ID格式'
    if (msg === 'Invalid pk') return '无效的主键'
    if (msg.toLowerCase().includes('already exists')) return '该记录已存在，请勿重复提交'
    if (msg.includes('must make a unique set')) return '该组合已存在，请勿重复提交'
    if (msg.includes('Incorrect type. Expected pk value')) return '字段类型错误，请检查参数'

    const maxMatch = msg.match(/^Ensure this field has no more than (\d+) characters\.$/)
    if (maxMatch) {
        return `长度不能超过 ${maxMatch[1]} 个字符`
    }

    const minMatch = msg.match(/^Ensure this field has at least (\d+) characters\.$/)
    if (minMatch) {
        return `长度不能少于 ${minMatch[1]} 个字符`
    }

    return msg
}

function fieldLabel(field: string): string {
    if (field === 'non_field_errors') {
        return '业务校验'
    }
    return FIELD_LABELS[field] || field
}

function parseErrorMessages(value: unknown): string[] {
    return flattenErrorValue(value)
        .map(item => translateBackendMessage(item))
        .filter(Boolean)
}

type ParsedApiError = {
    title: string
    desc: string
    fields: Record<string, string[]>
}

function extractApiError(data: unknown, fallbackStatus?: number): ParsedApiError {
    const fallbackTitle = fallbackStatus ? String(fallbackStatus) : '请求错误'
    const fallbackDesc = '请求失败'
    if (!isRecord(data)) {
        const plain = parseErrorMessages(data).join('；')
        return {
            title: fallbackTitle,
            desc: plain || fallbackDesc,
            fields: {},
        }
    }

    const title = flattenErrorValue(data.code)[0] || fallbackTitle
    const directMessage = parseErrorMessages(data.msg)[0]
        || parseErrorMessages(data.message)[0]
        || parseErrorMessages(data.detail)[0]
    if (directMessage) {
        return { title, desc: directMessage, fields: {} }
    }

    const fields: Record<string, string[]> = {}
    const fieldMessages = Object.entries(data)
        .filter(([key]) => !['code', 'msg', 'message', 'detail'].includes(key))
        .map(([key, value]) => {
            const values = parseErrorMessages(value)
            if (!values.length) {
                return ''
            }
            fields[key] = values
            const fieldName = fieldLabel(key)
            return `${fieldName}：${values.join('，')}`
        })
        .filter(Boolean)

    return {
        title,
        desc: fieldMessages.join('；') || fallbackDesc,
        fields,
    }
}

class Request {
    private instance: AxiosInstance

    constructor(config: AxiosRequestConfig) {
        this.instance = axios.create({
            baseURL: '/api',
            timeout: 10000,
            ...config,
        })

        // 添加请求拦截器
        this.instance.interceptors.request.use(
            (config: InternalAxiosRequestConfig) => {
                const token = getAuthToken()
                const selectedProjectId = getSelectedProjectId()

                if (token) {
                    config.headers.Authorization = `Bearer ${token}`
                }
                if (selectedProjectId && !config.headers['X-Project-Id']) {
                    config.headers['X-Project-Id'] = selectedProjectId
                }

                return config
            },
            (error: any) => {
                // 对请求错误做些什么
                return Promise.reject(error)
            },
        )

        // 添加响应拦截器
        this.instance.interceptors.response.use(
            (response: AxiosResponse) => {
                // 对响应数据做些什么
                return response
            },
            (error: any) => {
                if (error?.response?.status === 401) {
                    clearSession()
                    if (window.location.pathname !== '/log-lottery/login') {
                        window.location.href = '/log-lottery/login'
                    }
                    return Promise.reject({
                        status: 401,
                        code: '401',
                        message: '登录状态已失效，请重新登录',
                        msg: '登录状态已失效，请重新登录',
                        detail: '登录状态已失效，请重新登录',
                        fields: {},
                        raw: error?.response?.data ?? null,
                    })
                }
                // 对响应错误做些什么
                if (error.response && error.response.data) {
                    const parsed = extractApiError(error.response.data, error.response.status)
                    openModal({ title: parsed.title, desc: parsed.desc })
                    return Promise.reject({
                        status: error.response.status,
                        code: parsed.title,
                        message: parsed.desc,
                        msg: parsed.desc,
                        detail: parsed.desc,
                        fields: parsed.fields,
                        raw: error.response.data,
                    })
                }
                const fallbackMessage = translateBackendMessage(error?.message || '网络异常，请稍后重试')
                openModal({ title: '请求错误', desc: fallbackMessage })
                return Promise.reject({
                    status: 0,
                    code: 'REQUEST_ERROR',
                    message: fallbackMessage,
                    msg: fallbackMessage,
                    detail: fallbackMessage,
                    fields: {},
                    raw: error,
                })
            },
        )
    }

    public async request<T>(config: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.instance.request(config)

        return response.data
    }
}

// 函数
function request<T>(config: AxiosRequestConfig): Promise<T> {
    const instance = new Request(config)

    return instance.request(config)
}

export default request
