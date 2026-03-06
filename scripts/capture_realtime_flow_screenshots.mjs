#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { mkdir, writeFile, rm } from 'node:fs/promises'
import path from 'node:path'

const FRONTEND_BASE = process.env.FRONTEND_BASE || 'http://127.0.0.1:6719'
const APP_BASE = `${FRONTEND_BASE}/log-lottery`
const PROJECT_KEYWORD = process.env.PROJECT_KEYWORD || 'QA-PROJECT-RT-001'
const OUT_DIR = process.env.OUT_DIR || 'docs/screenshots/2026-03-06-realtime'
const DEBUG_PORT = Number(process.env.CDP_PORT || 9223)
const USER_DATA_DIR = process.env.CDP_USER_DATA_DIR || '/tmp/log-lottery-cdp-profile'

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

async function ensureDir(dir) {
    await mkdir(dir, { recursive: true })
}

async function httpGetJson(url) {
    const resp = await fetch(url)
    if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${url}`)
    }
    return await resp.json()
}

async function waitForChromeReady(timeoutMs = 15000) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
        try {
            const version = await httpGetJson(`http://127.0.0.1:${DEBUG_PORT}/json/version`)
            if (version?.Browser) {
                return version
            }
        }
        catch {
            // keep polling until timeout
        }
        await sleep(200)
    }
    throw new Error('Chrome remote debugging is not ready')
}

function launchChrome() {
    return spawn(
        'google-chrome-stable',
        [
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--hide-scrollbars',
            `--remote-debugging-port=${DEBUG_PORT}`,
            `--user-data-dir=${USER_DATA_DIR}`,
            `${APP_BASE}/login`,
        ],
        {
            stdio: 'ignore',
        },
    )
}

async function getFirstPageWebSocketUrl(timeoutMs = 10000) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
        try {
            const targets = await httpGetJson(`http://127.0.0.1:${DEBUG_PORT}/json/list`)
            const page = targets.find(item => item.type === 'page' && item.webSocketDebuggerUrl)
            if (page) {
                return page.webSocketDebuggerUrl
            }
        }
        catch {
            // keep polling
        }
        await sleep(200)
    }
    throw new Error('Cannot find a debuggable page target')
}

class CDP {
    constructor(wsUrl) {
        this.id = 0
        this.pending = new Map()
        this.handlers = new Set()
        this.ws = new WebSocket(wsUrl)
        this.opened = new Promise((resolve, reject) => {
            this.ws.addEventListener('open', () => resolve())
            this.ws.addEventListener('error', err => reject(err))
        })
        this.ws.addEventListener('message', (event) => {
            const message = JSON.parse(event.data)
            if (message.id) {
                const pending = this.pending.get(message.id)
                if (!pending)
                    return
                this.pending.delete(message.id)
                if (message.error) {
                    pending.reject(new Error(`${message.error.message} (${message.error.code})`))
                }
                else {
                    pending.resolve(message.result ?? {})
                }
                return
            }

            for (const handler of this.handlers) {
                handler(message)
            }
        })
    }

    async ready() {
        await this.opened
    }

    send(method, params = {}) {
        const id = ++this.id
        this.ws.send(JSON.stringify({ id, method, params }))
        return new Promise((resolve, reject) => {
            this.pending.set(id, { resolve, reject })
        })
    }

    onEvent(handler) {
        this.handlers.add(handler)
        return () => this.handlers.delete(handler)
    }

    waitForEvent(method, timeoutMs = 10000, predicate = () => true) {
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                off()
                reject(new Error(`Timed out waiting for event ${method}`))
            }, timeoutMs)
            const off = this.onEvent((event) => {
                if (event.method !== method)
                    return
                if (!predicate(event.params))
                    return
                clearTimeout(timer)
                off()
                resolve(event.params)
            })
        })
    }

    async evaluate(expression) {
        const { result, exceptionDetails } = await this.send('Runtime.evaluate', {
            expression,
            returnByValue: true,
            awaitPromise: true,
        })
        if (exceptionDetails) {
            throw new Error(`Runtime.evaluate failed: ${JSON.stringify(exceptionDetails)}`)
        }
        return result?.value
    }

    async close() {
        try {
            await this.send('Browser.close')
        }
        catch {
            this.ws.close()
        }
    }
}

async function waitForDocumentReady(cdp, timeoutMs = 10000) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
        const ready = await cdp.evaluate('document.readyState')
        if (ready === 'complete' || ready === 'interactive') {
            return
        }
        await sleep(200)
    }
    throw new Error('Timed out waiting for document readiness')
}

async function waitForPath(cdp, pathname, timeoutMs = 15000) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
        const current = await cdp.evaluate('location.pathname')
        if (current === pathname) {
            return
        }
        await sleep(200)
    }
    const finalPath = await cdp.evaluate('location.pathname')
    throw new Error(`Timed out waiting for path ${pathname}, current=${finalPath}`)
}

async function waitForExpression(cdp, expression, timeoutMs = 15000) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
        const ok = await cdp.evaluate(`Boolean(${expression})`)
        if (ok) {
            return
        }
        await sleep(200)
    }
    throw new Error(`Timed out waiting for expression: ${expression}`)
}

async function navigate(cdp, url, expectedPathname) {
    await cdp.send('Page.navigate', { url })
    await waitForDocumentReady(cdp)
    if (expectedPathname) {
        await waitForPath(cdp, expectedPathname)
    }
}

async function screenshot(cdp, filename) {
    const { data } = await cdp.send('Page.captureScreenshot', {
        format: 'png',
        fromSurface: true,
        captureBeyondViewport: true,
    })
    const fullPath = path.join(OUT_DIR, filename)
    await writeFile(fullPath, Buffer.from(data, 'base64'))
    return fullPath
}

async function clickByText(cdp, texts) {
    const escapedTexts = texts.map(t => t.replace(/'/g, "\\'"))
    const result = await cdp.evaluate(`(() => {
        const nodes = [...document.querySelectorAll('button, [role="button"], a')]
        const keywords = [${escapedTexts.map(text => `'${text.toLowerCase()}'`).join(',')}]
        const pick = nodes.find((node) => {
            const txt = (node.innerText || node.textContent || '').trim().toLowerCase()
            if (!txt) return false
            return keywords.some(keyword => txt.includes(keyword))
        })
        if (!pick) return false
        for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
            pick.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }))
        }
        return true
    })()`)
    if (!result) {
        throw new Error(`Failed to click element by text: ${texts.join('/')}`)
    }
}

async function clickSelector(cdp, selector) {
    const escaped = selector.replace(/'/g, "\\'")
    const result = await cdp.evaluate(`(() => {
        const node = document.querySelector('${escaped}')
        if (!node) return false
        for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
            node.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }))
        }
        return true
    })()`)
    if (!result) {
        throw new Error(`Failed to click selector: ${selector}`)
    }
}

async function clickProjectEnter(cdp, keyword) {
    const escaped = keyword.replace(/'/g, "\\'")
    const result = await cdp.evaluate(`(() => {
        const rows = [...document.querySelectorAll('tbody tr')]
        const row = rows.find((r) => {
            const text = (r.innerText || '').trim()
            return text.includes('${escaped}') || text.includes('QA实时截图项目')
        })
        if (!row) return 'row-not-found'
        const btn = [...row.querySelectorAll('button')].find(b => {
            const txt = (b.innerText || '').trim()
            return txt.includes('进入项目') || txt.toLowerCase().includes('enter')
        })
        if (!btn) return 'button-not-found'
        btn.click()
        return 'ok'
    })()`)
    if (result !== 'ok') {
        throw new Error(`Failed to choose project: ${result}`)
    }
}

async function login(cdp, username, password) {
    const escapedUser = username.replace(/'/g, "\\'")
    const escapedPass = password.replace(/'/g, "\\'")
    const result = await cdp.evaluate(`(() => {
        const textInput = document.querySelector('input[type="text"]')
        const passInput = document.querySelector('input[type="password"]')
        if (!textInput || !passInput) return 'inputs-not-found'
        textInput.focus()
        textInput.value = '${escapedUser}'
        textInput.dispatchEvent(new Event('input', { bubbles: true }))
        passInput.focus()
        passInput.value = '${escapedPass}'
        passInput.dispatchEvent(new Event('input', { bubbles: true }))
        const btn = [...document.querySelectorAll('button')].find((b) => {
            const txt = (b.innerText || '').trim()
            return txt.includes('登录') || txt.toLowerCase().includes('login')
        })
        if (!btn) return 'login-button-not-found'
        btn.click()
        return 'ok'
    })()`)
    if (result !== 'ok') {
        throw new Error(`Login action failed: ${result}`)
    }
}

async function run() {
    await ensureDir(OUT_DIR)
    await rm(USER_DATA_DIR, { recursive: true, force: true })

    const chrome = launchChrome()
    let cdp = null
    try {
        await waitForChromeReady()
        const wsUrl = await getFirstPageWebSocketUrl()
        cdp = new CDP(wsUrl)
        await cdp.ready()

        await cdp.send('Page.enable')
        await cdp.send('Runtime.enable')
        await cdp.send('Network.enable')
        await cdp.send('Emulation.setDeviceMetricsOverride', {
            width: 1920,
            height: 1080,
            deviceScaleFactor: 1,
            mobile: false,
        })

        await navigate(cdp, `${APP_BASE}/login`, '/log-lottery/login')
        await waitForExpression(cdp, `document.querySelector('input[type="password"]') && document.body.innerText.includes('后台登录')`, 20000)
        await sleep(500)
        console.log('capturing 01-login.png')
        await screenshot(cdp, '01-login.png')

        await login(cdp, 'qa_operator', 'Qa123456!')
        await waitForPath(cdp, '/log-lottery/project-select')
        await waitForExpression(cdp, `document.body.innerText.includes('选择抽奖项目') && document.querySelector('table')`, 20000)
        await sleep(600)
        console.log('capturing 02-project-select.png')
        await screenshot(cdp, '02-project-select.png')

        await clickProjectEnter(cdp, PROJECT_KEYWORD)
        await waitForPath(cdp, '/log-lottery/home')
        await waitForExpression(cdp, `document.querySelector('#container') && document.body.innerText.length > 10`, 20000)
        await sleep(1500)
        console.log('capturing 03-home.png')
        await screenshot(cdp, '03-home.png')

        await clickSelector(cdp, '#menu .btn-neon')
        await waitForExpression(
            cdp,
            `Array.from(document.querySelectorAll('button')).some(btn => {
                const t=(btn.innerText||'').trim().toLowerCase()
                return t === 'start' || t.includes('开始')
            })`,
            15000,
        )
        await sleep(800)
        console.log('capturing 04-ready-start.png')
        await screenshot(cdp, '04-ready-start.png')

        await clickSelector(cdp, '#menu .btn-stars')
        await waitForExpression(
            cdp,
            `Array.from(document.querySelectorAll('button')).some(btn => {
                const t=(btn.innerText||'').trim().toLowerCase()
                return t.includes('抽取幸运儿') || t.includes('draw the lucky')
            })`,
            20000,
        )
        await sleep(1400)
        console.log('capturing 05-draw-running.png')
        await screenshot(cdp, '05-draw-running.png')

        await clickSelector(cdp, '#menu .btn-neon.glass.btn-lg')
        await waitForExpression(
            cdp,
            `Array.from(document.querySelectorAll('button')).some(btn => {
                const t=(btn.innerText||'').trim().toLowerCase()
                return t.includes('continue') || t.includes('继续')
            })`,
            20000,
        )
        await sleep(1400)
        console.log('capturing 06-draw-result.png')
        await screenshot(cdp, '06-draw-result.png')

        const pages = [
            ['07-config-person-all.png', '/log-lottery/config/person/all'],
            ['08-config-person-already.png', '/log-lottery/config/person/already'],
            ['09-config-prize.png', '/log-lottery/config/prize'],
            ['10-config-exclusion-rules.png', '/log-lottery/config/exclusion-rules'],
            ['11-config-export-jobs.png', '/log-lottery/config/export-jobs'],
            ['12-config-global-face.png', '/log-lottery/config/global/face'],
            ['13-config-global-image.png', '/log-lottery/config/global/image'],
            ['14-config-global-music.png', '/log-lottery/config/global/music'],
        ]

        for (const [filename, routePath] of pages) {
            await navigate(cdp, `${FRONTEND_BASE}${routePath}`, routePath)
            await waitForExpression(cdp, `document.body.innerText.length > 10`, 15000)
            await sleep(1000)
            console.log(`capturing ${filename}`)
            await screenshot(cdp, filename)
        }

        await navigate(cdp, 'http://127.0.0.1:8000/admin/login/?next=/admin/')
        await sleep(1200)
        console.log('capturing 15-admin-login.png')
        await screenshot(cdp, '15-admin-login.png')

        console.log(`done: ${OUT_DIR}`)
    }
    finally {
        if (cdp) {
            await cdp.close()
        }
        if (!chrome.killed) {
            chrome.kill('SIGTERM')
        }
    }
}

run().catch((error) => {
    console.error('[capture] failed:', error?.message || error)
    process.exit(1)
})
