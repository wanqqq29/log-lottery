<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toast-notification'
import {
    apiArrivalVisitList,
    apiDrawWinnerList,
    apiPrizeList,
    apiRegisterArrivalVisit,
    type BackendDrawWinner,
    type BackendPrize,
} from '@/api/lottery'
import { getSelectedProjectId, getSelectedProjectName } from '@/utils/session'

function buildErrorMessage(error: any, fallback: string) {
    return error?.message || error?.detail || error?.msg || fallback
}

function normalizePhone(value: string) {
    return value.replace(/\D/g, '')
}

function sortWinners(rows: BackendDrawWinner[]) {
    return rows
        .slice()
        .sort((a, b) => {
            const aTime = a.confirmed_at || a.created_at
            const bTime = b.confirmed_at || b.created_at
            return new Date(bTime).getTime() - new Date(aTime).getTime()
        })
}

const ARRIVAL_REWARD_PRIZE_NAME = '到访奖励'

const router = useRouter()
const toast = useToast()
const baseLoading = ref(false)
const searchLoading = ref(false)
const submitLoading = ref(false)
const recordsLoading = ref(false)
const selectedProjectId = ref(getSelectedProjectId())
const selectedProjectName = ref(getSelectedProjectName() || '当前项目')
const prizes = ref<BackendPrize[]>([])
const winnerMatches = ref<BackendDrawWinner[]>([])
const visitRecords = ref<BackendDrawWinner[]>([])
const searchExecuted = ref(false)
const searchedPhone = ref('')

const form = ref({
    phone: '',
    name: '',
    prize_id: '',
    is_prize_claimed: true,
    claim_note: '',
})

const selectablePrizes = computed(() =>
    prizes.value.filter(item => item.is_active && item.name !== ARRIVAL_REWARD_PRIZE_NAME),
)

const prizeNameMap = computed(() => {
    const mapping = new Map<string, string>()
    prizes.value.forEach((prize) => {
        mapping.set(prize.id, prize.name)
    })
    return mapping
})

async function loadRecentVisits() {
    if (!selectedProjectId.value) {
        return
    }
    recordsLoading.value = true
    try {
        const rows = await apiArrivalVisitList({
            project_id: selectedProjectId.value,
            limit: 20,
        })
        visitRecords.value = sortWinners(rows)
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '加载到访记录失败'))
    }
    finally {
        recordsLoading.value = false
    }
}

async function loadBaseData() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    baseLoading.value = true
    try {
        const [prizeList] = await Promise.all([
            apiPrizeList(selectedProjectId.value),
            loadRecentVisits(),
        ])
        prizes.value = prizeList
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '加载数据失败'))
    }
    finally {
        baseLoading.value = false
    }
}

async function queryWinnersByPhone(phone: string, silent = false) {
    if (!selectedProjectId.value) {
        return
    }
    const rows = await apiDrawWinnerList({
        project_id: selectedProjectId.value,
        status: 'CONFIRMED',
        phone,
    })
    winnerMatches.value = sortWinners(rows)
    searchExecuted.value = true
    searchedPhone.value = phone
    if (winnerMatches.value.length > 0) {
        if (!form.value.name.trim()) {
            form.value.name = winnerMatches.value[0].name || ''
        }
        if (!form.value.prize_id) {
            form.value.prize_id = winnerMatches.value[0].prize
        }
        if (!silent) {
            toast.success(`查到 ${winnerMatches.value.length} 条中奖记录`)
        }
        return
    }
    form.value.prize_id = ''
    if (!silent) {
        toast.info('未查到中奖记录，也可以直接登记到访')
    }
}

async function searchWinner() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    const phone = normalizePhone(form.value.phone)
    if (!phone) {
        toast.error('请输入手机号')
        return
    }
    form.value.phone = phone
    searchLoading.value = true
    try {
        await queryWinnersByPhone(phone)
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '查询中奖失败'))
    }
    finally {
        searchLoading.value = false
    }
}

async function submitVisit() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    const phone = normalizePhone(form.value.phone)
    if (!phone) {
        toast.error('请输入手机号')
        return
    }
    form.value.phone = phone

    submitLoading.value = true
    try {
        const result = await apiRegisterArrivalVisit({
            project_id: selectedProjectId.value,
            phone,
            name: form.value.name.trim() || undefined,
            prize_id: form.value.prize_id || undefined,
            is_prize_claimed: form.value.is_prize_claimed,
            claim_note: form.value.claim_note.trim(),
        })
        const prizeName = prizeNameMap.value.get(result.prize) || ''
        if (prizeName === ARRIVAL_REWARD_PRIZE_NAME) {
            toast.success('已新增到访奖励中奖记录')
        }
        else {
            toast.success('已登记中奖客户到访')
        }
        form.value.claim_note = ''
        await Promise.all([
            queryWinnersByPhone(phone, true),
            loadRecentVisits(),
        ])
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '登记失败'))
    }
    finally {
        submitLoading.value = false
    }
}

function gotoProjectSelect() {
    router.push('/log-lottery/project-select')
}

onMounted(() => {
    loadBaseData()
})
</script>

<template>
  <div class="min-h-screen bg-base-100">
    <div class="max-w-md px-3 py-4 mx-auto">
      <div class="mb-4">
        <h1 class="text-xl font-bold">手机到访登记</h1>
        <p class="mt-1 text-xs opacity-70">先按手机号查中奖，再登记到访。未中奖客户也可登记领礼品。</p>
      </div>

      <div class="p-3 mb-4 border rounded-xl border-base-300 bg-base-200">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium">当前项目</span>
          <button class="btn btn-xs btn-outline" :disabled="baseLoading || submitLoading" @click="loadBaseData">刷新</button>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <span class="badge badge-outline">{{ selectedProjectName || '-' }}</span>
          <button v-if="!selectedProjectId" class="btn btn-xs btn-warning" @click="gotoProjectSelect">去选择项目</button>
        </div>
      </div>

      <div class="p-3 mb-4 border rounded-xl border-base-300 bg-base-200">
        <h3 class="mb-2 text-sm font-semibold">1. 手机号查询中奖</h3>
        <label class="form-control mb-2">
          <span class="label-text text-sm">手机号</span>
          <div class="flex gap-2">
            <input
              v-model="form.phone"
              class="input input-bordered text-base flex-1"
              maxlength="20"
              inputmode="numeric"
              placeholder="请输入手机号"
              @keyup.enter="searchWinner"
            >
            <button class="btn btn-primary" :disabled="searchLoading" @click="searchWinner">
              {{ searchLoading ? '查询中' : '查询' }}
            </button>
          </div>
        </label>

        <div v-if="searchExecuted" class="mt-2">
          <div v-if="winnerMatches.length > 0" class="space-y-2">
            <div
              v-for="row in winnerMatches"
              :key="row.id"
              class="p-2 border rounded-lg border-success/40 bg-success/10"
            >
              <div class="flex items-center justify-between text-sm">
                <span class="font-medium">{{ row.name || '-' }}</span>
                <span>{{ row.phone }}</span>
              </div>
              <div class="mt-1 text-xs opacity-80">
                中奖：{{ prizeNameMap.get(row.prize) || row.prize }} | {{ row.confirmed_at || '-' }}
              </div>
            </div>
          </div>
          <div v-else class="p-2 text-sm border rounded-lg border-warning/40 bg-warning/10">
            未查到中奖记录。可以继续登记“到访领取礼品”。
          </div>
        </div>
      </div>

      <div class="p-3 mb-4 border rounded-xl border-base-300 bg-base-200">
        <h3 class="mb-2 text-sm font-semibold">2. 到访登记</h3>
        <label class="form-control mb-2">
          <span class="label-text text-sm">姓名（未中奖客户可填写）</span>
          <input v-model="form.name" class="input input-bordered" maxlength="128" placeholder="可选" />
        </label>
        <label class="form-control mb-2">
          <span class="label-text text-sm">奖项（可选）</span>
          <select v-model="form.prize_id" class="select select-bordered">
            <option value="">自动匹配/留空</option>
            <option v-for="prize in selectablePrizes" :key="prize.id" :value="prize.id">
              {{ prize.name }}
            </option>
          </select>
        </label>
        <div class="mb-2">
          <p class="mb-1 text-sm">本次是否领到礼品</p>
          <div class="grid grid-cols-2 gap-2">
            <button
              class="btn"
              :class="form.is_prize_claimed ? 'btn-success' : 'btn-outline'"
              type="button"
              @click="form.is_prize_claimed = true"
            >
              已领取
            </button>
            <button
              class="btn"
              :class="!form.is_prize_claimed ? 'btn-warning' : 'btn-outline'"
              type="button"
              @click="form.is_prize_claimed = false"
            >
              未领取
            </button>
          </div>
        </div>
        <label class="form-control mb-3">
          <span class="label-text text-sm">备注（可空）</span>
          <textarea
            v-model="form.claim_note"
            class="textarea textarea-bordered h-20"
            maxlength="255"
            placeholder="例如：未中奖到访礼品、代领等"
          />
        </label>
        <button class="btn btn-primary btn-lg w-full" :disabled="submitLoading" @click="submitVisit">
          {{ submitLoading ? '提交中...' : '提交到访登记' }}
        </button>
      </div>

      <div class="p-3 border rounded-xl border-base-300">
        <h3 class="mb-2 text-sm font-semibold">最近到访登记</h3>
        <div v-if="recordsLoading" class="py-5 text-sm text-center opacity-60">
          加载中...
        </div>
        <div v-else-if="visitRecords.length > 0" class="space-y-2">
          <div
            v-for="row in visitRecords"
            :key="row.id"
            class="p-2 border rounded-lg border-base-300 bg-base-200"
          >
            <div class="flex items-center justify-between text-sm">
              <span class="font-medium">{{ row.name || '-' }}</span>
              <span>{{ row.phone }}</span>
            </div>
            <div class="mt-1 text-xs opacity-75">
              {{ prizeNameMap.get(row.prize) === ARRIVAL_REWARD_PRIZE_NAME ? '到访奖励中奖' : '中奖客户到访' }}
              <span v-if="row.prize"> | {{ prizeNameMap.get(row.prize) || row.prize }}</span>
              | {{ row.visited_at }}
            </div>
            <div class="flex gap-2 mt-2">
              <span class="badge badge-sm" :class="row.is_prize_claimed ? 'badge-success' : 'badge-warning'">
                {{ row.is_prize_claimed ? '已领取礼品' : '未领取礼品' }}
              </span>
            </div>
          </div>
        </div>
        <div v-else class="py-5 text-sm text-center opacity-60">
          暂无到访登记
        </div>
      </div>

      <div v-if="searchedPhone" class="mt-4 text-[11px] opacity-60">
        最近查询手机号：{{ searchedPhone }}
      </div>
    </div>
  </div>
</template>
