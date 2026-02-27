import type { IPersonConfig } from '@/types/storeType'
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'vue-toast-notification'
import { apiDrawWinnerList, apiExportJobCreate, apiExportJobDownload, apiPrizeList, apiRevokeWinner } from '@/api/lottery'
import i18n from '@/locales/i18n'
import { getSelectedProjectId } from '@/utils/session'
import { tableColumns } from './columns'

type WinnerTableRow = IPersonConfig & { winnerIds: string[] }

function buildErrorMessage(error: any, fallback: string) {
    return error?.message || error?.detail || error?.msg || fallback
}

export function useViewModel() {
    const toast = useToast()
    const isDetail = ref(false)
    const summaryRows = ref<WinnerTableRow[]>([])
    const detailRows = ref<WinnerTableRow[]>([])

    function selectedProjectId() {
        const projectId = getSelectedProjectId()
        if (!projectId)
            throw new Error('未选择项目，请先选择项目')
        return projectId
    }

    async function refreshData() {
        const projectId = selectedProjectId()
        const [winners, prizes] = await Promise.all([
            apiDrawWinnerList({ project_id: projectId, status: 'CONFIRMED' }),
            apiPrizeList(projectId),
        ])

        const prizeNameMap = new Map<string, string>()
        prizes.forEach((prize) => {
            prizeNameMap.set(prize.id, prize.name)
        })

        detailRows.value = winners.map((winner, index) => ({
            id: index + 1,
            uid: winner.uid,
            uuid: winner.id,
            name: winner.name,
            phone: winner.phone,
            isWin: true,
            x: 0,
            y: 0,
            createTime: winner.created_at,
            updateTime: winner.created_at,
            prizeName: [prizeNameMap.get(winner.prize) || winner.prize],
            prizeId: [winner.prize],
            prizeTime: winner.confirmed_at ? [winner.confirmed_at] : [],
            winnerIds: [winner.id],
        }))

        const summaryMap = new Map<string, WinnerTableRow>()
        detailRows.value.forEach((row) => {
            if (!summaryMap.has(row.phone)) {
                summaryMap.set(row.phone, {
                    id: summaryMap.size + 1,
                    uid: row.uid,
                    uuid: row.phone,
                    name: row.name,
                    phone: row.phone,
                    isWin: true,
                    x: 0,
                    y: 0,
                    createTime: row.createTime,
                    updateTime: row.updateTime,
                    prizeName: [...row.prizeName],
                    prizeId: [...row.prizeId],
                    prizeTime: [...row.prizeTime],
                    winnerIds: [...row.winnerIds],
                })
                return
            }
            const current = summaryMap.get(row.phone)!
            row.prizeName.forEach((name) => {
                if (!current.prizeName.includes(name))
                    current.prizeName.push(name)
            })
            row.prizeId.forEach((prizeId) => {
                if (!current.prizeId.includes(prizeId))
                    current.prizeId.push(prizeId)
            })
            row.prizeTime.forEach((time) => {
                if (!current.prizeTime.includes(time))
                    current.prizeTime.push(time)
            })
            current.winnerIds.push(...row.winnerIds)
        })

        summaryRows.value = Array.from(summaryMap.values())
    }

    async function handleMoveNotPerson(row: IPersonConfig) {
        try {
            const winnerRow = row as WinnerTableRow
            if (!winnerRow.winnerIds?.length) {
                toast.error('未找到可撤销的中奖记录')
                return
            }
            await Promise.all(
                winnerRow.winnerIds.map(winnerId =>
                    apiRevokeWinner(winnerId, '后台撤销中奖记录'),
                ),
            )
            await refreshData()
            toast.success(i18n.global.t('error.success'))
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, i18n.global.t('error.fail')))
        }
    }

    function exportExcel() {
        apiExportJobCreate({
            project_id: selectedProjectId(),
            status: 'CONFIRMED',
        })
            .then(async (job) => {
                const blob = await apiExportJobDownload(job.id)
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `${i18n.global.t('viewTitle.winnerManagement')}-${new Date().getTime()}.csv`
                a.click()
                window.URL.revokeObjectURL(url)
                toast.success(i18n.global.t('error.success'))
            })
            .catch((error: any) => {
                toast.error(buildErrorMessage(error, i18n.global.t('error.fail')))
            })
    }

    const alreadyPersonList = computed(() => summaryRows.value)
    const alreadyPersonDetail = computed(() => detailRows.value)
    const tableColumnsList = tableColumns({ showPrizeTime: false, handleDeletePerson: handleMoveNotPerson })
    const tableColumnsDetail = tableColumns({ showPrizeTime: true, handleDeletePerson: handleMoveNotPerson })

    onMounted(() => {
        refreshData().catch((error: any) => {
            toast.error(buildErrorMessage(error, '加载中奖名单失败'))
        })
    })

    return {
        alreadyPersonList,
        alreadyPersonDetail,
        isDetail,
        tableColumnsList,
        tableColumnsDetail,
        exportExcel,
    }
}
