import * as XLSX from 'xlsx'
import { addOtherInfo } from '@/utils'
// 定义消息类型
interface WorkerMessage {
    type: 'start' | 'stop' | 'reset'
    data: any
    templateData: any
}

function checkHeaders(actual: string[]): boolean {
    const requiredHeaders = ['ID', '姓名', '电话']
    return requiredHeaders.every(header => actual.includes(header))
}

// 接收主线程消息
globalThis.onmessage = async (e: MessageEvent<WorkerMessage>) => {
    switch (e.data.type) {
        case 'start':
        {
            try {
                const fileData = e.data.data
                const workBook = XLSX.read(fileData, { type: 'binary', cellDates: true })
                const workSheet = workBook.Sheets[workBook.SheetNames[0]]
                const excelData: any[] = XLSX.utils.sheet_to_json(workSheet)

                if (!excelData || excelData.length === 0) {
                    throw new Error('Excel file is empty or invalid.')
                }

                const header = Object.keys(excelData[0])
                if (!checkHeaders(header)) {
                    throw new Error('not right template')
                }

                const remappedData = excelData.map((row) => {
                    return {
                        uid: row['ID'] || '',
                        name: row['姓名'] || '',
                        phone: String(row['电话'] || ''),
                    }
                })

                const finalData = addOtherInfo(remappedData)

                globalThis.postMessage({
                    type: 'done',
                    data: finalData,
                    message: '读取完成',
                })
            }
            catch (error: any) {
                globalThis.postMessage({
                    type: 'error',
                    data: null,
                    message: error.message || 'Failed to process Excel file.',
                })
            }
            break
        }
        default:
            globalThis.postMessage({
                type: 'fail',
                data: null,
                message: '读取失败',
            })
            break
    }
}
