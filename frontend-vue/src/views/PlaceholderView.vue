<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>

<template>
  <section class="container-fluid p-4">
    <div class="placeholder-panel">
      <h1 class="fs-4 mb-2">{{ title }}</h1>
      <p class="text-secondary mb-0">Этот раздел будет перенесен в Vue позже.</p>
    </div>
  </section>
</template>
