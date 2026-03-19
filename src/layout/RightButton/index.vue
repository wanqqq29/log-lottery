<script setup lang='ts'>
import { useFullscreen } from '@vueuse/core'
import { LogOut, Maximize, Minimize } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { apiLogout } from '@/api/auth'
import { clearSelectedProject, clearSession } from '@/utils/session'
import { usePlayMusic } from './usePlayMusic'

const { playMusic, currentMusic, nextPlay } = usePlayMusic()
const { isFullscreen, toggle: toggleScreen } = useFullscreen()
const { t } = useI18n()
const router = useRouter()
const route = useRoute()

const settingRef = ref()
const fullScreenRef = ref()
const visible = ref(true)

function enterConfig() {
    router.push('/log-lottery/config')
}
function enterHome() {
    router.push('/log-lottery')
}
function exitCurrentProject() {
    clearSelectedProject()
    router.push('/log-lottery/project-select')
}
async function logout() {
    try {
        await apiLogout()
    }
    catch {
        // 忽略后端失败，前端仍清会话
    }
    clearSession()
    router.push('/log-lottery/login')
}

watch(() => route, (val) => {
    const { meta } = val
    if (meta && meta.isMobile) {
        visible.value = false
    }
}, { immediate: true })
onMounted(() => {
    if (!settingRef.value) {
        return
    }
    settingRef.value.addEventListener('mouseenter', () => {
        fullScreenRef.value.style.display = 'block'
    })
    settingRef.value.addEventListener('mouseleave', () => {
        fullScreenRef.value.style.display = 'none'
    })
})
</script>

<template>
  <div v-if="visible" ref="settingRef" class="flex flex-col gap-3">
    <div ref="fullScreenRef" class="tooltip tooltip-left hidden" @click="toggleScreen">
      <div
        v-if="isFullscreen"
        class="flex items-center justify-center w-10 h-10 p-0 m-0 cursor-pointer setting-container bg-slate-500/50 rounded-l-xl hover:bg-slate-500/80 hover:text-blue-400/90"
      >
        <Minimize />
      </div>
      <div
        v-else
        class="flex items-center justify-center w-10 h-10 p-0 m-0 cursor-pointer setting-container bg-slate-500/50 rounded-l-xl hover:bg-slate-500/80 hover:text-blue-400/90"
      >
        <Maximize />
      </div>
    </div>
    <div v-if="route.path.includes('/config')" class="tooltip tooltip-left" :data-tip="t('tooltip.toHome')">
      <div
        class="flex items-center justify-center w-10 h-10 p-0 m-0 cursor-pointer setting-container bg-slate-500/50 rounded-l-xl hover:bg-slate-500/80 hover:text-blue-400/90"
        @click="enterHome"
      >
        <svg-icon name="home" />
      </div>
    </div>
    <div v-else class="tooltip tooltip-left" :data-tip="t('tooltip.settingConfiguration')">
      <div
        class="flex items-center justify-center w-10 h-10 p-0 m-0 cursor-pointer setting-container bg-slate-500/50 rounded-l-xl hover:bg-slate-500/80 hover:text-blue-400/90"
        @click="enterConfig"
      >
        <svg-icon name="setting" />
      </div>
    </div>
    <div class="tooltip tooltip-left" data-tip="退出当前项目">
      <div
        class="flex items-center justify-center w-10 h-10 p-0 m-0 cursor-pointer setting-container bg-slate-500/50 rounded-l-xl hover:bg-slate-500/80 hover:text-blue-400/90"
        @click="exitCurrentProject"
      >
        <svg-icon name="menu" />
      </div>
    </div>
    <div class="tooltip tooltip-left" data-tip="退出登录">
      <div
        class="flex items-center justify-center w-10 h-10 p-0 m-0 cursor-pointer setting-container bg-slate-500/50 rounded-l-xl hover:bg-slate-500/80 hover:text-blue-400/90"
        @click="logout"
      >
        <LogOut :size="18" />
      </div>
    </div>
    <div class="tooltip tooltip-left" :data-tip="currentMusic.item ? `${currentMusic.item.name}\n\r ${t('tooltip.nextSong')}` : t('tooltip.noSongPlay')">
      <div
        class="flex items-center justify-center w-10 h-10 p-0 m-0 cursor-pointer setting-container bg-slate-500/50 rounded-l-xl hover:bg-slate-500/80 hover:text-blue-400/90"
        @click="playMusic(currentMusic.item)" @click.right.prevent="nextPlay"
      >
        <svg-icon :name="currentMusic.paused ? 'play' : 'pause'" />
      </div>
    </div>
  </div>
</template>

<style lang='scss' scoped>
details {

    // display: none;
    summary {
        display: none;
    }
}
</style>
