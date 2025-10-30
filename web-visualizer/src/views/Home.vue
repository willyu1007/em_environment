<template>
  <section class="home">
    <h2>欢迎</h2>
    <p>本前端基于 Vue3 + Vite，独立于现有 Streamlit 前端。</p>
    <ol>
      <li>进入“地图”页</li>
      <li>在侧边栏依次加载 GeoTIFF（场强）与 Parquet（Top-K），可选加载配置 JSON</li>
      <li>使用上方标签切换：地图可视化 / 统计图表 / Top-K 分析 / 配置信息</li>
    </ol>
  </section>
</template>

<script setup lang="ts">
</script>

<style scoped>
.home { padding: 16px; }
</style>



