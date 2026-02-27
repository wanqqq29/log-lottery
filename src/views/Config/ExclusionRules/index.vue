<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useToast } from 'vue-toast-notification'
import {
    apiExclusionRuleCreate,
    apiExclusionRuleDelete,
    apiExclusionRuleList,
    apiExclusionRuleUpdate,
    apiPrizeList,
    type BackendExclusionRule,
    type BackendPrize,
} from '@/api/lottery'
import { apiProjectList, type ProjectItem } from '@/api/project'
import PageHeader from '@/components/PageHeader/index.vue'
import { getSelectedProjectId, getSelectedProjectName } from '@/utils/session'

interface RuleRow {
    id: string
    source_project_id: string
    source_project_name: string
    source_prize_id: string | null
    source_prize_name: string
    target_project_id: string
    target_project_name: string
    target_prize_id: string | null
    target_prize_name: string
    is_enabled: boolean
    description: string
    mode: string
}

function buildErrorMessage(error: any, fallback: string) {
    return error?.message || error?.detail || error?.msg || fallback
}

const toast = useToast()
const loading = ref(false)
const rules = ref<RuleRow[]>([])
const projects = ref<ProjectItem[]>([])
const prizesByProject = ref<Record<string, BackendPrize[]>>({})
const selectedProjectId = ref(getSelectedProjectId())
const selectedProjectName = ref(getSelectedProjectName() || '当前项目')

const form = ref({
    source_project: '',
    source_prize: '',
    target_prize: '',
    description: '',
})

const sourceProjectOptions = computed(() => {
    return projects.value.filter(project => project.id !== selectedProjectId.value && project.is_active)
})

const sourcePrizeOptions = computed(() => {
    return prizesByProject.value[form.value.source_project] || []
})

const targetPrizeOptions = computed(() => {
    return prizesByProject.value[selectedProjectId.value] || []
})

function prizeNameById(prizeId: string | null | undefined) {
    if (!prizeId)
        return '全部奖项'
    for (const list of Object.values(prizesByProject.value)) {
        const found = list.find(item => item.id === prizeId)
        if (found)
            return found.name
    }
    return prizeId
}

function projectNameById(projectId: string) {
    const found = projects.value.find(item => item.id === projectId)
    return found?.name || projectId
}

function mapRule(rule: BackendExclusionRule): RuleRow {
    return {
        id: rule.id,
        source_project_id: rule.source_project,
        source_project_name: projectNameById(rule.source_project),
        source_prize_id: rule.source_prize,
        source_prize_name: prizeNameById(rule.source_prize),
        target_project_id: rule.target_project,
        target_project_name: projectNameById(rule.target_project),
        target_prize_id: rule.target_prize,
        target_prize_name: prizeNameById(rule.target_prize),
        is_enabled: rule.is_enabled,
        description: rule.description || '',
        mode: rule.mode,
    }
}

async function loadProjectsAndPrizes() {
    projects.value = await apiProjectList()
    const activeProjectIds = projects.value.filter(item => item.is_active).map(item => item.id)
    const prizeResults = await Promise.all(
        activeProjectIds.map(async (projectId) => {
            const list = await apiPrizeList(projectId)
            return { projectId, list }
        }),
    )
    const mapping: Record<string, BackendPrize[]> = {}
    prizeResults.forEach(({ projectId, list }) => {
        mapping[projectId] = list.filter(item => item.is_active)
    })
    prizesByProject.value = mapping
}

async function loadRules() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    const list = await apiExclusionRuleList(selectedProjectId.value)
    rules.value = list.map(mapRule)
}

async function refreshAll() {
    loading.value = true
    try {
        await loadProjectsAndPrizes()
        await loadRules()
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '加载排除规则失败'))
    }
    finally {
        loading.value = false
    }
}

async function createRule() {
    if (!selectedProjectId.value) {
        toast.error('未选择项目，请先选择项目')
        return
    }
    if (!form.value.source_project) {
        toast.error('请选择来源项目')
        return
    }

    try {
        await apiExclusionRuleCreate({
            source_project: form.value.source_project,
            source_prize: form.value.source_prize || null,
            target_project: selectedProjectId.value,
            target_prize: form.value.target_prize || null,
            mode: 'EXCLUDE_SOURCE_WINNERS',
            is_enabled: true,
            description: form.value.description || '',
        })
        form.value = {
            source_project: '',
            source_prize: '',
            target_prize: '',
            description: '',
        }
        await loadRules()
        toast.success('新增排除规则成功')
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '新增规则失败'))
    }
}

async function toggleRule(row: RuleRow) {
    try {
        await apiExclusionRuleUpdate(row.id, { is_enabled: !row.is_enabled })
        await loadRules()
        toast.success('规则状态已更新')
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '更新规则失败'))
    }
}

async function deleteRule(row: RuleRow) {
    try {
        await apiExclusionRuleDelete(row.id)
        await loadRules()
        toast.success('删除规则成功')
    }
    catch (error: any) {
        toast.error(buildErrorMessage(error, '删除规则失败'))
    }
}

watch(
    () => form.value.source_project,
    () => {
        form.value.source_prize = ''
    },
)

onMounted(() => {
    refreshAll()
})
</script>

<template>
  <div>
    <PageHeader title="排除规则">
      <template #buttons>
        <div class="flex items-center gap-3">
          <span class="text-sm opacity-70">当前项目：{{ selectedProjectName }}</span>
          <button class="btn btn-sm btn-outline" :disabled="loading" @click="refreshAll">刷新</button>
        </div>
      </template>
      <template #alerts>
        <div role="alert" class="w-full my-3 alert alert-info">
          <span>说明：规则只作用于当前项目。可以排除来源项目已中奖用户，支持按来源奖项/目标奖项细分。</span>
        </div>
      </template>
    </PageHeader>

    <div class="p-4 mb-4 border rounded-lg border-base-300 bg-base-200">
      <h3 class="mb-3 text-sm font-semibold">新增规则</h3>
      <div class="grid grid-cols-1 gap-3 md:grid-cols-4">
        <label class="form-control">
          <span class="label-text">来源项目</span>
          <select v-model="form.source_project" class="select select-bordered select-sm">
            <option value="">请选择</option>
            <option v-for="project in sourceProjectOptions" :key="project.id" :value="project.id">
              {{ project.name }} ({{ project.code }})
            </option>
          </select>
        </label>

        <label class="form-control">
          <span class="label-text">来源奖项（可选）</span>
          <select v-model="form.source_prize" class="select select-bordered select-sm">
            <option value="">全部奖项</option>
            <option v-for="prize in sourcePrizeOptions" :key="prize.id" :value="prize.id">
              {{ prize.name }}
            </option>
          </select>
        </label>

        <label class="form-control">
          <span class="label-text">目标奖项（可选）</span>
          <select v-model="form.target_prize" class="select select-bordered select-sm">
            <option value="">当前项目全部奖项</option>
            <option v-for="prize in targetPrizeOptions" :key="prize.id" :value="prize.id">
              {{ prize.name }}
            </option>
          </select>
        </label>

        <label class="form-control">
          <span class="label-text">说明</span>
          <input v-model="form.description" class="input input-bordered input-sm" type="text" placeholder="例如：A 项目一等奖排除">
        </label>
      </div>
      <div class="mt-3">
        <button class="btn btn-primary btn-sm" :disabled="loading" @click="createRule">新增规则</button>
      </div>
    </div>

    <div class="overflow-x-auto">
      <table class="table">
        <thead>
          <tr>
            <th>来源项目</th>
            <th>来源奖项</th>
            <th>目标项目</th>
            <th>目标奖项</th>
            <th>状态</th>
            <th>说明</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody v-if="rules.length > 0">
          <tr v-for="row in rules" :key="row.id">
            <td>{{ row.source_project_name }}</td>
            <td>{{ row.source_prize_name }}</td>
            <td>{{ row.target_project_name }}</td>
            <td>{{ row.target_prize_name }}</td>
            <td>
              <span class="badge" :class="row.is_enabled ? 'badge-success' : 'badge-ghost'">
                {{ row.is_enabled ? '启用' : '停用' }}
              </span>
            </td>
            <td>{{ row.description || '-' }}</td>
            <td class="flex gap-2">
              <button class="btn btn-xs btn-info" @click="toggleRule(row)">{{ row.is_enabled ? '停用' : '启用' }}</button>
              <button class="btn btn-xs btn-error" @click="deleteRule(row)">删除</button>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr>
            <td colspan="7" class="text-center">暂无规则</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
