import type { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import axios from 'axios'
import openModal from '@/components/ErrorModal'
import { clearSession, getAuthToken, getSelectedProjectId } from '@/utils/session'

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
                    return Promise.reject(error)
                }
                // 对响应错误做些什么
                if (error.response && error.response.data) {
                    const { code, msg, detail } = error.response.data
                    openModal({ title: code || error.response.status || '请求错误', desc: msg || detail || '请求失败' })
                    return Promise.reject(error.response.data)
                }
                openModal({ title: '请求错误', desc: error.message })
                return Promise.reject(error)
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
