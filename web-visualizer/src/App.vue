<template>
  <div class="layout">
    <header>
      <h1>EM 可视化（Vue3 独立版）</h1>
      <nav>
        <router-link to="/">首页</router-link>
        <span> | </span>
        <router-link to="/map">地图</router-link>
      </nav>
    </header>
    <main>
      <router-view />
    </main>
  </div>
  
</template>

<script setup lang="ts">
</script>

<style scoped>
.layout { display: flex; flex-direction: column; height: 100%; }
header { padding: 10px 16px; border-bottom: 1px solid #eee; }
main { flex: 1; }
nav a { margin-right: 8px; }
</style>



