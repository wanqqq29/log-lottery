<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toast-notification'
import { apiLogin } from '@/api/auth'
import { setAuthToken, setAuthUser } from '@/utils/session'

const username = ref('')
const password = ref('')
const loading = ref(false)
const router = useRouter()
const toast = useToast()

async function handleLogin() {
    if (!username.value || !password.value) {
        toast.warning('请输入用户名和密码')
        return
    }

    loading.value = true
    try {
        const data = await apiLogin({ username: username.value, password: password.value })
        setAuthToken(data.token)
        setAuthUser(data.user)
        toast.success('登录成功')
        router.push('/log-lottery/project-select')
    }
    catch (error: any) {
        toast.error(error?.message || '登录失败')
    }
    finally {
        loading.value = false
    }
}
</script>

<template>
  <div class="flex items-center justify-center min-h-screen bg-base-200 px-4">
    <div class="w-full max-w-md shadow-xl card bg-base-100">
      <div class="card-body">
        <h1 class="text-2xl font-bold text-center">后台登录</h1>
        <p class="text-sm opacity-70 text-center">登录后选择抽奖项目</p>

        <label class="form-control w-full">
          <div class="label"><span class="label-text">用户名</span></div>
          <input v-model="username" type="text" class="input input-bordered w-full" placeholder="请输入用户名">
        </label>

        <label class="form-control w-full">
          <div class="label"><span class="label-text">密码</span></div>
          <input v-model="password" type="password" class="input input-bordered w-full" placeholder="请输入密码" @keyup.enter="handleLogin">
        </label>

        <button class="btn btn-primary mt-4" :disabled="loading" @click="handleLogin">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </div>
    </div>
  </div>
</template>
