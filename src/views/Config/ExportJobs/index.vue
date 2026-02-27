<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useToast } from 'vue-toast-notification'
import { apiExportJobCreate, apiExportJobDownload, apiExportJobList, apiPrizeList, type BackendExportJob, type BackendPrize } from '@/api/lottery'
import PageHeader from '@/components/PageHeader/index.vue'
import { getSelectedProjectId, getSelectedProjectName } from '@/utils/session'

function buildErrorMessage(error: any, fallback: string) {
    return error?.message || error?.detail || error?.msg || fallback
}

const toast = useToast()
const loading = ref(false)
const jobs = ref<BackendExportJob[]>([])
const prizes = ref<BackendPrize[]>([])
const selectedProjectId = ref(getSelectedProjectId())
const selectedProjectName = ref(getSelectedProjectName() || '当前项目')

const form = ref({
    prize_id: '',
    status: 'CONFIRMED' as 'PENDING' | 'CONFIRMED' | 'VOID',
})

function statusLabel(status: 'PENDING' | 'CONFIRMED' | 'VOID' | 'SUCCESS' | 'FAILED') {
    const mapping: Record<string, string> = {
        PENDING: '待确认',
        CONFIRMED: '已确认',
        VOID: '已作废',
        SUCCESS: '成功',
        FAILED: '失败',
    }
    return mapping[status] || status
}

async function refreshData() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    loading.value = true
    try {
        const [jobList, prizeList] = await Promise.all([
            apiExportJobList(selectedProjectId.value),
            apiPrizeList(selectedProjectId.value),
        ])
        jobs.value = jobList
        prizes.value = prizeList.filter(item => item.is_active)
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '加载导出任务失败'))
    }
    finally {
        loading.value = false
    }
}

async function createJob() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    try {
        await apiExportJobCreate({
            project_id: selectedProjectId.value,
            prize_id: form.value.prize_id || undefined,
            status: form.value.status,
        })
        toast.success('导出任务已创建')
        await refreshData()
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '创建导出任务失败'))
    }
}

async function downloadJob(row: BackendExportJob) {
    try {
        if (row.status !== 'SUCCESS') {
            toast.error('任务尚未成功，无法下载')
            return
        }
        const blob = await apiExportJobDownload(row.id)
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `中奖导出-${row.id}.csv`
        a.click()
        window.URL.revokeObjectURL(url)
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '下载失败'))
    }
}

onMounted(() => {
    refreshData()
})
</script>

<template>
  <div>
    <PageHeader title="导出任务">
      <template #buttons>
        <div class="flex items-center gap-3">
          <span class="text-sm opacity-70">当前项目：{{ selectedProjectName }}</span>
          <button class="btn btn-sm btn-outline" :disabled="loading" @click="refreshData">刷新</button>
        </div>
      </template>
      <template #alerts>
        <div role="alert" class="w-full my-3 alert alert-info">
          <span>说明：创建导出任务后，状态为“成功”才可下载 CSV。</span>
        </div>
      </template>
    </PageHeader>

    <div class="p-4 mb-4 border rounded-lg border-base-300 bg-base-200">
      <h3 class="mb-3 text-sm font-semibold">创建导出任务</h3>
      <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label class="form-control">
          <span class="label-text">奖项（可选）</span>
          <select v-model="form.prize_id" class="select select-bordered select-sm">
            <option value="">全部奖项</option>
            <option v-for="prize in prizes" :key="prize.id" :value="prize.id">
              {{ prize.name }}
            </option>
          </select>
        </label>
        <label class="form-control">
          <span class="label-text">中奖状态</span>
          <select v-model="form.status" class="select select-bordered select-sm">
            <option value="CONFIRMED">已确认</option>
            <option value="PENDING">待确认</option>
            <option value="VOID">已作废</option>
          </select>
        </label>
        <div class="form-control">
          <span class="label-text">&nbsp;</span>
          <button class="btn btn-primary btn-sm" :disabled="loading" @click="createJob">创建并刷新</button>
        </div>
      </div>
    </div>

    <div class="overflow-x-auto">
      <table class="table">
        <thead>
          <tr>
            <th>任务ID</th>
            <th>状态</th>
            <th>过滤条件</th>
            <th>创建时间</th>
            <th>错误信息</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody v-if="jobs.length > 0">
          <tr v-for="row in jobs" :key="row.id">
            <td class="max-w-48 truncate">{{ row.id }}</td>
            <td>
              <span
                class="badge"
                :class="row.status === 'SUCCESS' ? 'badge-success' : row.status === 'FAILED' ? 'badge-error' : 'badge-warning'"
              >
                {{ statusLabel(row.status) }}
              </span>
            </td>
            <td class="max-w-48 truncate">{{ JSON.stringify(row.filters || {}) }}</td>
            <td>{{ row.created_at }}</td>
            <td class="max-w-48 truncate">{{ row.error_message || '-' }}</td>
            <td>
              <button class="btn btn-xs btn-info" :disabled="row.status !== 'SUCCESS'" @click="downloadJob(row)">下载</button>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr>
            <td colspan="6" class="text-center">暂无导出任务</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
