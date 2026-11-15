#!/usr/bin/env node
/* 数格涂涂 · 独立数学校验
   直接从 HTML 里抽 KERNEL 段运行，保证"校验的就是页面在用的那份逻辑"。
   用法：node scripts/verify.mjs [html路径]
   不给路径时按"仓库布局 → 技能包布局"自动找，所以在 GitHub 仓库根、在 skillhub
   install 下来的技能包里，同一条 `node scripts/verify.mjs` 都能跑（1.0.0 那轮只认
   仓库根，技能包里就报 ENOENT）。 */
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const MAIN = '数格涂涂_生成器.html';
const HERE = path.dirname(fileURLToPath(import.meta.url));

function resolveFile() {
  if (process.argv[2]) return process.argv[2];
  const roots = [process.cwd(), path.join(HERE, '..')];
  for (const r of roots) {
    for (const rel of [MAIN, path.join('assets', MAIN)]) {
      const p = path.join(r, rel);
      if (fs.existsSync(p)) return p;
    }
  }
  for (const r of roots) {
    for (const d of [r, path.join(r, 'assets')]) {
      if (!fs.existsSync(d)) continue;
      const hit = fs.readdirSync(d).find(f => f.includes('生成器') && f.endsWith('.html'));
      if (hit) return path.join(d, hit);
    }
  }
  console.error(`找不到 ${MAIN}。技能包里它在 assets/ 下、仓库里在根目录；` +
                `也可以显式传路径：node scripts/verify.mjs assets/${MAIN}`);
  process.exit(1);
}

const FILE = resolveFile();
console.log('校验对象：' + FILE);
const html = fs.readFileSync(FILE, 'utf8');
const m = html.match(/\/\* ===== KERNEL START ===== \*\/([\s\S]*?)\/\* ===== KERNEL END ===== \*\//);
if (!m) { console.error('找不到 KERNEL 段，校验中止'); process.exit(1); }

const ctx = vm.createContext({ Math, Object, Array, JSON, Error, String, Number });
vm.runInContext(m[1], ctx, { filename: 'kernel.js' });
const K = ctx;

let pass = 0, fail = 0;
const ok = (name, cond, extra = '') => {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (extra ? '  → ' + extra : '')); }
};
const section = t => console.log('\n' + t);

/* ---------- 1. 基础图论 ---------- */
section('[1] 网格与相邻边');
for (const size of [4, 8, 10]) {
  const E = K.allEdges(size);
  const want = 2 * size * (size - 1);
  ok(`${size}×${size} 相邻边数 = ${want}`, E.length === want, '实得 ' + E.length);
  ok(`${size}×${size} 每条边两端奇偶相反（二分图成立）`,
    E.every(([a, b]) => K.parity(size, a) !== K.parity(size, b)));
  ok(`${size}×${size} 只有横竖、没有斜角`,
    E.every(([a, b]) => {
      const [r1, c1] = [Math.floor(a / size), a % size], [r2, c2] = [Math.floor(b / size), b % size];
      return (r1 === r2 && Math.abs(c1 - c2) === 1) || (c1 === c2 && Math.abs(r1 - r2) === 1);
    }));
}

/* ---------- 2. 最大匹配算法：对拍暴力解 ---------- */
section('[2] maxMatching 与暴力枚举对拍');
function bruteMax(size, pairs) {          // 全子集枚举，最大互不重叠边数
  let best = 0;
  const n = pairs.length;
  for (let mask = 0; mask < (1 << n); mask++) {
    const used = new Set(); let cnt = 0, good = true;
    for (let i = 0; i < n; i++) if (mask & (1 << i)) {
      const [a, b] = pairs[i];
      if (used.has(a) || used.has(b)) { good = false; break; }
      used.add(a); used.add(b); cnt++;
    }
    if (good && cnt > best) best = cnt;
  }
  return best;
}
{
  const rng = K.mulberry32(20261111);
  let mismatch = 0, cases = 0;
  for (let t = 0; t < 60; t++) {
    const size = 4, N = size * size, E = K.allEdges(size), pick = [];
    for (const e of E) if (rng() < 0.35) pick.push([e[0], e[1]]);
    if (pick.length > 16) pick.length = 16;   // 暴力解上限保护
    const got = K.maxMatching(size, pick), exp = bruteMax(size, pick);
    cases++; if (got !== exp) mismatch++;
  }
  ok(`4×4 随机边集 ${cases} 组，与暴力解全部一致`, mismatch === 0, mismatch + ' 组不符');
  // 全边集：n×n 网格完美匹配 = floor(N/2)（偶数格时可完美）
  for (const size of [4, 8, 10]) {
    const full = K.allEdges(size).map(e => [e[0], e[1]]);
    const got = K.maxMatching(size, full), want = (size * size) / 2;
    ok(`${size}×${size} 全边集最大匹配 = ${want}（棋盘可完美铺满骨牌）`, got === want, '实得 ' + got);
  }
}

/* ---------- 3. digitsFor：植桩数字必须合法且命中目标 ---------- */
section('[3] 植桩数字生成');
{
  let bad = [];
  for (const t of [0, 1, 2, 3, 5, 7, 9, 10]) {
    const rng = K.mulberry32(t * 131 + 7);
    for (let i = 0; i < 400; i++) {
      const d = K.digitsFor('sum', t, rng);
      if (!d) { bad.push(`sum t=${t} 第${i}次返回 null`); break; }
      if (d[0] < 0 || d[0] > 9 || d[1] < 0 || d[1] > 9) { bad.push(`sum 越界 ${d}`); break; }
      if (d[0] + d[1] !== t) { bad.push(`sum 不达目标 ${d} ≠ ${t}`); break; }
      if (t > 10 && d[0] + d[1] > K.MAXV) { bad.push('和越出 10 以内'); break; }
    }
  }
  for (const t of [0, 1, 3, 6, 9]) {
    const rng = K.mulberry32(t * 977 + 3);
    for (let i = 0; i < 400; i++) {
      const d = K.digitsFor('diff', t, rng);
      if (!d) { bad.push(`diff t=${t} 返回 null`); break; }
      if (Math.abs(d[0] - d[1]) !== t) { bad.push(`diff 不达目标 ${d} ≠ ${t}`); break; }
      if (d[0] < 0 || d[0] > 9 || d[1] < 0 || d[1] > 9) { bad.push('diff 越界'); break; }
    }
  }
  ok('和/差植桩数字 3200 次全部合法且命中目标', bad.length === 0, bad[0] || '');
  ok('t=10 时不会出现 0+10（单格上限 9）', (() => {
    const rng = K.mulberry32(1);
    for (let i = 0; i < 500; i++) { const d = K.digitsFor('sum', 10, rng); if (d.some(x => x > 9 || x < 0)) return false; }
    return true;
  })());
  ok('diff t=9 只能生成 (0,9)', (() => {
    const rng = K.mulberry32(5), seen = new Set();
    for (let i = 0; i < 200; i++) { const d = K.digitsFor('diff', 9, rng); seen.add(d.join(',')); }
    return [...seen].every(s => { const [a, b] = s.split(',').map(Number); return Math.max(a, b) === 9 && Math.min(a, b) === 0; });
  })());
}

/* ---------- 3b. 乘法：可达积、植桩数字、口诀文本 ---------- */
section('[3b] 表内乘法（积）的可达性与口诀');
{
  const MT = K.MUL_TARGETS;
  const closure = new Set();
  for (let a = 1; a <= 9; a++) for (let b = 1; b <= 9; b++) closure.add(a * b);
  ok(`候选积列表 ${MT.length} 个，与"两个一位数之积"的集合完全一致`,
    MT.length === closure.size && MT.every(t => closure.has(t)),
    '列表 ' + MT.join(',') + ' / 闭合集 ' + [...closure].sort((x, y) => x - y).join(','));
  ok('积列表升序且全部落在 1–81', MT.every((t, i) => t >= 1 && t <= 81 && (i === 0 || t > MT[i - 1])));
  ok('11、13、17、19、22、23、44 这些两位数组合不出的数被判定为非法积',
    [11, 13, 17, 19, 22, 23, 44, 46, 50, 55, 58, 60, 66, 70].every(t => !K.isMulTarget(t)),
    [11, 13, 17, 19, 22, 23, 44, 46, 50, 55, 58, 60, 66, 70].filter(t => K.isMulTarget(t)).join(','));
  ok('isMulTarget 与 factorPairs 口径一致', MT.every(t => K.factorPairs(t).length > 0) &&
    [11, 13, 17, 19, 22, 23, 29, 43, 81 + 1].every(t => K.factorPairs(t).length === 0));
  ok('factorPairs(36) = 4×9 / 6×6 / 9×4，且都是 1–9 的数字', (() => {
    const fp = K.factorPairs(36).map(p => p.join('×'));
    return fp.join('|') === '4×9|6×6|9×4' && K.factorPairs(36).every(([a, b]) => a >= 1 && a <= 9 && b >= 1 && b <= 9);
  })(), K.factorPairs(36).map(p => p.join('×')).join('|'));

  let bad = [], seenDigits = new Set();
  for (const t of MT) {
    const rng = K.mulberry32(t * 7919 + 13);
    for (let i = 0; i < 200; i++) {
      const d = K.digitsFor('mul', t, rng);
      if (!d) { bad.push(`mul t=${t} 返回 null`); break; }
      if (d[0] < 1 || d[0] > 9 || d[1] < 1 || d[1] > 9) { bad.push(`mul 数字越出 1–9：${d}`); break; }
      if (d[0] * d[1] !== t) { bad.push(`mul 不达目标：${d} ≠ ${t}`); break; }
      seenDigits.add(d.join(','));
    }
  }
  ok(`全部 ${MT.length} 个积 × 200 次植桩 = ${MT.length * 200} 组，数字在 1–9 且乘积命中目标`, bad.length === 0, bad[0] || '');
  ok('mul 目标 11（凑不出）返回 null，交由 checkJob 拦住', K.digitsFor('mul', 11, K.mulberry32(1)) === null);
  ok('口诀文本：二二得四 / 二五一十 / 三四十二 / 五五二十五 / 九九八十一',
    K.guoju(2, 2) === '二二得四' && K.guoju(2, 5) === '二五一十' && K.guoju(3, 4) === '三四十二' &&
    K.guoju(5, 5) === '五五二十五' && K.guoju(9, 9) === '九九八十一',
    [K.guoju(2, 2), K.guoju(2, 5), K.guoju(3, 4), K.guoju(5, 5), K.guoju(9, 9)].join(' '));
  ok('口诀小数在前（7×2 也读作"二七十四"）', K.guoju(7, 2) === '二七十四' && K.guoju(9, 4) === '四九三十六');
  ok('全部 45 句口诀都能生成，且只由中文数字与"十/得"构成', (() => {
    const n = [];
    for (let a = 1; a <= 9; a++) for (let b = a; b <= 9; b++) {
      const g = K.guoju(a, b);
      if (!/^[一二三四五六七八九]{2}(得)?[一二三四五六七八九十]+$/.test(g)) return false;
      if (/(undefined|NaN|零)/.test(g)) return false;
      n.push(g);
    }
    return n.length === 45 && new Set(n).size === 45;
  })());
  ok('数字转中文：一十 / 十四 / 二十一 / 三十六 / 八十一',
    K.cnNum(10) === '一十' && K.cnNum(14) === '十四' && K.cnNum(21) === '二十一' &&
    K.cnNum(36) === '三十六' && K.cnNum(81) === '八十一',
    [2, 10, 11, 14, 20, 21, 36, 40, 54, 81].map(n => n + '→' + K.cnNum(n)).join(' '));
}

/* ---------- 4. 主流程：各难度包 × 两种盘面 × 多批次 ---------- */
section('[4] 出题主流程自检（audit）');
const PRESETS = K.PRESETS;
function jobsFrom(p, quotaOverride) {
  const j = [];
  for (const t of p.sum) j.push({ kind: 'sum', t, quota: quotaOverride ?? p.quota });
  for (const t of p.diff) j.push({ kind: 'diff', t, quota: quotaOverride ?? p.quota });
  for (const t of p.mul || []) j.push({ kind: 'mul', t, quota: quotaOverride ?? p.quota });
  return j;
}
let issues = [], runs = 0, maxSeen = {}, quotaSum = {};
for (const name of Object.keys(PRESETS)) {
  for (const size of [8, 10]) {
    for (let s = 0; s < 120; s++) {
      let bd;
      try { bd = K.buildBoard({ size, jobs: jobsFrom(PRESETS[name]), seed: 1000 + s * 3571 }); }
      catch (e) { issues.push(`${name}/${size}/seed${1000 + s * 3571} 抛错：${e.message}`); continue; }
      runs++;
      const bad = K.audit(bd);
      if (bad.length) issues.push(`${name}/${size}/seed${bd.seed}: ` + bad[0]);
      maxSeen[name + '/' + size] = Math.max(maxSeen[name + '/' + size] || 0, bd.fullMax);
      quotaSum[name + '/' + size] = bd.totalQuota;
    }
  }
}
ok(`${runs} 次生成全部通过 audit（植桩互不重叠/答案同源/配额兑现）`, issues.length === 0, issues.slice(0, 3).join(' | '));
ok('每卷满分线 = 各目标配额之和', (() => {
  for (const k of Object.keys(quotaSum)) if (quotaSum[k] > maxSeen[k]) return false;
  return true;
})(), '出现 fullMax < totalQuota');
section('[4b] 各难度包在 10×10 上的实际容量');
for (const name of Object.keys(PRESETS)) {
  console.log(`     ${name.padEnd(5)} 目标 ${jobsFrom(PRESETS[name]).length} 个 / 满分 ${quotaSum[name + '/10']} 对 / 本盘最多可达 ${maxSeen[name + '/10']} 对`);
}

/* ---------- 4c. 乘法轮专页：0 死格、算式格式、口诀一致性 ---------- */
section('[4c] 乘法轮的盘面口径');
{
  const mulNames = Object.keys(PRESETS).filter(n => (PRESETS[n].mul || []).length);
  const pureNames = mulNames.filter(n => !PRESETS[n].sum.length && !PRESETS[n].diff.length);
  const mixNames = mulNames.filter(n => PRESETS[n].sum.length || PRESETS[n].diff.length);
  ok('难度包里含乘法的有 ' + mulNames.join('/') + '（其中纯乘法 ' + pureNames.join('/') + '）',
    mulNames.length >= 4, mulNames.join(','));
  let zeroCells = 0, zeroInFiller = 0, badEq = [], badGuoju = [], lowQuota = [], runs = 0, pureRuns = 0, mixZeros = 0;
  for (const name of mulNames) {
    const pure = pureNames.includes(name);
    for (const size of [8, 10]) {
      for (let s = 0; s < 60; s++) {
        const bd = K.buildBoard({ size, jobs: jobsFrom(PRESETS[name]), seed: 5000 + s * 3571 });
        runs++;
        if (pure) pureRuns++;
        const planted = new Set();
        for (const p of bd.plan) { planted.add(p.a); planted.add(p.b); }
        const zeros = bd.grid.reduce((n, d) => n + (d === 0 ? 1 : 0), 0);
        if (zeros) mixZeros++;
        for (let i = 0; i < bd.grid.length; i++) if (bd.grid[i] === 0 && !planted.has(i)) zeroInFiller++;
        if (pure && zeros > 0) zeroCells++;
        for (const k of bd.key) {
          if (k.list.length < k.quota) lowQuota.push(`${name}/${size}/${k.t}：仅 ${k.list.length} 对 < 配额 ${k.quota}`);
          for (const e of k.list) {
            const x = bd.grid[e.a], y = bd.grid[e.b];
            if (k.kind === 'mul') {
              if (!new RegExp('^\\d × \\d = ' + k.t + '$').test(e.eq)) badEq.push(e.eq);
              if (x < 1 || y < 1) badEq.push('积用了 0：' + e.eq);
              if (K.guoju(x, y) !== K.guoju(y, x)) badGuoju.push(x + ',' + y);
            } else if (!new RegExp('^\\d+ [+] \\d+ = ' + k.t + '$|^\\d+ - \\d+ = ' + k.t + '$').test(e.eq)) badEq.push(e.eq);
          }
        }
      }
    }
  }
  ok(`纯乘法卷（${pureNames.join('/')}）共 ${pureRuns} 张，盘内一个 0 都没有`,
    zeroCells === 0, zeroCells + ' 张纯乘法卷出现 0');
  ok('随机补位格里永远不埋 0（0 只能出现在加减植桩对上）', zeroInFiller === 0, zeroInFiller + ' 个补位 0');
  console.log(`     混合卷（${mixNames.join('/')}）里含 0 的张数：${mixZeros} / ${runs}——0 只在和·差的桩上，乘法这一轮用不到它`);
  ok('全部算式格式正确（□×□=t / □+□=t / □−□=t，且结果等于目标数）', badEq.length === 0, badEq.slice(0, 3).join(' | '));
  ok('口诀与格子读数无关（先后顺序不影响口诀）', badGuoju.length === 0, badGuoju.slice(0, 3).join(' | '));
  ok('每个目标的合法对都够涂（不少于配额）', lowQuota.length === 0, lowQuota.slice(0, 2).join(' | '));
  const bd = K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.m2), seed: 31415 });
  ok('m2 卷里每对积的算式都能背出口诀（抽查一条）', (() => {
    const k = bd.key.find(z => z.kind === 'mul'), e = k.list.find(z => z.star) || k.list[0];
    const g = K.guoju(bd.grid[e.a], bd.grid[e.b]);
    return /[一二三四五六七八九]{2}/.test(g) && bd.grid[e.a] * bd.grid[e.b] === k.t;
  })());
  ok('纯加法卷仍然允许 0（不误伤一年级口径）', (() => {
    let hasZero = false;
    for (let s = 0; s < 40; s++) {
      const b2 = K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.std), seed: 600 + s });
      if (b2.grid.some(d => d === 0)) { hasZero = true; break; }
    }
    return hasZero;
  })());
}

/* ---------- 5. 可复现性 ---------- */
section('[5] 同种子必须同盘');
{
  const a = K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.std), seed: 20261111 });
  const b = K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.std), seed: 20261111 });
  ok('两次生成的数字盘面完全相同', a.grid.join('') === b.grid.join(''));
  ok('两次生成的合法对清单相同',
    JSON.stringify(a.key.map(k => k.list.map(e => e.a + '-' + e.b))) ===
    JSON.stringify(b.key.map(k => k.list.map(e => e.a + '-' + e.b))));
  const c = K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.std), seed: 20261112 });
  ok('换个种子就是另一张盘（印 N 份不重复）', c.grid.join('') !== a.grid.join(''));
}

/* ---------- 6. 教学口径：10 以内 ---------- */
section('[6] 10 以内约束与题目质量');
{
  const bd = K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.std), seed: 777 });
  ok('所有和型合法目标 ≤ 10', PRESETS.std.sum.every(t => t <= K.MAXV));
  ok('答案里没有"和 > 10"的条目', (() => {
    for (const k of bd.key) {
      if (k.kind !== 'sum') continue;
      for (const e of k.list) {
        const v = bd.grid[e.a] + bd.grid[e.b];
        if (v > K.MAXV) return false;
        if (v !== k.t) return false;
      }
    }
    return true;
  })());
  const digits = bd.grid.join('').split('').map(Number);
  const dist = new Array(10).fill(0);
  digits.forEach(d => dist[d]++);
  ok('数字覆盖 0–9 全部出现（避免"永远凑不出"的死角）', dist.every(c => c > 0), JSON.stringify(dist));
  ok('单数字占比不超过 25%（分布够随机）', Math.max(...dist) / 100 <= 0.25, JSON.stringify(dist));
  ok('每个目标都确有可涂对', bd.key.every(k => k.list.length >= k.quota));
  const eqs = bd.key.flatMap(k => k.list.map(e => e.eq));
  ok('算式字符串格式正确（a + b = t / a - b = t）',
    eqs.every(s => /^\d+ [+] \d+ = \d+$|^\d+ - \d+ = \d+$/.test(s)), eqs.find(s => !/^\d+ [+] \d+ = \d+$|^\d+ - \d+ = \d+$/.test(s)));
  ok('差型算式一定是大减小，且差等于目标数', bd.key.filter(k => k.kind === 'diff').flatMap(k => k.list)
    .every(e => { const g = /^(\d+) - (\d+) = (\d+)$/.exec(e.eq); return g && Number(g[1]) >= Number(g[2]) && Number(g[1]) - Number(g[2]) === Number(g[3]); }));
  ok('和型算式加数顺序与盘面读数一致，且和等于目标数', bd.key.filter(k => k.kind === 'sum').flatMap(k => k.list)
    .every(e => { const g = /^(\d+) \+ (\d+) = (\d+)$/.exec(e.eq); return g && Number(g[1]) + Number(g[2]) === Number(g[3]); }));
}

/* ---------- 7. 反向测试：故意破坏必须被抓到 ---------- */
section('[7] 反向测试（篡改必须报错）');
{
  const fresh = () => K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.std), seed: 4242 });
  let t = fresh(); t.grid[5] = 3;
  ok('改一个盘面数字 → audit 报警（答案与盘面不再同源）', K.audit(t).length > 0);

  t = fresh(); const q = t.plan[0], a = q.a;
  q.t = (q.kind === 'sum' ? q.t + 1 : q.t + 1);
  ok('植桩记录被改成不达目标 → audit 报警', K.audit(t).some(s => /植桩|覆盖|非法/.test(s)));

  t = fresh();
  t.plan.push({ a: t.plan[0].a, b: t.plan[0].b + 1, kind: 'sum', t: t.plan[0].t, job: 0, seq: 9 });
  ok('植桩格重复占用 → audit 报警', K.audit(t).some(s => /重复占用/.test(s)));

  t = fresh(); t.key[0].quota = t.key[0].planted + 3;
  ok('配额虚报高于植桩兑现 → audit 报警', K.audit(t).some(s => /覆盖不足|计数异常/.test(s)));

  t = fresh(); t.key[1].list.pop();
  ok('答案清单少一条（与穷举不符）→ audit 报警', K.audit(t).some(s => /条数/ .test(s)));

  t = fresh(); t.fullMax = t.totalQuota - 5;
  ok('满分线低于配额 → audit 报警', K.audit(t).some(s => /fullMax/.test(s)));

  let err = '';
  try { K.buildBoard({ size: 8, jobs: [{ kind: 'sum', t: 7, quota: 40 }], seed: 1 }); } catch (e) { err = e.message; }
  ok('8×8 要 40 对（超容量 32）→ 明确抛错而非硬印', /超出盘面容量/.test(err), err);

  err = '';
  try { K.buildBoard({ size: 10, jobs: [{ kind: 'sum', t: 14, quota: 1 }], seed: 1 }); } catch (e) { err = e.message; }
  ok('目标数 14 越出 10 以内 → 抛错', /0–10/.test(err), err);

  err = '';
  try { K.buildBoard({ size: 10, jobs: [], seed: 1 }); } catch (e) { err = e.message; }
  ok('一个目标都不选 → 抛错', /至少选一个/.test(err), err);

  // 乘法专属红线
  err = '';
  try { K.buildBoard({ size: 10, jobs: [{ kind: 'mul', t: 11, quota: 2 }], seed: 1 }); } catch (e) { err = e.message; }
  ok('积=11（两个一位数乘不出来）→ 明确抛错，不印无解卷', /凑不出来/.test(err), err);
  for (const t of [13, 17, 19, 55, 60, 100]) {
    err = '';
    try { K.buildBoard({ size: 10, jobs: [{ kind: 'mul', t, quota: 1 }], seed: 2 }); } catch (e) { err = e.message; }
    ok(`积=${t} 同样被拦住`, /凑不出来/.test(err), err);
  }
  err = '';
  try { K.buildBoard({ size: 8, jobs: [{ kind: 'mul', t: 36, quota: 40 }], seed: 3 }); } catch (e) { err = e.message; }
  ok('乘法也要遵守盘面容量（8×8 要 40 对 → 抛错）', /超出盘面容量/.test(err), err);

  let mbd = K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.m2), seed: 90210 });
  const free = mbd.grid.findIndex((d, i) => !mbd.plan.some(p => p.a === i || p.b === i));
  mbd.grid[free] = 0;
  ok('乘法轮里塞进一个 0（死格）→ audit 报警', K.audit(mbd).some(s => /补位出现 0/.test(s)), JSON.stringify(K.audit(mbd).slice(0, 2)));

  mbd = K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.m2), seed: 90210 });
  const pq = mbd.plan.find(p => p.kind === 'mul');
  mbd.grid[pq.a] = 1; mbd.grid[pq.b] = 1;
  ok('把植桩的乘法对改成 1×1（不达目标）→ audit 报警', K.audit(mbd).some(s => /植桩对不达目标/.test(s)));

  mbd = K.buildBoard({ size: 10, jobs: jobsFrom(PRESETS.m2), seed: 90210 });
  mbd.key.find(k => k.kind === 'mul').list.push({ a: 0, b: 1, dir: 'h', eq: '1 × 1 = 6', star: false });
  ok('答案页多塞一条假积对 → audit 报警（与穷举条数不符）', K.audit(mbd).some(s => /条数|非法/.test(s)));
}

/* ---------- 8. 压力：极端配置只许"要么成功要么明说" ---------- */
section('[8] 极端配置');
{
  const cases = [
    { label: '10×10 集齐和 0–10 各 1 对', size: 10, jobs: Array.from({ length: 11 }, (_, t) => ({ kind: 'sum', t, quota: 1 })) },
    { label: '10×10 和+差 12 目标 × 4 对（=48 对，逼近容量）', size: 10,
      jobs: [].concat([2, 3, 5, 6, 7, 8, 9, 10].map(t => ({ kind: 'sum', t, quota: 4 })), [1, 2, 3, 4].map(t => ({ kind: 'diff', t, quota: 4 }))) },
    { label: '8×8 和=10 差=0 各 4 对', size: 8, jobs: [{ kind: 'sum', t: 10, quota: 4 }, { kind: 'diff', t: 0, quota: 4 }] },
    { label: '10×10 全目标 0–10 和与差各 2 对（44 对）', size: 10,
      jobs: [].concat(Array.from({ length: 11 }, (_, t) => ({ kind: 'sum', t, quota: 2 })), Array.from({ length: 10 }, (_, t) => ({ kind: 'diff', t, quota: 2 }))) },
    { label: '10×10 积集齐 1–9 的口诀开头（9 目标 × 2 对）', size: 10,
      jobs: [1, 2, 3, 4, 5, 6, 7, 8, 9].map(t => ({ kind: 'mul', t, quota: 2 })) },
    { label: '10×10 大积 36/48/63/72/81 各 3 对（15 对）', size: 10,
      jobs: [36, 48, 63, 72, 81].map(t => ({ kind: 'mul', t, quota: 3 })) },
    { label: '10×10 和+差+积 12 目标 × 3 对（36 对）', size: 10,
      jobs: [].concat([4, 6, 8, 10].map(t => ({ kind: 'sum', t, quota: 3 })), [1, 3].map(t => ({ kind: 'diff', t, quota: 3 })),
                       [6, 12, 18, 24, 30, 36].map(t => ({ kind: 'mul', t, quota: 3 }))) },
    { label: '8×8 积 2–9 各 2 对（16 对 = 容量上限的一半）', size: 8,
      jobs: [2, 3, 4, 5, 6, 7, 8, 9].map(t => ({ kind: 'mul', t, quota: 2 })) },
  ];
  for (const c of cases) {
    let good = 0, thrown = 0, bad = [];
    for (let s = 0; s < 40; s++) {
      try {
        const bd = K.buildBoard({ size: c.size, jobs: c.jobs, seed: 90000 + s * 7919 });
        good++;
        const a = K.audit(bd);
        if (a.length) bad.push(a[0]);
      } catch (e) { thrown++; if (!/排不出|超出盘面容量/.test(e.message)) bad.push('意外异常：' + e.message); }
    }
    ok(`${c.label} → ${good} 成功 / ${thrown} 明确拒答，且成功卷 audit 全通过`,
      bad.length === 0 && good > 0, bad.slice(0, 2).join(' | '));
  }
}

console.log(`\n合计 ${pass} 项通过，${fail} 项失败。`);
process.exit(fail ? 1 : 0);
