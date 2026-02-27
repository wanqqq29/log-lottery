import type { IPrizeConfig } from '@/types/storeType'
import { storeToRefs } from 'pinia'
import { onMounted, ref } from 'vue'
import { useToast } from 'vue-toast-notification'
import { apiPrizeCreate, apiPrizeDelete, apiPrizeList, apiPrizeUpdate, type BackendPrize } from '@/api/lottery'
import i18n from '@/locales/i18n'
import useStore from '@/store'
import { getSelectedProjectId } from '@/utils/session'

function buildErrorMessage(error: any, fallback: string) {
    return error?.message || error?.detail || error?.msg || fallback
}

function mapBackendPrizeToLocal(prize: BackendPrize): IPrizeConfig {
    const total = Number(prize.total_count || 0)
    const used = Number(prize.used_count || 0)
    return {
        id: prize.id,
        name: prize.name,
        sort: prize.sort || 0,
        isAll: Boolean(prize.is_all),
        count: total,
        isUsedCount: used,
        picture: {
            id: '',
            name: '',
            url: '',
        },
        separateCount: {
            enable: Boolean(prize.separate_count?.enable),
            countList: prize.separate_count?.countList || [],
        },
        desc: prize.description || '',
        isShow: Boolean(prize.is_active),
        isUsed: used >= total,
        frequency: 1,
    }
}

export function usePrizeConfig() {
    const toast = useToast()
    const prizeConfig = useStore().prizeConfig
    const globalConfig = useStore().globalConfig
    const { getCurrentPrize: currentPrize } = storeToRefs(prizeConfig)
    const { getImageList: localImageList } = storeToRefs(globalConfig)

    const prizeList = ref<IPrizeConfig[]>([])
    const selectedPrize = ref<IPrizeConfig | null>(null)

    function selectedProjectId() {
        const projectId = getSelectedProjectId()
        if (!projectId)
            throw new Error('未选择项目，请先选择项目')
        return projectId
    }

    async function loadPrizes() {
        const list = await apiPrizeList(selectedProjectId())
        prizeList.value = list
            .map(mapBackendPrizeToLocal)
            .sort((a, b) => a.sort - b.sort)
    }

    function toPrizePatch(item: IPrizeConfig, sort?: number) {
        return {
            name: item.name || i18n.global.t('data.prizeName'),
            sort: sort ?? item.sort ?? 0,
            is_all: Boolean(item.isAll),
            total_count: Math.max(Number(item.count || 1), 1),
            separate_count: {
                enable: Boolean(item.separateCount?.enable),
                countList: item.separateCount?.countList || [],
            },
            description: item.desc || '',
            is_active: Boolean(item.isShow),
        }
    }

    async function persistPrize(item: IPrizeConfig, sort?: number) {
        const prizeId = String(item.id)
        await apiPrizeUpdate(prizeId, toPrizePatch(item, sort))
    }

    async function selectPrize(item: IPrizeConfig) {
        selectedPrize.value = item
        selectedPrize.value.isUsedCount = item.isUsedCount || 0
        selectedPrize.value.isUsed = selectedPrize.value.isUsedCount >= selectedPrize.value.count
        if ((selectedPrize.value.separateCount?.countList?.length || 0) > 1) {
            return
        }
        selectedPrize.value.separateCount = {
            enable: true,
            countList: [
                {
                    id: '0',
                    count: item.count,
                    isUsedCount: item.isUsedCount || 0,
                },
            ],
        }
        await persistPrize(item)
    }

    function changePrizeStatus(item: IPrizeConfig) {
        item.isUsed = item.isUsedCount >= item.count
        toast.info('奖项完成状态由抽奖记录自动计算，不支持手动切换')
    }

    async function toggleFullParticipation(item: IPrizeConfig) {
        item.isAll = !item.isAll
        await persistPrize(item)
    }

    async function savePrize(item: IPrizeConfig) {
        try {
            if (item.count < item.isUsedCount) {
                item.count = item.isUsedCount
            }
            item.isUsed = item.isUsedCount >= item.count
            await persistPrize(item)
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, i18n.global.t('error.fail')))
            await loadPrizes()
        }
    }

    async function changePrizePerson(item: IPrizeConfig) {
        if (!item.count || item.count < 1) {
            item.count = 1
        }
        if (item.count < item.isUsedCount) {
            item.count = item.isUsedCount
            toast.info('奖项总人数不能小于已中奖人数')
        }
        item.separateCount.countList = []
        item.isUsed = item.isUsedCount >= item.count
        await savePrize(item)
    }

    async function submitData(value: any) {
        if (!selectedPrize.value)
            return
        selectedPrize.value.separateCount.countList = value
        await savePrize(selectedPrize.value)
        selectedPrize.value = null
    }

    async function delItem(item: IPrizeConfig) {
        try {
            await apiPrizeDelete(String(item.id))
            await loadPrizes()
            toast.success(i18n.global.t('error.deleteSuccess'))
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, i18n.global.t('error.fail')))
        }
    }

    async function addPrize() {
        try {
            const created = await apiPrizeCreate({
                project: selectedProjectId(),
                name: i18n.global.t('data.prizeName'),
                sort: prizeList.value.length + 1,
                is_all: false,
                total_count: 1,
                separate_count: {
                    enable: false,
                    countList: [],
                },
                description: '',
                is_active: true,
            })
            prizeList.value.push(mapBackendPrizeToLocal(created))
            prizeList.value = prizeList.value.sort((a, b) => a.sort - b.sort)
            toast.success(i18n.global.t('error.success'))
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, i18n.global.t('error.fail')))
        }
    }

    async function resetDefault() {
        try {
            await loadPrizes()
            toast.success(i18n.global.t('error.success'))
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, i18n.global.t('error.fail')))
        }
    }

    async function delAll() {
        try {
            const ids = prizeList.value.map(item => String(item.id))
            await Promise.all(ids.map(id => apiPrizeDelete(id)))
            prizeList.value = []
            toast.success(i18n.global.t('error.success'))
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, i18n.global.t('error.fail')))
        }
    }

    async function handleSortChange() {
        try {
            const requests = prizeList.value.map((item, index) => {
                item.sort = index + 1
                return persistPrize(item, index + 1)
            })
            await Promise.all(requests)
            await loadPrizes()
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, i18n.global.t('error.fail')))
            await loadPrizes()
        }
    }

    onMounted(() => {
        loadPrizes().catch((error: any) => {
            toast.error(buildErrorMessage(error, '加载奖项失败'))
        })
    })

    return {
        addPrize,
        resetDefault,
        delAll,
        delItem,
        prizeList,
        currentPrize,
        selectedPrize,
        submitData,
        changePrizePerson,
        changePrizeStatus,
        selectPrize,
        localImageList,
        savePrize,
        toggleFullParticipation,
        handleSortChange,
    }
}
