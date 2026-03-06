#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { mkdir, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'

const ADMIN_BASE = process.env.ADMIN_BASE || 'http://127.0.0.1:8000/admin'
const ADMIN_USERNAME = process.env.ADMIN_USERNAME || 'qa_operator'
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'Qa123456!'
const OUT_DIR = process.env.OUT_DIR || 'docs/screenshots/2026-03-06-admin'
const DEBUG_PORT = Number(process.env.CDP_PORT || 9224)
const USER_DATA_DIR = process.env.CDP_USER_DATA_DIR || '/tmp/log-lottery-admin-cdp-profile'

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
                return
            }
        }
        catch {
            // retry
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
            `${ADMIN_BASE}/login/?next=/admin/`,
        ],
        { stdio: 'ignore' },
    )
}

async function getPageWebSocketUrl(timeoutMs = 10000) {
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
            // retry
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

    async evaluate(expression) {
        const { result, exceptionDetails } = await this.send('Runtime.evaluate', {
            expression,
            awaitPromise: true,
            returnByValue: true,
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

async function waitForPathPrefix(cdp, prefix, timeoutMs = 15000) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
        const pathname = await cdp.evaluate('location.pathname')
        if (pathname.startsWith(prefix)) {
            return pathname
        }
        await sleep(200)
    }
    const pathname = await cdp.evaluate('location.pathname')
    throw new Error(`Timed out waiting for path prefix ${prefix}, current=${pathname}`)
}

async function navigate(cdp, url) {
    await cdp.send('Page.navigate', { url })
    await waitForExpression(cdp, `document.readyState === 'complete' || document.readyState === 'interactive'`, 10000)
}

async function screenshot(cdp, filename) {
    const { data } = await cdp.send('Page.captureScreenshot', {
        format: 'png',
        fromSurface: true,
        captureBeyondViewport: false,
    })
    const fullPath = path.join(OUT_DIR, filename)
    await writeFile(fullPath, Buffer.from(data, 'base64'))
    return fullPath
}

async function adminLogin(cdp) {
    const user = ADMIN_USERNAME.replace(/'/g, "\\'")
    const pass = ADMIN_PASSWORD.replace(/'/g, "\\'")
    const result = await cdp.evaluate(`(() => {
        const username = document.querySelector('input[name="username"]')
        const password = document.querySelector('input[name="password"]')
        if (!username || !password) return 'inputs-not-found'
        username.focus()
        username.value = '${user}'
        username.dispatchEvent(new Event('input', { bubbles: true }))
        password.focus()
        password.value = '${pass}'
        password.dispatchEvent(new Event('input', { bubbles: true }))
        const form = document.querySelector('#login-form')
        if (!form) return 'form-not-found'
        form.submit()
        return 'ok'
    })()`)
    if (result !== 'ok') {
        throw new Error(`Admin login failed: ${result}`)
    }
}

async function run() {
    await ensureDir(OUT_DIR)
    await rm(USER_DATA_DIR, { recursive: true, force: true })

    const chrome = launchChrome()
    let cdp = null
    try {
        await waitForChromeReady()
        const wsUrl = await getPageWebSocketUrl()
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

        await navigate(cdp, `${ADMIN_BASE}/login/?next=/admin/`)
        await waitForExpression(cdp, `document.querySelector('input[name="username"]') && document.querySelector('input[name="password"]')`, 15000)
        console.log('capturing 01-admin-login.png')
        await screenshot(cdp, '01-admin-login.png')

        await adminLogin(cdp)
        await waitForPathPrefix(cdp, '/admin/')
        await waitForExpression(cdp, `!document.querySelector('input[name="username"]') && document.body.innerText.length > 30`, 15000)
        await sleep(800)
        console.log('capturing 02-admin-index.png')
        await screenshot(cdp, '02-admin-index.png')

        const pages = [
            ['03-admin-department-list.png', '/admin/accounts/department/'],
            ['04-admin-user-list.png', '/admin/accounts/adminuser/'],
            ['05-admin-project-list.png', '/admin/lottery/project/'],
            ['06-admin-member-list.png', '/admin/lottery/projectmember/'],
            ['07-admin-customer-list.png', '/admin/lottery/customer/'],
            ['08-admin-prize-list.png', '/admin/lottery/prize/'],
            ['09-admin-drawbatch-list.png', '/admin/lottery/drawbatch/'],
            ['10-admin-drawwinner-list.png', '/admin/lottery/drawwinner/'],
            ['11-admin-exclusion-rule-list.png', '/admin/lottery/exclusionrule/'],
            ['12-admin-exportjob-list.png', '/admin/lottery/exportjob/'],
        ]

        for (const [filename, routePath] of pages) {
            await navigate(cdp, `http://127.0.0.1:8000${routePath}`)
            await waitForExpression(cdp, `document.body.innerText.length > 30`, 10000)
            await sleep(700)
            console.log(`capturing ${filename}`)
            await screenshot(cdp, filename)
        }

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
    console.error('[capture-admin] failed:', error?.message || error)
    process.exit(1)
})
