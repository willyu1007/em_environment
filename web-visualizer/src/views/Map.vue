<template>
  <div class="map-page">
    <div class="sidebar">
      <h3>数据加载</h3>
      <div class="group">
        <div class="title">配置来源</div>
        <div class="field" style="gap:6px;">
          <label><input type="radio" value="file" v-model="configMode" /> 从文件/示例</label>
          <label><input type="radio" value="editor" v-model="configMode" /> 参数编辑器</label>
        </div>
      </div>

      <div v-if="configMode==='file'" class="group">
        <div class="title">从示例选择</div>
        <div class="field">
          <label>示例文件：</label>
          <select v-model="selectedExample" style="flex:1;">
            <option v-for="e in exampleList" :key="e" :value="e">{{ e }}</option>
          </select>
        </div>
        <div class="hint">仅允许选择项目路径下 examples/ 目录中以 request_ 开头的 JSON 文件。</div>
        <div class="ok" v-if="exampleSuccess">{{ exampleSuccess }}</div>
        <div class="warn" v-if="exampleReadError">{{ exampleReadError }}</div>
        <div class="warn" v-if="exampleParseError">{{ exampleParseError }}</div>
        <div class="group" v-if="exampleConfig">
          <div class="title">参数摘要</div>
          <div class="ro-line">区域点数：{{ (exampleConfig.region?.polygon||[]).length }}</div>
          <details style="margin:4px 0;">
            <summary>区域坐标</summary>
            <ul>
              <li v-for="(p,i) in (exampleConfig.region?.polygon||[])" :key="i">点{{ i+1 }}: ({{ p.lat }}, {{ p.lon }})</li>
            </ul>
          </details>
          <div class="ro-line">网格：res={{ exampleConfig.grid?.resolution_deg }}°，alt={{ exampleConfig.grid?.alt_m }}m</div>
          <div class="ro-line">传播模型：{{ exampleConfig.environment?.propagation?.model }}</div>
          <details style="margin:4px 0;">
            <summary>频段（{{ (exampleConfig.bands||[]).length }}）</summary>
            <ul>
              <li v-for="(b,i) in (exampleConfig.bands||[])" :key="i">{{ b.name }}：{{ b.f_min_MHz }}-{{ b.f_max_MHz }} MHz（ref_bw {{ b.ref_bw_kHz }} kHz）</li>
            </ul>
          </details>
        </div>
        <div class="group" v-if="exampleConfig && (exampleConfig.sources||[]).length">
          <div class="title">辐射源设置</div>
          <div class="hint">辐射源数量：{{ (exampleConfig.sources||[]).length }}</div>
          <div class="warn" v-if="exampleReadError">{{ exampleReadError }}</div>
          <div class="warn" v-if="exampleParseError">{{ exampleParseError }}</div>
          <details v-for="(s,idx) in exampleConfig.sources" :key="idx" class="src-readonly">
            <summary>源 {{ s.id || ('source_'+(idx+1)) }}</summary>
            <div class="ro-line">类型: {{ s.type }}</div>
            <div class="ro-line">位置: ({{ s.position?.lat }}, {{ s.position?.lon }}, {{ s.position?.alt_m }}m)</div>
            <div class="ro-line">EIRP: {{ s.emission?.eirp_dBm }} dBm</div>
            <div class="ro-line">频率: {{ s.emission?.center_freq_MHz }} MHz</div>
            <div class="ro-line">带宽: {{ s.emission?.bandwidth_MHz }} MHz</div>
            <div class="ro-line">占空比: {{ s.emission?.duty_cycle }}</div>
            <div class="ro-title">波束方向</div>
            <div class="ro-line">方位角: {{ s.antenna?.pointing?.az_deg }}°</div>
            <div class="ro-line">仰角: {{ s.antenna?.pointing?.el_deg }}°</div>
            <div class="ro-line">水平波束宽度: {{ s.antenna?.pattern?.hpbw_deg }}°</div>
            <div class="ro-line">垂直波束宽度: {{ s.antenna?.pattern?.vpbw_deg }}°</div>
            <div class="ro-line">副瓣模板: {{ s.antenna?.pattern?.sidelobe_template }}</div>
            <div class="ro-title">扫描模式</div>
            <div class="ro-line">模式: {{ s.antenna?.scan?.mode }}</div>
            <div class="ro-line" v-if="s.antenna?.scan?.mode!=='none'">转速: {{ s.antenna?.scan?.rpm }} rpm</div>
            <div class="ro-line" v-if="s.antenna?.scan?.mode==='sector'">扇区角: {{ s.antenna?.scan?.sector_deg }}°</div>
          </details>
        </div>
      </div>
      <p class="hint">提示：选择示例后可在“地图可视化”标签页选择频段并加载 outputs/latest 数据。</p>

      <details v-if="configMode==='editor'" class="editor" open>
        <summary>🛠 参数编辑器（源配置）</summary>
        <div class="group">
          <div class="title">辐射源</div>
          <div class="field">
            <button type="button" @click="addSource">➕ 新增源</button>
            <button type="button" @click="clearSources" style="margin-left:8px;">🗑️ 清空</button>
          </div>
          <div v-for="(s,idx) in editor.sources" :key="idx" class="source-card">
            <div class="field"><label>ID</label><input type="text" v-model="s.id" /></div>
            <div class="field"><label>类型</label>
              <select v-model="s.type">
                <option value="radar">radar</option>
                <option value="comm">comm</option>
                <option value="jammer">jammer</option>
                <option value="other">other</option>
              </select>
            </div>
            <div class="field"><label>lat</label><input type="number" step="0.01" v-model.number="s.position.lat" /></div>
            <div class="field"><label>lon</label><input type="number" step="0.01" v-model.number="s.position.lon" /></div>
            <div class="field"><label>alt_m</label><input type="number" step="10" v-model.number="s.position.alt_m" /></div>
            <div class="field"><label>eirp_dBm</label><input type="number" step="1" v-model.number="s.emission.eirp_dBm" /></div>
            <div class="field"><label>center_freq_MHz</label><input type="number" step="1" v-model.number="s.emission.center_freq_MHz" /></div>
            <div class="field"><label>bandwidth_MHz</label><input type="number" step="1" v-model.number="s.emission.bandwidth_MHz" /></div>
            <div class="field"><label>polarization</label>
              <select v-model="s.emission.polarization">
                <option>H</option><option>V</option><option>RHCP</option><option>LHCP</option>
              </select>
            </div>
            <div class="field"><label>duty_cycle</label><input type="number" step="0.1" min="0" max="1" v-model.number="s.emission.duty_cycle" /></div>
            <div class="field"><label>az_deg</label><input type="number" step="1" v-model.number="s.antenna.pointing.az_deg" /></div>
            <div class="field"><label>el_deg</label><input type="number" step="1" v-model.number="s.antenna.pointing.el_deg" /></div>
            <div class="field"><label>hpbw_deg</label><input type="number" step="0.5" v-model.number="s.antenna.pattern.hpbw_deg" /></div>
            <div class="field"><label>vpbw_deg</label><input type="number" step="0.5" v-model.number="s.antenna.pattern.vpbw_deg" /></div>
            <div class="field">
              <button type="button" @click="removeSource(idx)">删除该源</button>
            </div>
          </div>
        </div>
      </details>
    </div>

    <div class="content">
      <div class="tabs">
        <button :class="{active: tab==='map'}" @click="tab='map'">🗺️ 地图可视化</button>
        <button :class="{active: tab==='stats'}" @click="tab='stats'">📊 统计图表</button>
        <button :class="{active: tab==='topk'}" @click="tab='topk'">🔍 Top-K分析</button>
        <button :class="{active: tab==='config'}" @click="tab='config'">ℹ️ 配置信息</button>
      </div>

      <div v-show="tab==='map'" class="panel">
        <div class="group">
          <div class="title">数据源（outputs/latest）</div>
          <div class="field">
            <label>频段：</label>
            <select v-model="selectedBand">
              <option v-for="b in availableBands" :key="b" :value="b">{{ b }}</option>
            </select>
            <button type="button" @click="refreshBands">刷新</button>
            <button type="button" @click="loadBandData">加载</button>
          </div>
          <div class="warn" v-if="availableBands.length===0">未检测到 outputs/latest 下的频段目录，请先运行计算或点击“刷新”。</div>
          <div class="hint" v-if="lastLoadInfo">{{ lastLoadInfo }}</div>
        </div>
        <div class="group">
          <div class="title">色彩方案与映射</div>
          <div class="field">
            <select v-model="selectedScheme">
              <option v-for="(label, key) in colorSchemeOptions" :key="key" :value="key">{{ label }}</option>
            </select>
            <span style="flex:1"></span>
            <label>值域映射</label>
            <input type="number" v-model.number="vmin" style="width:90px;" /> ~
            <input type="number" v-model.number="vmax" style="width:90px;" />
            <label style="margin-left:8px;">自定义色带</label>
            <input type="color" v-model="colorStart" /> →
            <input type="color" v-model="colorEnd" />
            <button type="button" @click="rerenderHeat">应用</button>
          </div>
        </div>
        <div class="two-col">
          <div class="map-container"><div ref="mapEl" class="map"></div></div>
          <div class="beam-panel">
            <h4>波束示意</h4>
            <svg class="beam" viewBox="-100 -100 200 200" preserveAspectRatio="xMidYMid meet">
              <g v-for="(s,idx) in beamSources" :key="idx" :fill="palette[idx%palette.length]" :stroke="palette[idx%palette.length]" stroke-width="0.5" opacity="0.6">
                <circle :cx="relPos(s).x" :cy="relPos(s).y" r="1.5" />
                <path :d="sectorPath(s)" />
              </g>
            </svg>
            <div class="beam-legend">相对坐标示意（km）</div>
          </div>
        </div>
        <div class="group">
          <div class="title">数据统计</div>
          <div v-if="stats && stats.count>0" class="stats-grid">
            <div class="metric"><div class="k">最小值</div><div class="v">{{ stats.min.toFixed(2) }}</div></div>
            <div class="metric"><div class="k">最大值</div><div class="v">{{ stats.max.toFixed(2) }}</div></div>
            <div class="metric"><div class="k">平均值</div><div class="v">{{ stats.mean.toFixed(2) }}</div></div>
            <div class="metric"><div class="k">标准差</div><div class="v">{{ stats.std.toFixed(2) }}</div></div>
            <div class="metric"><div class="k">中位数</div><div class="v">{{ stats.median.toFixed(2) }}</div></div>
            <div class="metric"><div class="k">有效像素</div><div class="v">{{ stats.count }}</div></div>
          </div>
          <div v-else class="hint">尚未加载或无有效数据</div>
        </div>
      </div>

      <div v-show="tab==='stats'" class="panel">
        <h3>数据统计</h3>
        <div v-if="stats && stats.count>0" class="stats-grid">
          <div class="metric"><div class="k">最小值</div><div class="v">{{ stats.min.toFixed(2) }}</div></div>
          <div class="metric"><div class="k">最大值</div><div class="v">{{ stats.max.toFixed(2) }}</div></div>
          <div class="metric"><div class="k">平均值</div><div class="v">{{ stats.mean.toFixed(2) }}</div></div>
          <div class="metric"><div class="k">标准差</div><div class="v">{{ stats.std.toFixed(2) }}</div></div>
          <div class="metric"><div class="k">中位数</div><div class="v">{{ stats.median.toFixed(2) }}</div></div>
          <div class="metric"><div class="k">有效像素</div><div class="v">{{ stats.count }}</div></div>
        </div>
        <div v-else class="hint">尚未加载或无有效数据</div>
        <div class="pcts" v-if="percentiles.length">
          <h4>分位数</h4>
          <ul>
            <li v-for="p in percentiles" :key="p.q">{{ p.q }}%：{{ p.v.toFixed(2) }}</li>
          </ul>
        </div>
      </div>

      <div v-show="tab==='topk'" class="panel">
        <h3>Top-K 贡献源分析</h3>
        <div v-if="topkSummary.length">
          <div class="bar-list">
            <div v-for="item in topkSummary" :key="item.id" class="bar-row">
              <div class="bar-label">{{ item.id }}</div>
              <div class="bar">
                <div class="bar-fill" :style="{ width: (item.fraction*100).toFixed(1)+'%' }"></div>
              </div>
              <div class="bar-value">{{ (item.fraction*100).toFixed(1) }}%</div>
            </div>
          </div>
          <details class="table-wrap">
            <summary>查看明细表（前 200 行）</summary>
            <table>
              <thead>
                <tr>
                  <th>lat</th><th>lon</th><th>rank</th><th>source_id</th><th>fraction</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in topkRows.slice(0,200)" :key="row.__idx">
                  <td>{{ row.lat }}</td>
                  <td>{{ row.lon }}</td>
                  <td>{{ row.rank }}</td>
                  <td>{{ row.source_id }}</td>
                  <td>{{ row.fraction.toFixed(4) }}</td>
                </tr>
              </tbody>
            </table>
          </details>
        </div>
        <div v-else class="hint">尚未加载 Parquet 或未解析出 fraction/source_id 列</div>
      </div>

      <div v-show="tab==='config'" class="panel">
        <h3>配置信息</h3>
        <div v-if="config">
          <div class="cfg-block">
            <h4>计算区域</h4>
            <div v-if="config.region && config.region.polygon && config.region.polygon.length">
              <ul>
                <li v-for="(p,i) in config.region.polygon" :key="i">点{{ i+1 }}: ({{ p.lat }}, {{ p.lon }})</li>
              </ul>
            </div>
          </div>
          <div class="cfg-block">
            <h4>网格设置</h4>
            <div>分辨率(°): {{ config.grid?.resolution_deg }}</div>
            <div>高度(m): {{ config.grid?.alt_m }}</div>
          </div>
          <div class="cfg-block">
            <h4>环境参数</h4>
            <div>传播模型: {{ config.environment?.propagation?.model }}</div>
            <div>大气损耗: {{ config.environment?.atmosphere?.gas_loss }}</div>
          </div>
          <div class="cfg-block">
            <h4>辐射源（{{ (config.sources||[]).length }}）</h4>
            <div class="beam-wrap">
              <svg class="beam" viewBox="-100 -100 200 200" preserveAspectRatio="xMidYMid meet">
                <g v-for="(s,idx) in (config.sources||[])" :key="idx" :fill="palette[idx%palette.length]" :stroke="palette[idx%palette.length]" stroke-width="0.5" opacity="0.6">
                  <circle :cx="relPos(s).x" :cy="relPos(s).y" r="1.5" />
                  <path :d="sectorPath(s)" />
                </g>
              </svg>
              <div class="beam-legend">相对坐标示意（单位：km，中心为区域中心近似）</div>
            </div>
          </div>
        </div>
        <div v-else class="hint">可在侧边栏加载 JSON 配置以查看明细与波束示意</div>
      </div>
    </div>
    <div class="rightbar">
      <h3>计算配置</h3>
      <div class="group">
        <div class="title">区域（矩形）</div>
        <div class="grid-2">
          <div class="field"><label>lat_min</label><input type="number" step="0.01" v-model.number="editor.regionRect.lat_min" /></div>
          <div class="field"><label>lat_max</label><input type="number" step="0.01" v-model.number="editor.regionRect.lat_max" /></div>
          <div class="field"><label>lon_min</label><input type="number" step="0.01" v-model.number="editor.regionRect.lon_min" /></div>
          <div class="field"><label>lon_max</label><input type="number" step="0.01" v-model.number="editor.regionRect.lon_max" /></div>
        </div>
      </div>
      <div class="group">
        <div class="title">网格与影响</div>
        <div class="grid-2">
          <div class="field"><label>resolution_deg</label><input type="number" step="0.001" v-model.number="editor.grid.resolution_deg" /></div>
          <div class="field"><label>alt_m</label><input type="number" step="10" v-model.number="editor.grid.alt_m" /></div>
          <div class="field"><label>influence_buffer_km</label><input type="number" step="10" v-model.number="editor.influence_buffer_km" /></div>
        </div>
      </div>
      <div class="group">
        <div class="title">环境</div>
        <div class="field">
          <label>propagation.model</label>
          <select v-model="editor.environment.propagation.model">
            <option value="free_space">free_space</option>
            <option value="two_ray_flat">two_ray_flat</option>
          </select>
        </div>
        <div class="grid-2">
          <div class="field"><label>gas_loss</label><input type="text" v-model="editor.environment.atmosphere.gas_loss" /></div>
          <div class="field"><label>rain_rate_mmph</label><input type="number" step="1" v-model.number="editor.environment.atmosphere.rain_rate_mmph" /></div>
          <div class="field"><label>fog_lwc_gm3</label><input type="number" step="0.1" v-model.number="editor.environment.atmosphere.fog_lwc_gm3" /></div>
        </div>
      </div>
      <div class="group">
        <div class="title">频段</div>
        <div class="field">
          <select multiple size="6" v-model="editor.selectedBands" style="width:100%;">
            <option v-for="b in defaultBandDefs" :key="b.name" :value="b.name">{{ b.name }}</option>
          </select>
        </div>
      </div>
      <div class="group">
        <div class="title">计算参数</div>
        <div class="grid-2">
          <div class="field"><label>combine_sources</label><select v-model="editor.combine_sources"><option value="power_sum">power_sum</option></select></div>
          <div class="field"><label>temporal_agg</label><select v-model="editor.temporal_agg"><option value="peak">peak</option></select></div>
        </div>
      </div>
      <div class="group">
        <div class="title">运算与导出</div>
        <div class="field"><label>REST 基址</label><input type="text" v-model="restBase" placeholder="http://localhost:8000" style="width:100%;" /></div>
        <div class="field" style="gap:8px;">
          <button type="button" @click="downloadConfig">导出 JSON</button>
          <button type="button" @click="runCompute">运行计算(REST)</button>
        </div>
        <div class="field"><label>输出目录</label><input type="text" value="outputs/latest" readonly /></div>
        <div class="hint" v-if="lastComputeInfo">{{ lastComputeInfo }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed, watchEffect } from 'vue';
import * as L from 'leaflet';
import { fromArrayBuffer } from 'geotiff';
import initParquet, { readParquet } from 'parquet-wasm';

const mapEl = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;
let rasterLayer: any = null;

const tab = ref<'map'|'stats'|'topk'|'config'>('map');
const colorStart = ref('#1e90ff');
const colorEnd = ref('#ffeb3b');
const vmin = ref(40);
const vmax = ref(120);

// 颜色方案
const colorSchemeOptions: Record<string,string> = {
  'blue_to_red': '蓝-青-绿-黄-橙-红 (推荐)',
  'green_to_red': '绿-黄-橙-红',
  'purple_to_yellow': '紫-蓝-青-绿-黄-白',
  'cool_to_warm': '深蓝-蓝-浅蓝-浅绿-橙-红'
};
const selectedScheme = ref<keyof typeof colorSchemeOptions>('blue_to_red');

// GeoTIFF 缓存
let tiffData: Float32Array | null = null;
let tiffWidth = 0;
let tiffHeight = 0;
let tiffBBox: [number, number, number, number] | null = null; // [minX, minY, maxX, maxY]

// Parquet 缓存
const topkRows = ref<Array<{ __idx:number; lat:number; lon:number; rank:number; source_id:string; fraction:number }>>([]);

// 配置 JSON
const config = ref<any | null>(null);
const restBase = ref<string>('http://localhost:8000');
const lastComputeInfo = ref<string>('');
const lastLoadInfo = ref<string>('');
const configMode = ref<'file'|'editor'>('file');
const selectedExample = ref<string>('request_basic_free_space.json');
const exampleList = [
  'request_basic_free_space.json',
  'request_comm_and_jammer.json',
  'request_highland_complex.json',
  'request_maritime_network.json',
  'request_mega_urban.json',
  'request_multi_band_dense.json',
  'request_two_ray.json',
  'request_wide_area.json'
];

// 选择示例后，自动从 /examples/ 拉取并解析，显示只读辐射源详情
const exampleConfig = ref<any | null>(null);
const exampleReadError = ref<string>('');
const exampleParseError = ref<string>('');
const exampleSuccess = ref<string>('');
async function loadExampleConfig(name: string){
  try{
    // 优先使用 Vite 的 /@fs 绝对路径直读，避免 SPA 回退
    // __EXAMPLES_ABS__ 由 vite.config.ts define 注入
    // @ts-ignore
    const absBase: string = typeof __EXAMPLES_ABS__ !== 'undefined' ? __EXAMPLES_ABS__ : '';
    const url = absBase ? `/@fs/${absBase}/${encodeURIComponent(name)}` : `/examples/${encodeURIComponent(name)}`;
    const res = await fetch(url);
    if (!res.ok) {
      exampleConfig.value = null;
      config.value = null;
      exampleReadError.value = `示例文件读取失败（HTTP ${res.status}）`;
      exampleParseError.value = '';
      exampleSuccess.value = '';
      return;
    }
    const text = await res.text();
    try {
      const json = JSON.parse(text);
      exampleConfig.value = json;
      config.value = exampleConfig.value;
      exampleReadError.value = '';
      exampleParseError.value = '';
      exampleSuccess.value = `已成功载入示例：${name}`;
      setTimeout(()=>{ exampleSuccess.value = ''; }, 3000);
    } catch (e:any) {
      exampleConfig.value = null;
      config.value = null;
      exampleReadError.value = '';
      exampleParseError.value = `示例文件解析失败：${e?.message||'JSON 语法错误'}`;
      exampleSuccess.value = '';
    }
  }catch{
    exampleConfig.value = null;
    config.value = null;
    exampleReadError.value = '示例文件读取失败（网络或跨域）';
    exampleParseError.value = '';
    exampleSuccess.value = '';
  }
}

watchEffect(()=>{
  if (configMode.value === 'file' && selectedExample.value){
    loadExampleConfig(selectedExample.value);
  }
});

// 进入页面时尝试枚举 outputs/latest 频段
onMounted(() => { refreshBands(); });

// 地图可视化：outputs/latest 频段列举与加载
const availableBands = ref<string[]>([]);
const selectedBand = ref<string>('');
async function refreshBands(){
  try{
    const res = await fetch('/__dev/outputs');
    const data = await res.json();
    availableBands.value = Array.isArray(data.bands) ? data.bands : [];
    if ((!availableBands.value || availableBands.value.length===0) && exampleConfig.value?.bands?.length){
      // 回退：用示例里的频段名称占位，提示用户先运行计算
      availableBands.value = exampleConfig.value.bands.map((b:any)=>b.name).filter((x:string)=>!!x);
    }
    if (!selectedBand.value && availableBands.value.length) selectedBand.value = availableBands.value[0];
  }catch{ availableBands.value = []; }
}
async function loadBandData(){
  if (!selectedBand.value) return;
  // 加载 tiff
  const tiffUrl = `/outputs/latest/${encodeURIComponent(selectedBand.value)}/${encodeURIComponent(selectedBand.value)}_field_strength.tif`;
  lastLoadInfo.value = '正在加载 GeoTIFF...';
  const tifResp = await fetch(tiffUrl);
  if (tifResp.ok){ const buf = await tifResp.arrayBuffer(); await loadTiffBuffer(buf); lastLoadInfo.value = 'GeoTIFF 已加载'; }
  else { lastLoadInfo.value = `加载 GeoTIFF 失败: ${tifResp.status}`; return; }
  // 加载 parquet
  const pqUrl = `/outputs/latest/${encodeURIComponent(selectedBand.value)}/${encodeURIComponent(selectedBand.value)}_topk.parquet`;
  const pqResp = await fetch(pqUrl);
  if (pqResp.ok){ const buf = await pqResp.arrayBuffer(); await loadParquetBuffer(buf); lastLoadInfo.value = lastLoadInfo.value + '，Parquet 已加载'; }
  else { lastLoadInfo.value = lastLoadInfo.value + `，Parquet 加载失败: ${pqResp.status}`; }
}
function onBandChange(){ /* 预留：切换时不自动加载 */ }

async function loadTiffBuffer(ab:ArrayBuffer){
  const tiff = await fromArrayBuffer(ab);
  const image = await tiff.getImage();
  const bbox = image.getBoundingBox();
  const width = image.getWidth();
  const height = image.getHeight();
  const rasters = await image.readRasters({ interleave: true, pool: undefined, width, height });
  const data = rasters as Float32Array;
  tiffData = data; tiffWidth = width; tiffHeight = height; tiffBBox = [bbox[0], bbox[1], bbox[2], bbox[3]];
  drawHeat();
}
async function loadParquetBuffer(ab:ArrayBuffer){
  await ensureParquet();
  const bytes = new Uint8Array(ab);
  const table = readParquet(bytes);
  const latCol = table.get('lat');
  const lonCol = table.get('lon');
  const rankCol = table.get('rank');
  const srcCol = table.get('source_id');
  const fracCol = table.get('fraction');
  topkRows.value = [];
  const length = latCol ? latCol.length : 0;
  for (let i = 0; i < length; i++) {
    const lat = latCol?.get(i); const lon = lonCol?.get(i); const rank = rankCol?.get(i); const source_id = srcCol?.get(i); const fraction = fracCol?.get(i);
    if (typeof lat !== 'number' || typeof lon !== 'number' || typeof rank !== 'number' || typeof fraction !== 'number') continue;
    topkRows.value.push({ __idx: i, lat, lon, rank, source_id: String(source_id), fraction });
  }
  if (map) {
    const sample = topkRows.value.filter(r => r.rank === 0).slice(0, 2000);
    for (const r of sample) { L.circleMarker([r.lat, r.lon], { radius: 2, color: '#f44336', weight: 1 }).addTo(map).bindTooltip(r.source_id); }
  }
}
function rerenderHeat(){ if (tiffData) drawHeat(); }
function drawHeat(){
  if (!tiffData || !tiffBBox || !map) return;
  const width = tiffWidth, height = tiffHeight, data = tiffData;
  const canvas = document.createElement('canvas'); canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext('2d')!; const img = ctx.createImageData(width, height); const toColor = getColorScale();
  for (let i = 0; i < data.length; i++) {
    const v = data[i]; let a = 0; let r = 0, g = 0, b = 0;
    if (Number.isFinite(v)) { const t = Math.max(0, Math.min(1, (v - vmin.value) / Math.max(1e-6, (vmax.value - vmin.value)))); const [rr,gg,bb] = toColor(t); r=rr; g=gg; b=bb; a=255; }
    const j = i*4; img.data[j]=r; img.data[j+1]=g; img.data[j+2]=b; img.data[j+3]=a;
  }
  ctx.putImageData(img, 0, 0);
  const bounds = L.latLngBounds([tiffBBox[1], tiffBBox[0]], [tiffBBox[3], tiffBBox[2]]);
  if (rasterLayer && map) { try { map.removeLayer(rasterLayer); } catch {} }
  // 使用 blob URL，避免 dataURL 过长导致失败
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    rasterLayer = L.imageOverlay(url, bounds, { opacity: 0.85, interactive: false });
    rasterLayer.addTo(map);
    try { map.fitBounds(bounds); } catch {}
    // 清理 URL
    setTimeout(()=>URL.revokeObjectURL(url), 10000);
  }, 'image/png');
}

// 配置编辑器状态
const defaultBandDefs = [
  { name: 'VHF', f_min_MHz: 100, f_max_MHz: 300 },
  { name: 'UHF', f_min_MHz: 300, f_max_MHz: 1000 },
  { name: 'L', f_min_MHz: 1000, f_max_MHz: 2000 },
  { name: 'S', f_min_MHz: 2000, f_max_MHz: 4000 },
  { name: 'C', f_min_MHz: 4000, f_max_MHz: 8000 },
  { name: 'X', f_min_MHz: 8000, f_max_MHz: 12000 },
  { name: 'Ku', f_min_MHz: 12000, f_max_MHz: 18000 }
];

const editor = ref<any>({
  regionRect: { lat_min: 33.2, lat_max: 34.1, lon_min: 118.1, lon_max: 119.2 },
  grid: { resolution_deg: 0.01, alt_m: 100 },
  influence_buffer_km: 200,
  environment: {
    propagation: { model: 'free_space' },
    atmosphere: { gas_loss: 'auto', rain_rate_mmph: 0, fog_lwc_gm3: 0 },
    earth: { k_factor: 1.3333333333 }
  },
  selectedBands: ['VHF','UHF','L','S'],
  metric: 'E_field_dBuV_per_m',
  combine_sources: 'power_sum',
  temporal_agg: 'peak',
  limits: { max_sources: 50, max_region_km: 200 },
  sources: [] as any[]
});

function addSource(){
  const idx = editor.value.sources.length + 1;
  editor.value.sources.push({
    id: `src_${idx}`,
    type: 'radar',
    position: { lat: 0, lon: 0, alt_m: 0 },
    emission: { eirp_dBm: 90, center_freq_MHz: 3000, bandwidth_MHz: 10, polarization: 'H', duty_cycle: 1 },
    antenna: { pattern: { type: 'simplified_directional', hpbw_deg: 3, vpbw_deg: 3 }, pointing: { az_deg: 0, el_deg: 0 }, scan: { mode: 'none', rpm: 0, sector_deg: 90 } }
  });
}
function clearSources(){ editor.value.sources = []; }
function removeSource(i:number){ editor.value.sources.splice(i,1); }

function editorToComputeRequest(){
  const rect = editor.value.regionRect;
  const polygon = [
    { lat: rect.lat_max, lon: rect.lon_min },
    { lat: rect.lat_max, lon: rect.lon_max },
    { lat: rect.lat_min, lon: rect.lon_max },
    { lat: rect.lat_min, lon: rect.lon_min }
  ];
  const bands = editor.value.selectedBands.map((name:string)=>{
    const def = defaultBandDefs.find(d=>d.name===name);
    return { name, f_min_MHz: def?.f_min_MHz ?? 0, f_max_MHz: def?.f_max_MHz ?? 0, ref_bw_kHz: 1000 };
  });
  return {
    region: { crs: 'WGS84', polygon },
    grid: { ...editor.value.grid },
    influence_buffer_km: editor.value.influence_buffer_km,
    environment: editor.value.environment,
    bands,
    metric: editor.value.metric,
    combine_sources: editor.value.combine_sources,
    temporal_agg: editor.value.temporal_agg,
    limits: editor.value.limits,
    sources: editor.value.sources
  };
}

function downloadConfig(){
  const payload = editorToComputeRequest();
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'compute_request.json'; a.click();
  setTimeout(()=>URL.revokeObjectURL(url), 0);
}

async function runCompute(){
  lastComputeInfo.value = '提交计算中...';
  try{
    const res = await fetch(`${restBase.value.replace(/\/$/,'')}/compute`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(editorToComputeRequest())
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();
    lastComputeInfo.value = `计算已接受，返回频段: ${(data.bands||[]).join(', ')}`;
  }catch(err:any){
    lastComputeInfo.value = `计算失败: ${err?.message||String(err)}`;
  }
}

function createMap() {
  if (!mapEl.value) return;
  map = L.map(mapEl.value).setView([34.0, 118.5], 7);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);
}

function onTiffSelected(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async () => {
    if (!reader.result) return;
    const tiff = await fromArrayBuffer(reader.result as ArrayBuffer);
    const image = await tiff.getImage();
    const bbox = image.getBoundingBox();
    const width = image.getWidth();
    const height = image.getHeight();
    const rasters = await image.readRasters({ interleave: true, pool: undefined, width, height });
    const data = rasters as Float32Array; // 单波段
    tiffData = data; tiffWidth = width; tiffHeight = height; tiffBBox = [bbox[0], bbox[1], bbox[2], bbox[3]];

    const canvas = document.createElement('canvas');
    canvas.width = width; canvas.height = height;
    const ctx = canvas.getContext('2d')!;
    const img = ctx.createImageData(width, height);
    const toColor = getColorScale();
    for (let i = 0; i < data.length; i++) {
      const v = data[i];
      let a = 0;
      let r = 0, g = 0, b = 0;
      if (Number.isFinite(v)) {
        const t = Math.max(0, Math.min(1, (v - vmin.value) / Math.max(1e-6, (vmax.value - vmin.value))));
        const [rr, gg, bb] = toColor(t);
        r = rr; g = gg; b = bb; a = 255;
      }
      const j = i * 4;
      img.data[j] = r;
      img.data[j + 1] = g;
      img.data[j + 2] = b;
      img.data[j + 3] = a;
    }
    ctx.putImageData(img, 0, 0);

    const bounds = L.latLngBounds([bbox[1], bbox[0]], [bbox[3], bbox[2]]);

    if (rasterLayer && map) {
      try { map.removeLayer(rasterLayer); } catch {}
    }
    const dataUrl = canvas.toDataURL();
    rasterLayer = L.imageOverlay(dataUrl, bounds, { opacity: 0.85 });
    if (map) {
      rasterLayer.addTo(map);
      try { map.fitBounds(bounds); } catch {}
    }
  };
  reader.readAsArrayBuffer(file);
}

function onParquetSelected(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async () => {
    if (!reader.result) return;
    await ensureParquet();
    const bytes = new Uint8Array(reader.result as ArrayBuffer);
    const table = readParquet(bytes);
    const latCol = table.get('lat');
    const lonCol = table.get('lon');
    const rankCol = table.get('rank');
    const srcCol = table.get('source_id');
    const fracCol = table.get('fraction');
    topkRows.value = [];
    const length = latCol ? latCol.length : 0;
    for (let i = 0; i < length; i++) {
      const lat = latCol?.get(i);
      const lon = lonCol?.get(i);
      const rank = rankCol?.get(i);
      const source_id = srcCol?.get(i);
      const fraction = fracCol?.get(i);
      if (typeof lat !== 'number' || typeof lon !== 'number' || typeof rank !== 'number' || typeof fraction !== 'number') continue;
      topkRows.value.push({ __idx: i, lat, lon, rank, source_id: String(source_id), fraction });
    }
    // 在地图上标注 rank==0 部分点
    if (map) {
      const sample = topkRows.value.filter(r => r.rank === 0).slice(0, 2000);
      for (const r of sample) {
        L.circleMarker([r.lat, r.lon], { radius: 2, color: '#f44336', weight: 1 }).addTo(map).bindTooltip(r.source_id);
      }
    }
  };
  reader.readAsArrayBuffer(file);
}

// 不再从左侧上传 JSON，这里保留函数以兼容可能的引用（未使用）
function onConfigSelected(_e: Event) {}

let parquetReady = false;
async function ensureParquet() {
  if (!parquetReady) {
    await initParquet();
    parquetReady = true;
  }
}

function getColorScale(): (t:number)=>[number,number,number] {
  // 预设色表
  const schemes: Record<string, Array<[number,string]>> = {
    blue_to_red: [ [0,'#0000ff'],[0.2,'#00ffff'],[0.4,'#00ff00'],[0.6,'#ffff00'],[0.8,'#ff9900'],[1,'#ff0000'] ],
    green_to_red: [ [0,'#006400'],[0.2,'#008000'],[0.4,'#ffff00'],[0.6,'#ff9900'],[0.8,'#8b0000'],[1,'#ff0000'] ],
    purple_to_yellow: [ [0,'#800080'],[0.2,'#0000ff'],[0.4,'#00ffff'],[0.6,'#00ff00'],[0.8,'#ffff00'],[1,'#ffffff'] ],
    cool_to_warm: [ [0,'#00008b'],[0.2,'#0000ff'],[0.4,'#87cefa'],[0.6,'#90ee90'],[0.8,'#ff9900'],[1,'#ff0000'] ]
  };
  const stops = schemes[selectedScheme.value] ?? schemes.blue_to_red;
  const custom = [ [0, colorStart.value], [1, colorEnd.value] ] as Array<[number,string]>;
  const activeStops = [ ...stops, ...custom ]; // 末端仍按预设，允许覆盖端点
  const parsed = activeStops.map(([p,c]) => [p, hexOrRgbToTuple(c)] as [number,[number,number,number]]).sort((a,b)=>a[0]-b[0]);
  return (t:number) => {
    const x = Math.max(0, Math.min(1, t));
    let i = 0;
    while (i < parsed.length-1 && x > parsed[i+1][0]) i++;
    const [p0,c0] = parsed[i];
    const [p1,c1] = parsed[Math.min(i+1, parsed.length-1)];
    const u = p1===p0 ? 0 : (x - p0) / (p1 - p0);
    return [
      Math.round(c0[0] + (c1[0]-c0[0])*u),
      Math.round(c0[1] + (c1[1]-c0[1])*u),
      Math.round(c0[2] + (c1[2]-c0[2])*u)
    ];
  };
}

function hexOrRgbToTuple(c: string): [number,number,number] {
  if (c.startsWith('#')) {
    const s = c.replace('#','');
    const v = parseInt(s, 16);
    return [ (v>>16)&255, (v>>8)&255, v&255 ];
  }
  const m = c.match(/rgb\((\d+),(\d+),(\d+)\)/);
  if (m) return [parseInt(m[1],10), parseInt(m[2],10), parseInt(m[3],10)];
  return [0,0,0];
}

// 统计量
const stats = computed(() => {
  if (!tiffData) return null as any;
  const arr: number[] = [];
  for (let i=0;i<tiffData.length;i++){ const v=tiffData[i]; if (Number.isFinite(v)) arr.push(v); }
  if (!arr.length) return { count: 0 } as any;
  arr.sort((a,b)=>a-b);
  const count = arr.length;
  const min = arr[0];
  const max = arr[count-1];
  const mean = arr.reduce((s,v)=>s+v,0)/count;
  const variance = arr.reduce((s,v)=>s+(v-mean)*(v-mean),0)/count;
  const std = Math.sqrt(variance);
  const median = arr[Math.floor(count/2)];
  return { count, min, max, mean, std, median };
});

const percentiles = computed(()=>{
  if (!tiffData) return [] as Array<{q:number; v:number}>;
  const arr:number[]=[]; for (let i=0;i<tiffData.length;i++){ const v=tiffData[i]; if (Number.isFinite(v)) arr.push(v); }
  if (!arr.length) return [];
  arr.sort((a,b)=>a-b);
  const qs = [10,25,50,75,90,95,99];
  return qs.map(q=>({ q, v: arr[Math.min(arr.length-1, Math.floor((q/100)*arr.length))] }));
});

// Top-K 平均贡献按 source_id
const topkSummary = computed(()=>{
  if (!topkRows.value.length) return [] as Array<{id:string; fraction:number}>;
  const agg: Record<string,{s:number;c:number}> = {};
  for (const r of topkRows.value){
    if (!agg[r.source_id]) agg[r.source_id] = { s:0, c:0 };
    agg[r.source_id].s += r.fraction;
    agg[r.source_id].c += 1;
  }
  const out = Object.entries(agg).map(([id,{s,c}])=>({ id, fraction: s/Math.max(1,c) }));
  out.sort((a,b)=>b.fraction-a.fraction);
  return out;
});

// 波束示意（简化平面）
const palette = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf'];
const beamSources = computed(()=> (config.value?.sources || exampleConfig.value?.sources || []));
function regionCenter(){
  const poly = config.value?.region?.polygon || [];
  if (!poly.length) return { lat:0, lon:0 };
  let sl=0, so=0; for (const p of poly){ sl += Number(p.lat)||0; so += Number(p.lon)||0; }
  return { lat: sl/poly.length, lon: so/poly.length };
}
function relPos(s:any){
  const c = regionCenter();
  const lat = Number(s?.position?.lat)||0; const lon = Number(s?.position?.lon)||0;
  const dy = (lat - c.lat) * 111.0;
  const dx = (lon - c.lon) * 111.0 * Math.cos(c.lat*Math.PI/180);
  // 映射到 SVG 坐标（上为负y，所以取 -dy）
  return { x: dx, y: -dy };
}
function sectorPath(s:any){
  const az = Number(s?.antenna?.pointing?.az_deg)||0; // 北=0，东=90（与后端一致，转为数学习惯）
  const hpbw = Number(s?.antenna?.pattern?.hpbw_deg)||20;
  const eirp = Number(s?.emission?.eirp_dBm)||90;
  const length = Math.max(2, Math.min(20, (eirp-50)/50*20));
  const azMath = 90 - az; // 转为数学角
  const half = hpbw/2;
  const steps: Array<[number,number]> = [];
  const center = relPos(s);
  steps.push([center.x, center.y]);
  for (let a = azMath-half; a <= azMath+half; a += Math.max(2, hpbw/20)){
    const rad = a*Math.PI/180;
    const x = center.x + length*Math.cos(rad);
    const y = center.y + length*Math.sin(rad);
    steps.push([x,y]);
  }
  steps.push([center.x, center.y]);
  const d = steps.map((p,i)=> (i===0?`M ${p[0]} ${p[1]}`:`L ${p[0]} ${p[1]}`)).join(' ') + ' Z';
  return d;
}

onMounted(() => {
  createMap();
});

onBeforeUnmount(() => {
  if (map) {
    map.remove();
    map = null;
  }
});
</script>

<style scoped>
.map-page { display: flex; height: 100%; }
.sidebar { width: 300px; padding: 12px; border-right: 1px solid #eee; overflow: auto; }
.field { margin-bottom: 12px; display: flex; gap: 8px; align-items: center; }
.hint { color: #666; font-size: 12px; }
.ok { color: #0a7d16; font-size: 12px; }
.warn { color: #b3261e; font-size: 12px; }
.group { border: 1px solid #eee; padding: 8px; margin-bottom: 10px; background: #fafafa; }
.title { font-weight: 600; margin-bottom: 8px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.content { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.tabs { display: flex; gap: 8px; padding: 8px 12px; border-bottom: 1px solid #eee; }
.tabs button { padding: 6px 10px; background: #f5f5f5; border: 1px solid #ddd; cursor: pointer; }
.tabs button.active { background: #e8f4fd; border-color: #90caf9; }
.map-container { flex: 1; min-height: 0; }
.map { height: 100%; width: 100%; }
.panel { padding: 12px; overflow: auto; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; margin: 8px 0 16px; }
.metric { background: #f0f2f6; padding: 8px; border-left: 4px solid #1f77b4; }
.metric .k { font-size: 12px; color: #555; }
.metric .v { font-size: 18px; font-weight: 600; }
.pcts ul { padding-left: 18px; }
.bar-list { display: flex; flex-direction: column; gap: 6px; }
.bar-row { display: grid; grid-template-columns: 160px 1fr 70px; align-items: center; gap: 8px; }
.bar-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar { background: #eee; height: 10px; position: relative; }
.bar-fill { position: absolute; left: 0; top: 0; bottom: 0; background: #42b883; }
.table-wrap { margin-top: 12px; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #ddd; padding: 4px 6px; font-size: 12px; }
.cfg-block { margin-bottom: 12px; }
.beam-wrap { display:flex; flex-direction: column; align-items: center; gap: 6px; }
.beam { width: 360px; height: 360px; background: #fafafa; border: 1px solid #eee; }
.beam-legend { color:#666; font-size:12px; }
.rightbar { width: 320px; padding: 12px; border-left: 1px solid #eee; overflow: auto; }
.src-readonly { background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px; margin: 8px 0; }
.src-readonly summary { cursor: pointer; font-weight: 600; }
.ro-title { margin-top: 6px; font-weight: 600; color: #333; }
.ro-line { color: #333; margin: 4px 0; }
.two-col { display: grid; grid-template-columns: 1.5fr 1fr; gap: 12px; align-items: stretch; }
.beam-panel { display:flex; flex-direction: column; align-items: center; gap: 6px; }
.two-col .map-container { height: 560px; }
</style>



