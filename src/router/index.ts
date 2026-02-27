import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import Layout from '@/layout/index.vue'
import i18n from '@/locales/i18n'
import { getAuthToken, getSelectedProjectId } from '@/utils/session'
import Home from '@/views/Home/index.vue'

export const configRoutes = {
    path: '/log-lottery/config',
    name: 'Config',
    component: () => import('@/views/Config/index.vue'),
    children: [
        {
            path: '',
            redirect: '/log-lottery/config/person',
        },
        {
            path: '/log-lottery/config/person',
            name: 'PersonConfig',
            component: () => import('@/views/Config/Person/index.vue'),
            meta: {
                title: i18n.global.t('sidebar.personConfiguration'),
                icon: 'person',
            },
            children: [
                {
                    path: '',
                    redirect: '/log-lottery/config/person/all',
                },
                {
                    path: '/log-lottery/config/person/all',
                    name: 'AllPersonConfig',
                    component: () => import('@/views/Config/Person/PersonAll/index.vue'),
                    meta: {
                        title: i18n.global.t('sidebar.personList'),
                        icon: 'all',
                    },
                },
                {
                    path: '/log-lottery/config/person/already',
                    name: 'AlreadyPerson',
                    component: () => import('@/views/Config/Person/PersonAlready/index.vue'),
                    meta: {
                        title: i18n.global.t('sidebar.winnerList'),
                        icon: 'already',
                    },
                },
                // {
                //     path:'other',
                //     name:'OtherPersonConfig',
                //     component:()=>import('@/views/Config/Person/OtherPersonConfig.vue'),
                //     meta:{
                //         title:'其他配置',
                //         icon:'other'
                //     }
                // }
            ],
        },
        {
            path: '/log-lottery/config/prize',
            name: 'PrizeConfig',
            component: () => import('@/views/Config/Prize/PrizeConfig.vue'),
            meta: {
                title: i18n.global.t('sidebar.prizeConfiguration'),
                icon: 'prize',
            },
        },
        {
            path: '/log-lottery/config/exclusion-rules',
            name: 'ExclusionRules',
            component: () => import('@/views/Config/ExclusionRules/index.vue'),
            meta: {
                title: i18n.global.t('sidebar.exclusionRules'),
                icon: 'rule',
            },
        },
        {
            path: '/log-lottery/config/export-jobs',
            name: 'ExportJobs',
            component: () => import('@/views/Config/ExportJobs/index.vue'),
            meta: {
                title: i18n.global.t('sidebar.exportJobs'),
                icon: 'export',
            },
        },
        {
            path: '/log-lottery/config/global',
            name: 'GlobalConfig',
            redirect: '/log-lottery/config/global/all',
            meta: {
                title: i18n.global.t('sidebar.globalSetting'),
                icon: 'global',
            },
            children: [
                {
                    path: '/log-lottery/config/global/face',
                    name: 'FaceConfig',
                    component: () => import('@/views/Config/Global/FaceConfig/index.vue'),
                    meta: {
                        title: i18n.global.t('sidebar.viewSetting'),
                        icon: 'face',
                    },
                },
                {
                    path: '/log-lottery/config/global/image',
                    name: 'ImageConfig',
                    component: () => import('@/views/Config/Global/ImageConfig/index.vue'),
                    meta: {
                        title: i18n.global.t('sidebar.imagesManagement'),
                        icon: 'image',
                    },
                },
                {
                    path: '/log-lottery/config/global/music',
                    name: 'MusicConfig',
                    component: () => import('@/views/Config/Global/MusicConfig/index.vue'),
                    meta: {
                        title: i18n.global.t('sidebar.musicManagement'),
                        icon: 'music',
                    },
                },
            ],
        },
        {
            path: '/log-lottery/config/server',
            name: 'Server',
            component: () => import('@/views/Config/Server/index.vue'),
            meta: {
                hidden: import.meta.env.VITE_ENABLE_WEBSOCKET !== 'true',
                title: i18n.global.t('sidebar.server'),
                icon: 'server',
            },
        },
        {
            path: '/log-lottery/config/readme',
            name: 'Readme',
            component: () => import('@/views/Config/Readme/index.vue'),
            meta: {
                title: i18n.global.t('sidebar.operatingInstructions'),
                icon: 'readme',
            },
        },
    ],
}
const routes = [
    {
        path: '/',
        redirect: '/log-lottery',
    },
    {
        path: '/log-lottery/login',
        name: 'Login',
        meta: {
            public: true,
        },
        component: () => import('@/views/Auth/Login.vue'),
    },
    {
        path: '/log-lottery/project-select',
        name: 'ProjectSelect',
        component: () => import('@/views/Auth/ProjectSelect.vue'),
    },
    {
        path: '/log-lottery',
        component: Layout,
        redirect: '/log-lottery/home',
        children: [
            {
                path: '/log-lottery/home',
                name: 'Home',
                component: Home,
            },
            {
                path: '/log-lottery/demo',
                name: 'Demo',
                component: () => import('@/views/Demo/index.vue'),
            },
            {
                path: '/log-lottery/mobile',
                name: 'Mobile',
                meta: {
                    isMobile: true,
                    public: true,
                },
                component: () => import('@/views/Mobile/index.vue'),
            },
            configRoutes,
        ],
    },
]
const envMode = import.meta.env.MODE
const router = createRouter({
    // 读取环境变量
    history: envMode === 'file' ? createWebHashHistory() : createWebHistory(),
    routes,
})

router.beforeEach((to) => {
    const token = getAuthToken()
    const selectedProjectId = getSelectedProjectId()

    if (to.meta.public) {
        if (token) {
            return selectedProjectId ? '/log-lottery/home' : '/log-lottery/project-select'
        }
        return true
    }

    if (!token) {
        return '/log-lottery/login'
    }

    if (to.path === '/log-lottery/project-select') {
        return true
    }

    if (!selectedProjectId) {
        return '/log-lottery/project-select'
    }

    return true
})

export default router
