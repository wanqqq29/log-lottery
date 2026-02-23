import type { IPersonConfig } from '@/types/storeType'
import { storeToRefs } from 'pinia'
import { ref } from 'vue'
import { useToast } from 'vue-toast-notification'
import * as XLSX from 'xlsx'
import i18n from '@/locales/i18n'
import useStore from '@/store'
import { tableColumns } from './columns'

export function useViewModel() {
    const personConfig = useStore().personConfig
    const toast = useToast()

    const { getAlreadyPersonList: alreadyPersonList, getAlreadyPersonDetail: alreadyPersonDetail } = storeToRefs(personConfig)

    const isDetail = ref(false)
    function handleMoveNotPerson(row: IPersonConfig) {
        personConfig.moveAlreadyToNot(row)
    }

    function exportExcel() {
        try {
            const data = isDetail.value ? alreadyPersonDetail.value : alreadyPersonList.value
            const exportData = data.map((item: any) => {
                return {
                    [i18n.global.t('data.number')]: item.uid,
                    [i18n.global.t('data.name')]: item.name,
                    [i18n.global.t('data.phone')]: item.phone,
                    [i18n.global.t('data.prizeName')]: Array.isArray(item.prizeName) ? item.prizeName.join(',') : item.prizeName,
                    [i18n.global.t('data.prizeTime')]: Array.isArray(item.prizeTime) ? item.prizeTime.join(',') : item.prizeTime,
                }
            })
            const worksheet = XLSX.utils.json_to_sheet(exportData)
            const workbook = XLSX.utils.book_new()
            XLSX.utils.book_append_sheet(workbook, worksheet, 'Winners')
            XLSX.writeFile(workbook, `${i18n.global.t('viewTitle.winnerManagement')}-${new Date().getTime()}.xlsx`)
            toast.success(i18n.global.t('error.success'))
        }
        catch (error) {
            toast.error(String(error))
        }
    }

    const tableColumnsList = tableColumns({ showPrizeTime: false, handleDeletePerson: handleMoveNotPerson })
    const tableColumnsDetail = tableColumns({ showPrizeTime: true, handleDeletePerson: handleMoveNotPerson })
    return {
        alreadyPersonList,
        alreadyPersonDetail,
        isDetail,
        tableColumnsList,
        tableColumnsDetail,
        exportExcel,
    }
}
