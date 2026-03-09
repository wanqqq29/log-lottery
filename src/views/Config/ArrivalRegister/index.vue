<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'vue-toast-notification'
import { apiDrawWinnerList, apiPrizeList, apiRegisterWinnerArrival, type BackendDrawWinner, type BackendPrize } from '@/api/lottery'
import PageHeader from '@/components/PageHeader/index.vue'
import { getAuthUser, getSelectedProjectId, getSelectedProjectName } from '@/utils/session'

function buildErrorMessage(error: any, fallback: string) {
    return error?.message || error?.detail || error?.msg || fallback
}

function normalizePhone(value: string) {
    return value.replace(/\D/g, '')
}

const toast = useToast()
const loading = ref(false)
const submitLoading = ref(false)
const selectedProjectId = ref(getSelectedProjectId())
const selectedProjectName = ref(getSelectedProjectName() || '当前项目')
const authUser = ref(getAuthUser())
const prizes = ref<BackendPrize[]>([])
const winners = ref<BackendDrawWinner[]>([])

const form = ref({
    phone: '',
    prize_id: '',
    is_prize_claimed: true,
    claim_note: '',
})

const prizeNameMap = computed(() => {
    const mapping = new Map<string, string>()
    prizes.value.forEach((prize) => {
        mapping.set(prize.id, prize.name)
    })
    return mapping
})

const roleLabel = computed(() => {
    const role = authUser.value?.role || ''
    const mapping: Record<string, string> = {
        SUPER_ADMIN: '超级管理员',
        DEPT_ADMIN: '部门管理员',
        OPERATOR: '运营',
        VIEWER: '只读',
    }
    return mapping[role] || role || '-'
})

async function refreshData() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    loading.value = true
    try {
        const [prizeList, winnerList] = await Promise.all([
            apiPrizeList(selectedProjectId.value),
            apiDrawWinnerList({ project_id: selectedProjectId.value, status: 'CONFIRMED' }),
        ])
        prizes.value = prizeList.filter(item => item.is_active)
        winners.value = winnerList
            .slice()
            .sort((a, b) => {
                const aTime = a.confirmed_at || a.created_at
                const bTime = b.confirmed_at || b.created_at
                return new Date(bTime).getTime() - new Date(aTime).getTime()
            })
            .slice(0, 30)
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '加载数据失败'))
    }
    finally {
        loading.value = false
    }
}

async function submitRegister() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    const phone = normalizePhone(form.value.phone)
    if (!phone) {
        toast.error('请输入手机号')
        return
    }

    submitLoading.value = true
    try {
        await apiRegisterWinnerArrival({
            project_id: selectedProjectId.value,
            phone,
            prize_id: form.value.prize_id || undefined,
            is_prize_claimed: form.value.is_prize_claimed,
            claim_note: form.value.claim_note.trim(),
        })
        toast.success('登记成功')
        form.value.phone = ''
        form.value.prize_id = ''
        form.value.claim_note = ''
        await refreshData()
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '登记失败'))
    }
    finally {
        submitLoading.value = false
    }
}

onMounted(() => {
    refreshData()
})
</script>

<template>
  <div class="overflow-y-auto">
    <PageHeader title="到访领奖登记">
      <template #buttons>
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <span class="badge badge-outline">项目：{{ selectedProjectName }}</span>
          <span class="badge badge-outline">角色：{{ roleLabel }}</span>
          <button class="btn btn-sm btn-outline" :disabled="loading || submitLoading" @click="refreshData">刷新</button>
        </div>
      </template>
      <template #alerts>
        <div role="alert" class="w-full my-3 alert alert-info">
          <span>输入手机号即可登记真实到访；只读账号也允许执行登记操作。</span>
        </div>
      </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-[360px,1fr]">
      <div class="p-4 border rounded-xl border-base-300 bg-base-200">
        <h3 class="mb-3 text-sm font-semibold">登记表单</h3>
        <label class="form-control mb-3">
          <span class="label-text">手机号</span>
          <input
            v-model="form.phone"
            class="input input-bordered input-sm"
            maxlength="20"
            placeholder="例如 13800138000"
            @keyup.enter="submitRegister"
          >
        </label>
        <label class="form-control mb-3">
          <span class="label-text">奖项（可选）</span>
          <select v-model="form.prize_id" class="select select-bordered select-sm">
            <option value="">自动匹配该手机号最新中奖记录</option>
            <option v-for="prize in prizes" :key="prize.id" :value="prize.id">
              {{ prize.name }}
            </option>
          </select>
        </label>
        <label class="cursor-pointer label mb-3">
          <span class="label-text">本次已领取奖品</span>
          <input v-model="form.is_prize_claimed" type="checkbox" class="toggle toggle-primary">
        </label>
        <label class="form-control mb-4">
          <span class="label-text">备注（可选）</span>
          <textarea v-model="form.claim_note" class="textarea textarea-bordered h-20" maxlength="255" />
        </label>
        <button class="btn btn-primary btn-sm w-full" :disabled="submitLoading" @click="submitRegister">
          {{ submitLoading ? '提交中...' : '确认登记' }}
        </button>
      </div>

      <div class="p-4 border rounded-xl border-base-300">
        <h3 class="mb-3 text-sm font-semibold">最近已确认中奖记录（{{ winners.length }}）</h3>
        <div class="overflow-x-auto">
          <table class="table table-sm">
            <thead>
              <tr>
                <th>手机号</th>
                <th>姓名</th>
                <th>奖项</th>
                <th>确认时间</th>
                <th>到访</th>
                <th>领奖</th>
              </tr>
            </thead>
            <tbody v-if="winners.length > 0">
              <tr v-for="row in winners" :key="row.id">
                <td>{{ row.phone }}</td>
                <td>{{ row.name }}</td>
                <td>{{ prizeNameMap.get(row.prize) || row.prize }}</td>
                <td>{{ row.confirmed_at || '-' }}</td>
                <td>
                  <span class="badge" :class="row.is_visited ? 'badge-success' : 'badge-ghost'">
                    {{ row.is_visited ? '已到访' : '未到访' }}
                  </span>
                </td>
                <td>
                  <span class="badge" :class="row.is_prize_claimed ? 'badge-success' : 'badge-warning'">
                    {{ row.is_prize_claimed ? '已领奖' : '未领奖' }}
                  </span>
                </td>
              </tr>
            </tbody>
            <tbody v-else>
              <tr>
                <td colspan="6" class="text-center">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
