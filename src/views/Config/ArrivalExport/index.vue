<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useToast } from 'vue-toast-notification'
import { apiExportArrivalWinners, apiPrizeList, type BackendPrize } from '@/api/lottery'
import PageHeader from '@/components/PageHeader/index.vue'
import { getSelectedProjectId, getSelectedProjectName } from '@/utils/session'

function buildErrorMessage(error: any, fallback: string) {
    return error?.message || error?.detail || error?.msg || fallback
}

function formatTime() {
    const d = new Date()
    const p = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
}

const toast = useToast()
const loading = ref(false)
const prizes = ref<BackendPrize[]>([])
const selectedProjectId = ref(getSelectedProjectId())
const selectedProjectName = ref(getSelectedProjectName() || '当前项目')

const form = ref({
    arrival_state: 'CLAIMED' as 'CLAIMED' | 'UNCLAIMED',
    prize_id: '',
})

async function refreshPrizes() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    loading.value = true
    try {
        const list = await apiPrizeList(selectedProjectId.value)
        prizes.value = list.filter(item => item.is_active)
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '加载奖项失败'))
    }
    finally {
        loading.value = false
    }
}

async function exportCsv() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    loading.value = true
    try {
        const blob = await apiExportArrivalWinners({
            project_id: selectedProjectId.value,
            arrival_state: form.value.arrival_state,
            prize_id: form.value.prize_id || undefined,
        })
        const url = window.URL.createObjectURL(blob)
        const stateLabel = form.value.arrival_state === 'CLAIMED' ? '已到访领奖' : '未到访领奖'
        const a = document.createElement('a')
        a.href = url
        a.download = `${selectedProjectName.value}-${stateLabel}-${formatTime()}.csv`
        a.click()
        window.URL.revokeObjectURL(url)
        toast.success('导出成功')
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '导出失败'))
    }
    finally {
        loading.value = false
    }
}

onMounted(() => {
    refreshPrizes()
})
</script>

<template>
  <div>
    <PageHeader title="到访领奖导出">
      <template #buttons>
        <div class="flex items-center gap-3 text-sm">
          <span class="badge badge-outline">项目：{{ selectedProjectName }}</span>
          <button class="btn btn-sm btn-outline" :disabled="loading" @click="refreshPrizes">刷新奖项</button>
        </div>
      </template>
      <template #alerts>
        <div role="alert" class="w-full my-3 alert alert-warning">
          <span>导出严格受账号项目边界约束，仅能导出当前有权限项目的数据。</span>
        </div>
      </template>
    </PageHeader>

    <div class="max-w-2xl p-5 border rounded-xl border-base-300 bg-base-200">
      <h3 class="mb-4 text-base font-semibold">导出条件</h3>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label class="form-control">
          <span class="label-text">导出类型</span>
          <select v-model="form.arrival_state" class="select select-bordered select-sm">
            <option value="CLAIMED">中奖已到访领奖</option>
            <option value="UNCLAIMED">中奖未到访领奖</option>
          </select>
        </label>
        <label class="form-control">
          <span class="label-text">奖项（可选）</span>
          <select v-model="form.prize_id" class="select select-bordered select-sm">
            <option value="">全部奖项</option>
            <option v-for="prize in prizes" :key="prize.id" :value="prize.id">
              {{ prize.name }}
            </option>
          </select>
        </label>
      </div>
      <div class="mt-5">
        <button class="btn btn-primary btn-sm" :disabled="loading" @click="exportCsv">
          {{ loading ? '导出中...' : '立即导出 CSV' }}
        </button>
      </div>
    </div>
  </div>
</template>
