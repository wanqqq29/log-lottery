<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'vue-toast-notification'
import { apiDrawWinnerDashboard, type DrawWinnerDashboardResp } from '@/api/lottery'
import PageHeader from '@/components/PageHeader/index.vue'
import { getSelectedProjectId, getSelectedProjectName } from '@/utils/session'

function buildErrorMessage(error: any, fallback: string) {
    return error?.message || error?.detail || error?.msg || fallback
}

const toast = useToast()
const loading = ref(false)
const selectedProjectId = ref(getSelectedProjectId())
const selectedProjectName = ref(getSelectedProjectName() || '当前项目')
const TREND_DAYS = 14
const dashboard = ref<DrawWinnerDashboardResp | null>(null)

const dailyArrivalMax = computed(() => {
    const rows = dashboard.value?.daily_stats || []
    return Math.max(1, ...rows.map(item => item.arrival_count))
})

const summaryCards = computed(() => {
    if (!dashboard.value) {
        return []
    }
    return [
        { label: '项目活跃成员', value: dashboard.value.members_total },
        { label: '确认中奖人数', value: dashboard.value.confirmed_winner_total },
        { label: '到访人数', value: dashboard.value.arrival_total },
        { label: '已领奖人数', value: dashboard.value.claimed_total },
        { label: '未领奖人数', value: dashboard.value.unclaimed_total },
        { label: '成员中奖率', value: `${dashboard.value.member_win_rate}%` },
        { label: '到访率', value: `${dashboard.value.arrival_rate}%` },
        { label: '领奖率', value: `${dashboard.value.claim_rate}%` },
    ]
})

async function loadDashboard() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    loading.value = true
    try {
        dashboard.value = await apiDrawWinnerDashboard({
            project_id: selectedProjectId.value,
            days: TREND_DAYS,
        })
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '加载运营看板失败'))
    }
    finally {
        loading.value = false
    }
}

onMounted(() => {
    loadDashboard()
})
</script>

<template>
  <div class="overflow-y-auto">
    <PageHeader title="运营看板">
      <template #buttons>
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <span class="badge badge-outline">项目：{{ selectedProjectName }}</span>
          <button class="btn btn-sm btn-outline" :disabled="loading" @click="loadDashboard">刷新</button>
        </div>
      </template>
      <template #alerts>
        <div role="alert" class="w-full my-3 alert alert-info">
          <span>重点关注：到访率、领奖率、各奖项未领奖积压和近14天到访趋势。</span>
        </div>
      </template>
    </PageHeader>

    <template v-if="dashboard">
      <div class="grid grid-cols-2 gap-3 mb-4 md:grid-cols-4">
        <div v-for="card in summaryCards" :key="card.label" class="p-3 border rounded-lg border-base-300 bg-base-200">
          <p class="mb-1 text-xs opacity-70">{{ card.label }}</p>
          <p class="text-xl font-semibold">{{ card.value }}</p>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 mb-4 xl:grid-cols-[1.3fr,1fr]">
        <div class="p-4 border rounded-xl border-base-300">
          <h3 class="mb-3 text-sm font-semibold">奖项维度监控</h3>
          <div class="overflow-x-auto">
            <table class="table table-sm">
              <thead>
                <tr>
                  <th>奖项</th>
                  <th>总名额</th>
                  <th>已用名额</th>
                  <th>已确认</th>
                  <th>已到访</th>
                  <th>已领奖</th>
                  <th>未领奖</th>
                  <th>领奖率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in dashboard.prize_stats" :key="row.prize_id">
                  <td>{{ row.prize_name }}</td>
                  <td>{{ row.total_quota }}</td>
                  <td>{{ row.used_quota }}</td>
                  <td>{{ row.confirmed_winner_count }}</td>
                  <td>{{ row.arrival_count }}</td>
                  <td>{{ row.claimed_count }}</td>
                  <td>
                    <span class="badge" :class="row.unclaimed_count > 0 ? 'badge-warning' : 'badge-success'">
                      {{ row.unclaimed_count }}
                    </span>
                  </td>
                  <td>{{ row.claim_rate }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="p-4 border rounded-xl border-base-300 bg-base-200">
          <h3 class="mb-3 text-sm font-semibold">总体转化</h3>
          <div class="mb-4">
            <div class="flex justify-between mb-1 text-sm">
              <span>到访率</span>
              <span>{{ dashboard.arrival_rate }}%</span>
            </div>
            <progress class="w-full progress progress-info" :value="dashboard.arrival_rate" max="100" />
          </div>
          <div>
            <div class="flex justify-between mb-1 text-sm">
              <span>领奖率</span>
              <span>{{ dashboard.claim_rate }}%</span>
            </div>
            <progress class="w-full progress progress-success" :value="dashboard.claim_rate" max="100" />
          </div>
        </div>
      </div>

      <div class="p-4 border rounded-xl border-base-300">
        <h3 class="mb-3 text-sm font-semibold">近14天到访趋势</h3>
        <div class="overflow-x-auto">
          <table class="table table-sm">
            <thead>
              <tr>
                <th>日期</th>
                <th>到访</th>
                <th>到访柱状</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in dashboard.daily_stats" :key="row.date">
                <td>{{ row.date }}</td>
                <td>{{ row.arrival_count }}</td>
                <td class="min-w-48">
                  <div class="w-full h-3 rounded-full bg-base-200">
                    <div
                      class="h-3 rounded-full bg-info"
                      :style="{ width: `${Math.round((row.arrival_count / dailyArrivalMax) * 100)}%` }"
                    />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
