<script setup lang="ts">
import type { ProjectItem } from '@/api/project'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toast-notification'
import { apiLogout, apiMe } from '@/api/auth'
import { apiProjectList } from '@/api/project'
import { clearSession, getAuthUser, setAuthUser, setSelectedProject } from '@/utils/session'

const router = useRouter()
const toast = useToast()
const loading = ref(false)
const keyword = ref('')
const projectList = ref<ProjectItem[]>([])
const authUser = ref(getAuthUser())

const filteredProjectList = computed(() => {
    const key = keyword.value.trim().toLowerCase()
    if (!key)
        return projectList.value
    return projectList.value.filter((item) => {
        return (
            item.name.toLowerCase().includes(key)
            || item.code.toLowerCase().includes(key)
            || item.region.toLowerCase().includes(key)
        )
    })
})

async function fetchProjects() {
    loading.value = true
    try {
        const me = await apiMe()
        setAuthUser(me)
        authUser.value = me

        const list = await apiProjectList()
        projectList.value = list.filter(item => item.is_active)
    }
    catch (error: any) {
        toast.error(error?.message || '获取项目列表失败')
    }
    finally {
        loading.value = false
    }
}

function chooseProject(item: ProjectItem) {
    setSelectedProject(item.id, item.name)
    toast.success(`已切换到项目: ${item.name}`)
    router.push('/log-lottery/home')
}

async function handleLogout() {
    try {
        await apiLogout()
    }
    catch {
        // 忽略后端失败，前端仍清会话
    }
    clearSession()
    router.push('/log-lottery/login')
}

onMounted(() => {
    fetchProjects()
})
</script>

<template>
  <div class="min-h-screen bg-base-200 p-6 md:p-10">
    <div class="max-w-5xl mx-auto">
      <div class="mb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <h1 class="text-2xl font-bold">选择抽奖项目</h1>
          <p class="text-sm opacity-70">当前登录用户：{{ authUser?.username || '-' }}</p>
        </div>
        <div class="flex gap-2">
          <button class="btn btn-outline" @click="fetchProjects">刷新</button>
          <button class="btn btn-error" @click="handleLogout">退出登录</button>
        </div>
      </div>

      <div class="mb-4">
        <input v-model="keyword" class="input input-bordered w-full" type="text" placeholder="搜索项目名称/编号/区域">
      </div>

      <div class="bg-base-100 rounded-box border border-base-300 overflow-hidden">
        <table class="table table-zebra">
          <thead>
            <tr>
              <th>项目名称</th>
              <th>项目编号</th>
              <th>区域</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="4">加载中...</td>
            </tr>
            <tr v-for="item in filteredProjectList" :key="item.id">
              <td>{{ item.name }}</td>
              <td>{{ item.code }}</td>
              <td>{{ item.region || '-' }}</td>
              <td>
                <button class="btn btn-primary btn-sm" @click="chooseProject(item)">进入项目</button>
              </td>
            </tr>
            <tr v-if="!loading && filteredProjectList.length === 0">
              <td colspan="4">暂无可用项目</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
