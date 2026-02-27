import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 从命令行参数获取版本号
const args = process.argv.slice(2);
let version = args[0];

if (!version) {
    console.error('错误: 请提供版本号作为参数');
    console.error('用法: node build/updateVersion.js <version>');
    process.exit(1);
}

// 验证版本号格式 (遵循语义化版本号格式，如 x.y.z)
const versionRegex = /^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+)?$/;
if (!versionRegex.test(version)) {
    console.error(`错误: 版本号格式不正确: ${version}`);
    console.error('正确的版本号格式示例: 1.0.0, 2.1.3, 0.5.0-beta 等');
    process.exit(1);
}

// 更新 package.json
const packageJsonPath = path.join(__dirname, '..', 'package.json');
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
packageJson.version = version;
fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2));

console.log(`版本号已更新至: ${version}`);
console.log(`- package.json`);
