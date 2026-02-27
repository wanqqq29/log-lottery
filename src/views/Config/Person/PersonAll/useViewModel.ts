import type { Ref } from 'vue'
import type { IPersonConfig } from '@/types/storeType'
import { computed, inject, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toast-notification'
import * as XLSX from 'xlsx'
import {
    apiClearProjectMembers,
    apiDrawWinnerList,
    apiProjectMemberBulkUpsert,
    apiProjectMemberCreate,
    apiProjectMemberDelete,
    apiProjectMemberList,
    apiPrizeList,
    apiResetProjectWinners,
    type BackendProjectMember,
} from '@/api/lottery'
import { loadingKey } from '@/components/Loading'
import i18n from '@/locales/i18n'
import { getSelectedProjectId } from '@/utils/session'
import { readFileBinary, readLocalFileAsArraybuffer } from '@/utils/file'
import { tableColumns } from './columns'
import ImportExcelWorker from './importExcel.worker?worker'

type IBasePersonConfig = Pick<IPersonConfig, 'uid' | 'name' | 'phone'>
type PersonTableRow = IPersonConfig & { memberId: number, winnerIds: string[] }

function buildErrorMessage(error: any, fallback: string) {
    return error?.message || error?.detail || error?.msg || fallback
}

function mapMemberToPerson(member: BackendProjectMember, index: number): PersonTableRow {
    return {
        id: member.id || index + 1,
        uid: member.uid,
        uuid: String(member.id),
        name: member.name,
        phone: member.phone,
        isWin: false,
        x: 0,
        y: 0,
        createTime: member.created_at,
        updateTime: member.updated_at,
        prizeName: [],
        prizeId: [],
        prizeTime: [],
        memberId: member.id,
        winnerIds: [],
    }
}

export function useViewModel({ exportInputFileRef }: { exportInputFileRef: Ref<HTMLInputElement> }) {
    const { t } = useI18n()
    const baseUrl = import.meta.env.BASE_URL.replace('./', '/')
    const toast = useToast()
    const worker: Worker | null = new ImportExcelWorker()
    const loading = inject(loadingKey)
    const tableRows = ref<PersonTableRow[]>([])
    const tableColumnList = tableColumns({ handleDeletePerson: delPersonItem })
    const addPersonModalVisible = ref(false)
    const singlePersonData = ref<IBasePersonConfig>({
        uid: '',
        name: '',
        phone: '',
    })

    const allPersonList = computed(() => tableRows.value)
    const alreadyPersonList = computed(() => tableRows.value.filter(item => item.isWin))

    function selectedProjectId() {
        const projectId = getSelectedProjectId()
        if (!projectId)
            throw new Error('未选择项目，请先选择项目')
        return projectId
    }

    async function refreshData() {
        const projectId = selectedProjectId()
        const [members, winners, prizes] = await Promise.all([
            apiProjectMemberList(projectId),
            apiDrawWinnerList({ project_id: projectId, status: 'CONFIRMED' }),
            apiPrizeList(projectId),
        ])

        const rows = members
            .filter(item => item.is_active)
            .map(mapMemberToPerson)

        const winnerByPhone = new Map<string, {
            prizeIds: Set<string>
            winnerIds: string[]
            times: string[]
        }>()
        winners.forEach((winner) => {
            if (!winnerByPhone.has(winner.phone)) {
                winnerByPhone.set(winner.phone, {
                    prizeIds: new Set<string>(),
                    winnerIds: [],
                    times: [],
                })
            }
            const current = winnerByPhone.get(winner.phone)!
            current.prizeIds.add(winner.prize)
            current.winnerIds.push(winner.id)
            if (winner.confirmed_at)
                current.times.push(winner.confirmed_at)
        })

        const prizeIdNameMap = new Map<string, string>()
        prizes.forEach((prize) => {
            prizeIdNameMap.set(prize.id, prize.name)
        })

        rows.forEach((row) => {
            const winnerInfo = winnerByPhone.get(row.phone)
            if (!winnerInfo)
                return
            row.isWin = true
            row.prizeId = Array.from(winnerInfo.prizeIds)
            row.prizeName = row.prizeId.map(prizeId => prizeIdNameMap.get(prizeId) || prizeId)
            row.prizeTime = winnerInfo.times
            row.winnerIds = winnerInfo.winnerIds
        })

        tableRows.value = rows
    }

    async function getExcelTemplateContent() {
        const locale = i18n.global.locale.value
        if (locale === 'zhCn') {
            const templateData = await readLocalFileAsArraybuffer(`${baseUrl}人口登记表-zhCn.xlsx`)
            return templateData
        }
        const templateData = await readLocalFileAsArraybuffer(`${baseUrl}personListTemplate-en.xlsx`)
        return templateData
    }

    function sendWorkerMessage(message: any) {
        if (worker) {
            worker.postMessage(message)
        }
    }

    async function startWorker(data: string) {
        loading?.show()
        sendWorkerMessage({ type: 'start', data, templateData: await getExcelTemplateContent() })
    }

    async function handleFileChange(e: Event) {
        if (worker) {
            worker.onmessage = async (event) => {
                try {
                    if (event.data.type === 'done') {
                        const importedData: IPersonConfig[] = event.data.data
                        const projectId = selectedProjectId()
                        const members = importedData
                            .filter(item => item.phone && item.name)
                            .map(item => ({
                                uid: item.uid || item.phone,
                                name: item.name,
                                phone: item.phone,
                                is_active: true,
                            }))

                        if (!members.length) {
                            toast.open({
                                message: t('error.noNewRecords'),
                                type: 'info',
                                position: 'top-right',
                            })
                            return
                        }

                        const result = await apiProjectMemberBulkUpsert({
                            project_id: projectId,
                            members,
                        })
                        await refreshData()
                        toast.open({
                            message: `${t('error.importSuccess')} (${result.created_count}/${result.updated_count})`,
                            type: 'success',
                            position: 'top-right',
                        })
                        clearFileInput()
                    }
                    if (event.data.type === 'error') {
                        if (event.data.message === 'not right template') {
                            toast.open({
                                message: t('error.excelFileError'),
                                type: 'error',
                                position: 'top-right',
                            })
                            return
                        }
                        toast.open({
                            message: event.data.message || t('error.importFail'),
                            type: 'error',
                            position: 'top-right',
                        })
                    }
                }
                catch (error: any) {
                    toast.open({
                        message: buildErrorMessage(error, t('error.importFail')),
                        type: 'error',
                        position: 'top-right',
                    })
                }
                finally {
                    loading?.hide()
                }
            }
        }

        const dataBinary = await readFileBinary(((e.target as HTMLInputElement).files as FileList)[0]!)
        startWorker(dataBinary)
    }

    function clearFileInput() {
        if (exportInputFileRef.value) {
            exportInputFileRef.value.value = ''
        }
    }

    function downloadTemplate() {
        const templateFileName = i18n.global.t('data.xlsxName')
        const fileUrl = `${baseUrl}${templateFileName}`
        fetch(fileUrl)
            .then(res => res.blob())
            .then((blob) => {
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = templateFileName
                a.click()
                toast.open({
                    message: t('error.downloadSuccess'),
                    type: 'success',
                    position: 'top-right',
                })
            })
    }

    function exportData() {
        let data = JSON.parse(JSON.stringify(allPersonList.value))
        for (let i = 0; i < data.length; i++) {
            delete data[i].x
            delete data[i].y
            delete data[i].id
            delete data[i].createTime
            delete data[i].updateTime
            delete data[i].prizeId
            delete data[i].memberId
            delete data[i].winnerIds
            if (data[i].isWin) {
                data[i].isWin = i18n.global.t('data.yes')
            }
            else {
                data[i].isWin = i18n.global.t('data.no')
            }
            data[i].prizeTime = data[i].prizeTime.join(',')
            data[i].prizeName = data[i].prizeName.join(',')
        }

        let dataString = JSON.stringify(data)
        dataString = dataString
            .replaceAll(/uid/g, i18n.global.t('data.number'))
            .replaceAll(/isWin/g, i18n.global.t('data.isWin'))
            .replaceAll(/phone/g, i18n.global.t('data.phone'))
            .replaceAll(/name/g, i18n.global.t('data.name'))
            .replaceAll(/prizeName/g, i18n.global.t('data.prizeName'))
            .replaceAll(/prizeTime/g, i18n.global.t('data.prizeTime'))

        data = JSON.parse(dataString)

        if (data.length > 0) {
            const dataBinary = XLSX.utils.json_to_sheet(data)
            const dataBinaryBinary = XLSX.utils.book_new()
            XLSX.utils.book_append_sheet(dataBinaryBinary, dataBinary, 'Sheet1')
            XLSX.writeFile(dataBinaryBinary, 'data.xlsx')
            toast.open({
                message: t('error.exportSuccess'),
                type: 'success',
                position: 'top-right',
            })
        }
    }

    async function resetData() {
        try {
            await apiResetProjectWinners({
                project_id: selectedProjectId(),
                reason: '后台重置中奖结果',
            })
            await refreshData()
            toast.success(t('error.success'))
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, t('error.fail')))
        }
    }

    async function deleteAll() {
        try {
            await apiClearProjectMembers({
                project_id: selectedProjectId(),
                reason: '后台清空项目成员',
            })
            await refreshData()
            toast.success(t('error.success'))
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, t('error.fail')))
        }
    }

    async function delPersonItem(row: IPersonConfig) {
        try {
            const currentRow = row as PersonTableRow
            await apiProjectMemberDelete(currentRow.memberId)
            await refreshData()
            toast.success(t('error.deleteSuccess'))
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, t('error.fail')))
        }
    }

    async function addOnePerson(addOnePersonDrawerRef: any, event: any) {
        event.preventDefault()
        try {
            await apiProjectMemberCreate({
                project: selectedProjectId(),
                uid: singlePersonData.value.uid || singlePersonData.value.phone,
                name: singlePersonData.value.name,
                phone: singlePersonData.value.phone,
                is_active: true,
            })
            await refreshData()
            addOnePersonDrawerRef.closeDrawer()
            singlePersonData.value = {
                uid: '',
                name: '',
                phone: '',
            }
            toast.success(t('error.success'))
        }
        catch (error: any) {
            toast.error(buildErrorMessage(error, t('error.fail')))
        }
    }

    onMounted(() => {
        refreshData().catch((error: any) => {
            toast.error(buildErrorMessage(error, '加载项目成员失败'))
        })
    })

    return {
        resetData,
        deleteAll,
        handleFileChange,
        exportData,
        alreadyPersonList,
        allPersonList,
        tableColumnList,
        addOnePerson,
        addPersonModalVisible,
        singlePersonData,
        downloadTemplate,
    }
}
