import type { Material, Object3D } from 'three'
import type { TargetType } from './type'
import type { IPersonConfig, IPrizeConfig } from '@/types/storeType'
import * as TWEEN from '@tweenjs/tween.js'
import { storeToRefs } from 'pinia'
import { PerspectiveCamera, Scene } from 'three'
import { CSS3DObject, CSS3DRenderer } from 'three-css3d'
import { TrackballControls } from 'three/examples/jsm/controls/TrackballControls.js'
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useToast } from 'vue-toast-notification'
import {
    apiConfirmDraw,
    apiDrawBatchList,
    apiPreviewDraw,
    apiPrizeList,
    apiProjectMemberList,
    apiVoidDraw,
    type BackendDrawWinner,
    type BackendPrize,
} from '@/api/lottery'
import dongSound from '@/assets/audio/end.mp3'
import enterAudio from '@/assets/audio/enter.wav'
import worldCupAudio from '@/assets/audio/worldcup.mp3'
import { SINGLE_TIME_MAX_PERSON_COUNT } from '@/constant/config'
import { useElementPosition, useElementStyle } from '@/hooks/useElement'
import i18n from '@/locales/i18n'
import useStore from '@/store'
import { maskPhone, selectCard } from '@/utils'
import { rgba } from '@/utils/color'
import { getSelectedProjectId } from '@/utils/session'
import { LotteryStatus } from './type'
import { confettiFire, createSphereVertices, createTableVertices, initTableData } from './utils'

const maxAudioLimit = 10

export function useViewModel() {
    const toast = useToast()
    // store里面存储的值
    const { personConfig, globalConfig, prizeConfig } = useStore()
    const {
        getAllPersonList: allPersonList,
    } = storeToRefs(personConfig)
    const { getCurrentPrize: currentPrize } = storeToRefs(prizeConfig)
    const {
        getCardColor: cardColor,
        getPatterColor: patternColor,
        getPatternList: patternList,
        getTextColor: textColor,
        getLuckyColor: luckyColor,
        getCardSize: cardSize,
        getTextSize: textSize,
        getRowCount: rowCount,
        getTitleFont: titleFont,
        getTitleFontSyncGlobal: titleFontSyncGlobal,
        getDefiniteTime: definiteTime,
        getWinMusic: isPlayWinMusic,
        getIsLowPerformance: isLowPerformance,
    } = storeToRefs(globalConfig)
    // three初始值
    const ballRotationY = ref(0)
    const containerRef = ref<HTMLElement>()
    const canOperate = ref(true)
    const cameraZ = ref(3000)
    const scene = ref()
    const camera = ref()
    const renderer = ref()
    const controls = ref()
    const objects = ref<any[]>([])
    const targets: TargetType = {
        grid: [],
        helix: [],
        table: [],
        sphere: [],
    }
    // 页面数据初始值
    const currentStatus = ref<LotteryStatus>(LotteryStatus.init) // 0为初始状态， 1为抽奖准备状态，2为抽奖中状态，3为抽奖结束状态
    const tableData = ref<any[]>([])
    const luckyTargets = ref<any[]>([])
    const luckyCardList = ref<number[]>([])
    const luckyCount = ref(10)
    const intervalTimer = ref<any>(null)
    const isInitialDone = ref<boolean>(false)
    const animationFrameId = ref<any>(null)
    const playingAudios = ref<HTMLAudioElement[]>([])
    const currentDrawBatchId = ref<string>('')
    const selectedProjectId = ref<string>(getSelectedProjectId())

    // 抽奖音乐相关
    const lotteryMusic = ref<HTMLAudioElement | null>(null)

    function mapBackendPrizeToLocal(prize: BackendPrize): IPrizeConfig {
        const total = Number(prize.total_count || 0)
        const used = Number(prize.used_count || 0)
        const isUsed = used >= total
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
            isUsed,
            frequency: 1,
        } as IPrizeConfig
    }

    function mapWinnerToPerson(winner: BackendDrawWinner, index: number): IPersonConfig {
        const existed = allPersonList.value.find(person => person.phone === winner.phone)
        if (existed) {
            return existed
        }
        return {
            id: Date.now() + index,
            uid: winner.uid,
            uuid: `${winner.phone}-${index}`,
            name: winner.name,
            phone: winner.phone,
            isWin: winner.status === 'CONFIRMED',
            x: 0,
            y: 0,
            createTime: winner.created_at,
            updateTime: winner.created_at,
            prizeName: [],
            prizeId: [],
            prizeTime: [],
        }
    }

    async function syncProjectData() {
        selectedProjectId.value = getSelectedProjectId()
        if (!selectedProjectId.value) {
            throw new Error('未选择项目，请先选择项目')
        }

        const [memberList, prizeList, confirmedBatchList] = await Promise.all([
            apiProjectMemberList(selectedProjectId.value),
            apiPrizeList(selectedProjectId.value),
            apiDrawBatchList({ project_id: selectedProjectId.value, status: 'CONFIRMED' }),
        ])

        const nowText = new Date().toISOString()
        const localPersonList: IPersonConfig[] = memberList
            .filter(item => item.is_active)
            .map((item, index) => ({
                id: index + 1,
                uid: item.uid,
                uuid: item.phone,
                name: item.name,
                phone: item.phone,
                isWin: false,
                x: 0,
                y: 0,
                createTime: item.created_at || nowText,
                updateTime: item.updated_at || nowText,
                prizeName: [],
                prizeId: [],
                prizeTime: [],
            }))

        const prizeNameMap = new Map<string, string>()
        prizeList.forEach((item) => {
            prizeNameMap.set(item.id, item.name)
        })
        confirmedBatchList.forEach((batch) => {
            const prizeId = batch.prize
            const prizeName = prizeNameMap.get(prizeId) || ''
            ;(batch.winners || []).forEach((winner) => {
                const person = localPersonList.find(item => item.phone === winner.phone)
                if (!person)
                    return
                person.isWin = true
                if (prizeName && !person.prizeName.includes(prizeName)) {
                    person.prizeName.push(prizeName)
                }
                if (!person.prizeId.includes(prizeId)) {
                    person.prizeId.push(prizeId)
                }
                if (winner.confirmed_at) {
                    person.prizeTime.push(winner.confirmed_at)
                }
            })
        })

        personConfig.reset()
        personConfig.addNotPersonList(localPersonList)

        const localPrizeList = prizeList
            .filter(item => item.is_active)
            .map(mapBackendPrizeToLocal)
            .sort((a, b) => a.sort - b.sort)

        prizeConfig.setPrizeConfig(localPrizeList)
        if (localPrizeList.length) {
            const current = localPrizeList.find(item => item.isUsedCount < item.count) || localPrizeList[0]
            prizeConfig.setCurrentPrize(current)
        }
        else {
            prizeConfig.setCurrentPrize({
                id: '',
                name: '',
                sort: 0,
                isAll: false,
                count: 0,
                isUsedCount: 0,
                picture: {
                    id: '-1',
                    name: '',
                    url: '',
                },
                separateCount: {
                    enable: false,
                    countList: [],
                },
                desc: '',
                isShow: false,
                isUsed: true,
                frequency: 1,
            } as IPrizeConfig)
        }
    }

    function initThreeJs() {
        const felidView = 40
        const width = window.innerWidth
        const height = window.innerHeight
        const aspect = width / height
        const nearPlane = 1
        const farPlane = 10000
        const WebGLoutput = containerRef.value

        scene.value = new Scene()
        camera.value = new PerspectiveCamera(felidView, aspect, nearPlane, farPlane)
        camera.value.position.z = cameraZ.value
        renderer.value = new CSS3DRenderer()
        renderer.value.setSize(width, height * 0.9)
        renderer.value.domElement.style.position = 'absolute'
        // 垂直居中
        renderer.value.domElement.style.paddingTop = '50px'
        renderer.value.domElement.style.top = '50%'
        renderer.value.domElement.style.left = '50%'
        renderer.value.domElement.style.transform = 'translate(-50%, -50%)'
        WebGLoutput!.appendChild(renderer.value.domElement)

        controls.value = new TrackballControls(camera.value, renderer.value.domElement)
        controls.value.rotateSpeed = 1
        controls.value.staticMoving = true
        controls.value.minDistance = 500
        controls.value.maxDistance = 6000
        controls.value.addEventListener('change', render)

        const tableLen = tableData.value.length
        for (let i = 0; i < tableLen; i++) {
            let element = document.createElement('div')
            element.className = 'element-card'

            const number = document.createElement('div')
            number.className = 'card-id'
            number.textContent = tableData.value[i].uid
            element.appendChild(number)

            const symbol = document.createElement('div')
            symbol.className = 'card-name'
            symbol.textContent = tableData.value[i].name
            element.appendChild(symbol)

            const detail = document.createElement('div')
            detail.className = 'card-detail'
            detail.innerHTML = maskPhone(tableData.value[i].phone)
            element.appendChild(detail)

            // Empty div for consistent child count (for useElementStyle)
            const emptyDiv = document.createElement('div')
            emptyDiv.style.display = 'none'
            element.appendChild(emptyDiv)

            element = useElementStyle({
                element,
                person: tableData.value[i],
                index: i,
                patternList: patternList.value,
                patternColor: patternColor.value,
                cardColor: cardColor.value,
                cardSize: cardSize.value,
                scale: 1,
                textSize: textSize.value,
                mod: 'default',
            },
            )
            const object = new CSS3DObject(element)
            object.position.x = Math.random() * 4000 - 2000
            object.position.y = Math.random() * 4000 - 2000
            object.position.z = Math.random() * 4000 - 2000
            scene.value.add(object)

            objects.value.push(object)
        }
        // 创建横铺的界面
        const tableVertices = createTableVertices({ tableData: tableData.value, rowCount: rowCount.value, cardSize: cardSize.value })
        targets.table = tableVertices
        // 创建球体
        const sphereVertices = createSphereVertices({ objectsLength: objects.value.length })
        targets.sphere = sphereVertices
        window.addEventListener('resize', onWindowResize, false)
        transform(targets.table, 1000)
        render()
    }
    function render() {
        if (renderer.value) {
            renderer.value.render(scene.value, camera.value)
        }
    }
    /**
     * @description: 位置变换
     * @param targets 目标位置
     * @param duration 持续时间
     */
    function transform(targets: any[], duration: number) {
        TWEEN.removeAll()
        if (intervalTimer.value) {
            clearInterval(intervalTimer.value)
            intervalTimer.value = null
            randomBallData('sphere')
        }

        return new Promise((resolve) => {
            const objLength = objects.value.length
            for (let i = 0; i < objLength; ++i) {
                const object = objects.value[i]
                const target = targets[i]
                new TWEEN.Tween(object.position)
                    .to({ x: target.position.x, y: target.position.y, z: target.position.z }, Math.random() * duration + duration)
                    .easing(TWEEN.Easing.Exponential.InOut)
                    .start()

                new TWEEN.Tween(object.rotation)
                    .to({ x: target.rotation.x, y: target.rotation.y, z: target.rotation.z }, Math.random() * duration + duration)
                    .easing(TWEEN.Easing.Exponential.InOut)
                    .start()
                    .onComplete(() => {
                        if (luckyCardList.value.length) {
                            luckyCardList.value.forEach((cardIndex: any) => {
                                const item = objects.value[cardIndex]
                                useElementStyle({
                                    element: item.element,
                                    person: {} as any,
                                    index: i,
                                    patternList: patternList.value,
                                    patternColor: patternColor.value,
                                    cardColor: cardColor.value,
                                    cardSize: cardSize.value,
                                    scale: 1,
                                    textSize: textSize.value,
                                    mod: 'sphere',
                                })
                            })
                        }
                        luckyTargets.value = []
                        luckyCardList.value = []
                        canOperate.value = true
                    })
            }

            // 这个补间用来在位置与旋转补间同步执行，通过onUpdate在每次更新数据后渲染scene和camera
            new TWEEN.Tween({})
                .to({}, duration * 2)
                .onUpdate(render)
                .start()
                .onComplete(() => {
                    canOperate.value = true
                    resolve('')
                })
        })
    }
    /**
     * @description: 窗口大小改变时重新设置渲染器的大小
     */
    function onWindowResize() {
        camera.value.aspect = window.innerWidth / window.innerHeight
        camera.value.updateProjectionMatrix()

        renderer.value.setSize(window.innerWidth, window.innerHeight)
        render()
    }

    const lastFrameTime = ref(0)
    /**
     * [animation update all tween && controls]
     */
    function animation(time: number = 1000) {
        if (isLowPerformance.value) {
            // 低性能模式：限制约 30 帧 (1000ms / 30 ≈ 33ms)
            if (time - lastFrameTime.value < 30) {
                animationFrameId.value = requestAnimationFrame(animation)
                return
            }
            lastFrameTime.value = time
        }

        TWEEN.update()
        if (controls.value) {
            controls.value.update()
        }
        // 设置自动旋转
        // 设置相机位置
        animationFrameId.value = requestAnimationFrame(animation)
    }
    /**
     * @description: 旋转的动画
     * @param rotateY 绕y轴旋转圈数
     * @param duration 持续时间，单位秒
     */
    function rollBall(rotateY: number, duration: number) {
        TWEEN.removeAll()

        return new Promise((resolve) => {
            scene.value.rotation.y = 0
            ballRotationY.value = Math.PI * rotateY * 1000
            const rotateObj = new TWEEN.Tween(scene.value.rotation)
            rotateObj
                .to(
                    {
                        // x: Math.PI * rotateX * 1000,
                        x: 0,
                        y: ballRotationY.value,
                        // z: Math.PI * rotateZ * 1000
                        z: 0,
                    },
                    duration * 1000,
                )
                .onUpdate(render)
                .start()
                .onStop(() => {
                    resolve('')
                })
                .onComplete(() => {
                    resolve('')
                })
        })
    }
    /**
     * @description: 视野转回正面
     */
    function resetCamera() {
        new TWEEN.Tween(camera.value.position)
            .to(
                {
                    x: 0,
                    y: 0,
                    z: 3000,
                },
                1000,
            )
            .onUpdate(render)
            .start()
            .onComplete(() => {
                new TWEEN.Tween(camera.value.rotation)
                    .to(
                        {
                            x: 0,
                            y: 0,
                            z: 0,
                        },
                        1000,
                    )
                    .onUpdate(render)
                    .start()
                    .onComplete(() => {
                        canOperate.value = true
                        // camera.value.lookAt(scene.value.position)
                        camera.value.position.y = 0
                        camera.value.position.x = 0
                        camera.value.position.z = 3000
                        camera.value.rotation.x = 0
                        camera.value.rotation.y = 0
                        camera.value.rotation.z = -0
                        controls.value.reset()
                    })
            })
    }

    /**
     * @description: 开始抽奖音乐
     */
    function startLotteryMusic() {
        if (!isPlayWinMusic.value) {
            return
        }
        if (lotteryMusic.value) {
            lotteryMusic.value.pause()
            lotteryMusic.value = null
        }

        lotteryMusic.value = new Audio(worldCupAudio)
        lotteryMusic.value.loop = true
        lotteryMusic.value.volume = 0.7

        lotteryMusic.value.play().catch((error) => {
            console.error('播放抽奖音乐失败:', error)
        })
    }

    /**
     * @description: 停止抽奖音乐
     */
    function stopLotteryMusic() {
        if (!isPlayWinMusic.value) {
            return
        }
        if (lotteryMusic.value) {
            lotteryMusic.value.pause()
            lotteryMusic.value = null
        }
    }

    /**
     * @description: 播放结束音效
     */
    function playEndSound() {
        if (!isPlayWinMusic.value) {
            return
        }
        console.log('准备播放结束音效', dongSound)

        // 清理已结束的音频
        playingAudios.value = playingAudios.value.filter(audio => !audio.ended)

        try {
            const endSound = new Audio(dongSound)
            endSound.volume = 1.0

            // 简化播放逻辑
            const playPromise = endSound.play()

            if (playPromise) {
                playPromise
                    .then(() => {
                        console.log('结束音效播放成功')
                        playingAudios.value.push(endSound)
                    })
                    .catch((err) => {
                        console.error('播放失败:', err.name, err.message)
                        if (err.name === 'NotAllowedError') {
                            console.warn('自动播放被阻止，需用户交互后播放')
                        }
                    })
            }

            endSound.onended = () => {
                console.log('结束音效播放完成')
                const index = playingAudios.value.indexOf(endSound)
                if (index > -1)
                    playingAudios.value.splice(index, 1)
            }
        }
        catch (error) {
            console.error('创建音频对象失败:', error)
        }
    }

    /**
     * @description: 重置音频状态
     */
    function resetAudioState() {
        if (!isPlayWinMusic.value) {
            return
        }
        // 停止抽奖音乐
        stopLotteryMusic()

        // 清理所有正在播放的音频
        playingAudios.value.forEach((audio) => {
            if (!audio.ended && !audio.paused) {
                audio.pause()
            }
        })
        playingAudios.value = []
    }

    /**
     * @description: 开始抽奖，由横铺变换为球体（或其他图形）
     * @returns 随机抽取球数据
     */
    /// <IP_ADDRESS>description 进入抽奖准备状态
    async function enterLottery() {
        if (!canOperate.value) {
            return
        }

        // 重置音频状态
        resetAudioState()

        // 预加载音频资源以解决浏览器自动播放策略
        try {
            const audioContext = window.AudioContext || (window as any).webkitAudioContext
            if (audioContext) {
                console.log('音频上下文可用')
            }
        }
        catch (e) {
            console.warn('音频上下文不可用:', e)
        }

        if (!intervalTimer.value) {
            randomBallData()
        }
        if (patternList.value.length) {
            for (let i = 0; i < patternList.value.length; i++) {
                if (i < rowCount.value * 7 && objects.value[patternList.value[i] - 1]) {
                    objects.value[patternList.value[i] - 1].element.style.backgroundColor = rgba(cardColor.value, Math.random() * 0.5 + 0.25)
                }
            }
        }
        canOperate.value = false
        await transform(targets.sphere, 1000)
        currentStatus.value = LotteryStatus.ready
        rollBall(0.1, 2000)
    }
    /**
     * @description 开始抽奖
     */
    async function startLottery() {
        if (!canOperate.value) {
            return
        }
        // 验证是否已抽完全部奖项
        if (currentPrize.value.isUsed || !currentPrize.value || !currentPrize.value.id) {
            toast.open({
                message: i18n.global.t('error.personIsAllDone'),
                type: 'warning',
                position: 'top-right',
                duration: 10000,
            })

            return
        }
        if (!selectedProjectId.value) {
            toast.open({
                message: '未选择项目，请先选择项目',
                type: 'warning',
                position: 'top-right',
                duration: 10000,
            })
            return
        }
        if (!allPersonList.value.length) {
            toast.open({
                message: i18n.global.t('error.personNotEnough'),
                type: 'warning',
                position: 'top-right',
                duration: 10000,
            })
            return
        }
        // 默认置为单次抽奖最大个数
        luckyCount.value = SINGLE_TIME_MAX_PERSON_COUNT
        // 还剩多少人未抽
        let leftover = currentPrize.value.count - currentPrize.value.isUsedCount
        if (leftover <= 0) {
            toast.open({
                message: i18n.global.t('error.personIsAllDone'),
                type: 'warning',
                position: 'top-right',
                duration: 8000,
            })
            return
        }
        luckyCount.value = leftover < luckyCount.value ? leftover : luckyCount.value

        try {
            const batch = await apiPreviewDraw({
                project_id: selectedProjectId.value,
                prize_id: String(currentPrize.value.id),
                count: luckyCount.value,
            })
            currentDrawBatchId.value = batch.id
            luckyTargets.value = (batch.winners || []).map((winner, index) => mapWinnerToPerson(winner, index))
            luckyCount.value = luckyTargets.value.length
            if (!luckyTargets.value.length) {
                throw new Error('未抽到任何候选中奖人')
            }
        }
        catch (error: any) {
            toast.open({
                message: error?.message || '抽奖请求失败，请检查项目配置',
                type: 'error',
                position: 'top-right',
                duration: 10000,
            })
            currentDrawBatchId.value = ''
            luckyTargets.value = []
            return
        }

        if (!luckyTargets.value.length) {
            toast.open({
                message: '本轮没有可确认中奖人',
                type: 'warning',
                position: 'top-right',
                duration: 8000,
            })
            return
        }

        toast.open({
            message: i18n.global.t('error.startDraw', { count: currentPrize.value.name, leftover }),
            type: 'default',
            position: 'top-right',
            duration: 8000,
        })

        // 开始播放抽奖音乐
        startLotteryMusic()

        currentStatus.value = LotteryStatus.running
        rollBall(10, 3000)
        if (definiteTime.value) {
            setTimeout(() => {
                if (currentStatus.value === LotteryStatus.running) {
                    stopLottery()
                }
            }, definiteTime.value * 1000)
        }
    }
    /**
     * @description: 停止抽奖，抽出幸运人
     */
    async function stopLottery() {
        if (!canOperate.value) {
            return
        }
        // 停止抽奖音乐
        stopLotteryMusic()

        // 播放结束音效
        playEndSound()

        //   clearInterval(intervalTimer.value)
        //   intervalTimer.value = null
        canOperate.value = false
        rollBall(0, 1)

        const windowSize = { width: window.innerWidth, height: window.innerHeight }
        luckyTargets.value.forEach((person: IPersonConfig, index: number) => {
            const cardIndex = selectCard(luckyCardList.value, tableData.value.length, person.id)
            luckyCardList.value.push(cardIndex)
            const totalLuckyCount = luckyTargets.value.length
            const item = objects.value[cardIndex]
            const { xTable, yTable, scale } = useElementPosition(
                item,
                rowCount.value,
                totalLuckyCount,
                { width: cardSize.value.width, height: cardSize.value.height },
                windowSize,
                index,
            )
            new TWEEN.Tween(item.position)
                .to({
                    x: xTable,
                    y: yTable,
                    z: 1000,
                }, 1200)
                .easing(TWEEN.Easing.Exponential.InOut)
                .onStart(() => {
                    item.element = useElementStyle({
                        element: item.element,
                        person,
                        index: cardIndex,
                        patternList: patternList.value,
                        patternColor: patternColor.value,
                        cardColor: luckyColor.value,
                        cardSize: { width: cardSize.value.width, height: cardSize.value.height },
                        scale,
                        textSize: textSize.value,
                        mod: 'lucky',
                    })
                })
                .start()
                .onComplete(() => {
                    canOperate.value = true
                    currentStatus.value = LotteryStatus.end
                })
            new TWEEN.Tween(item.rotation)
                .to({
                    x: 0,
                    y: 0,
                    z: 0,
                }, 900)
                .easing(TWEEN.Easing.Exponential.InOut)
                .start()
                .onComplete(() => {
                    playWinMusic()

                    if (!globalConfig.getIsLowPerformance) {
                        confettiFire()
                    }
                    resetCamera()
                })
        })
    }
    // 播放音频，中将卡片越多audio对象越多，声音越大
    function playWinMusic() {
        if (!isPlayWinMusic.value) {
            return
        }
        // 清理已结束的音频
        playingAudios.value = playingAudios.value.filter(audio => !audio.ended && !audio.paused)

        if (playingAudios.value.length > maxAudioLimit) {
            console.log('音频播放数量已达到上限，请勿重复播放')
            return
        }

        const enterNewAudio = new Audio(enterAudio)
        enterNewAudio.volume = 0.8

        playingAudios.value.push(enterNewAudio)
        enterNewAudio.play()
            .then(() => {
                // 当音频播放结束后，从数组中移除
                enterNewAudio.onended = () => {
                    const index = playingAudios.value.indexOf(enterNewAudio)
                    if (index > -1) {
                        playingAudios.value.splice(index, 1)
                    }
                }
            })
            .catch((error) => {
                console.error('播放音频失败:', error)
                // 如果播放失败，也从数组中移除
                const index = playingAudios.value.indexOf(enterNewAudio)
                if (index > -1) {
                    playingAudios.value.splice(index, 1)
                }
            })

        // 播放错误时从数组中移除
        enterNewAudio.onerror = () => {
            const index = playingAudios.value.indexOf(enterNewAudio)
            if (index > -1) {
                playingAudios.value.splice(index, 1)
            }
        }
    }
    /**
     * @description: 继续,意味着这抽奖作数，计入数据库
     */
    async function continueLottery() {
        if (!canOperate.value) {
            return
        }
        if (!currentDrawBatchId.value) {
            toast.open({
                message: '当前没有可确认的抽奖批次',
                type: 'warning',
                position: 'top-right',
                duration: 8000,
            })
            return
        }
        try {
            await apiConfirmDraw(currentDrawBatchId.value)
            currentDrawBatchId.value = ''
            luckyCount.value = 0
            await syncProjectData()
        }
        catch (error: any) {
            toast.open({
                message: error?.message || '确认中奖失败',
                type: 'error',
                position: 'top-right',
                duration: 10000,
            })
            return
        }
        await enterLottery()
    }
    /**
     * @description: 放弃本次抽奖，回到初始状态
     */
    async function quitLottery() {
        // 停止抽奖音乐
        stopLotteryMusic()

        if (currentDrawBatchId.value) {
            try {
                await apiVoidDraw(currentDrawBatchId.value, '手动作废并重新抽奖')
            }
            catch (error: any) {
                toast.open({
                    message: error?.message || '作废抽奖批次失败',
                    type: 'error',
                    position: 'top-right',
                    duration: 10000,
                })
                return
            }
        }
        currentDrawBatchId.value = ''
        luckyCount.value = 0
        luckyTargets.value = []
        await syncProjectData()
        await enterLottery()
        currentStatus.value = LotteryStatus.init
    }

    /**
     * @description: 随机替换卡片中的数据（不改变原有的值，只是显示）
     * @param {string} mod 模式
     */
    function randomBallData(mod: 'default' | 'lucky' | 'sphere' = 'default') {
        // 两秒执行一次
        intervalTimer.value = setInterval(() => {
            if (!allPersonList.value.length || !tableData.value.length) {
                return
            }
            // 产生随机数数组
            const indexLength = 4
            const cardRandomIndexArr: number[] = []
            const personRandomIndexArr: number[] = []
            for (let i = 0; i < indexLength; i++) {
                // 解决随机元素概率过于不均等问题
                const randomCardIndex = Math.floor(Math.random() * (tableData.value.length - 1))
                const randomPersonIndex = Math.floor(Math.random() * (allPersonList.value.length - 1))
                if (luckyCardList.value.includes(randomCardIndex)) {
                    continue
                }
                cardRandomIndexArr.push(randomCardIndex)
                personRandomIndexArr.push(randomPersonIndex)
            }
            for (let i = 0; i < cardRandomIndexArr.length; i++) {
                if (!objects.value[cardRandomIndexArr[i]]) {
                    continue
                }
                objects.value[cardRandomIndexArr[i]].element = useElementStyle({
                    element: objects.value[cardRandomIndexArr[i]].element,
                    person: allPersonList.value[personRandomIndexArr[i]],
                    index: cardRandomIndexArr[i],
                    patternList: patternList.value,
                    patternColor: patternColor.value,
                    cardColor: cardColor.value,
                    cardSize: { width: cardSize.value.width, height: cardSize.value.height },
                    textSize: textSize.value,
                    scale: 1,
                    mod,
                    type: 'change',
                })
            }
        }, 200)
    }
    /**
     * @description: 键盘监听，快捷键操作
     */
    function listenKeyboard(e: any) {
        if ((e.keyCode !== 32 || e.keyCode !== 27) && !canOperate.value) {
            return
        }
        if (e.keyCode === 27 && currentStatus.value === LotteryStatus.running) {
            quitLottery()
        }
        if (e.keyCode !== 32) {
            return
        }
        switch (currentStatus.value) {
            case LotteryStatus.init:
                enterLottery()
                break
            case LotteryStatus.ready:
                startLottery()
                break
            case LotteryStatus.running:
                stopLottery()
                break
            case LotteryStatus.end:
                continueLottery()
                break
            default:
                break
        }
    }
    /**
     * @description: 清理资源，避免内存溢出
     */
    function cleanup() {
        // 停止所有Tween动画
        TWEEN.removeAll()

        // 清理动画循环
        if ((window as any).cancelAnimationFrame) {
            (window as any).cancelAnimationFrame(animationFrameId.value)
        }
        clearInterval(intervalTimer.value)
        intervalTimer.value = null

        // 停止抽奖音乐
        stopLotteryMusic()

        // 清理所有音频资源
        playingAudios.value.forEach((audio) => {
            if (!audio.ended && !audio.paused) {
                audio.pause()
            }
            // 释放音频资源
            audio.src = ''
            audio.load()
        })
        playingAudios.value = []

        if (scene.value) {
            scene.value.traverse((object: Object3D) => {
                if ((object as any).material) {
                    if (Array.isArray((object as any).material)) {
                        (object as any).material.forEach((material: Material) => {
                            material.dispose()
                        })
                    }
                    else {
                        (object as any).material.dispose()
                    }
                }
                if ((object as any).geometry) {
                    (object as any).geometry.dispose()
                }
                if ((object as any).texture) {
                    (object as any).texture.dispose()
                }
            })
            scene.value.clear()
        }

        if (objects.value) {
            objects.value.forEach((object) => {
                if (object.element) {
                    object.element.remove()
                }
            })
            objects.value = []
        }

        if (controls.value) {
            controls.value.removeEventListener('change')
            controls.value.dispose()
        }
        //   移除所有事件监听
        window.removeEventListener('resize', onWindowResize)
        scene.value = null
        camera.value = null
        renderer.value = null
        controls.value = null
    }
    /**
     * @description: 设置默认人员列表
     */
    function setDefaultPersonList() {
        syncProjectData()
    }
    const init = async () => {
        try {
            await syncProjectData()
        }
        catch (error: any) {
            toast.open({
                message: error?.message || '初始化项目数据失败',
                type: 'error',
                position: 'top-right',
                duration: 10000,
            })
        }
        tableData.value = initTableData({ allPersonList: allPersonList.value, rowCount: rowCount.value })
        initThreeJs()
        animation()
        containerRef.value!.style.color = `${textColor}`
        randomBallData()
        window.addEventListener('keydown', listenKeyboard)
        isInitialDone.value = true
    }
    onMounted(() => {
        init()
    })
    onUnmounted(() => {
        nextTick(() => {
            cleanup()
        })
        clearInterval(intervalTimer.value)
        intervalTimer.value = null
        window.removeEventListener('keydown', listenKeyboard)
    })

    return {
        setDefaultPersonList,
        startLottery,
        continueLottery,
        quitLottery,
        containerRef,
        stopLottery,
        enterLottery,
        tableData,
        currentStatus,
        isInitialDone,
        titleFont,
        titleFontSyncGlobal,
    }
}
