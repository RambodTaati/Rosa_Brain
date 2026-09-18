<script setup lang="ts">
</script>

<template>
  <div class="layout">
    <nav class="topnav" aria-label="منوی اصلی">
      <div class="brand">Rosa_Brain</div>
      <RouterLink to="/">گفتگو و پروژه</RouterLink>
      <RouterLink to="/training">آموزش</RouterLink>
      <RouterLink to="/skills">مهارت‌ها (Skills)</RouterLink>
      <RouterLink to="/mcp">MCP</RouterLink>
    </nav>
    <main class="page">
      <RouterView />
    </main>
  </div>
</template>
