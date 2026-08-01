<script setup lang="ts">
import { computed, ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";

import {
  API_BASE_OPTIONS,
  CUSTOM_API_BASE_OPTION,
  getBaseApi,
  useApiBase,
} from "../lib/apiBase";

const emit = defineEmits<{
  apiBaseChange: [baseApi: string];
}>();

const queryClient = useQueryClient();
const { setBaseApi, getApiBaseSelection } = useApiBase();

const selectedApiBase = ref(getApiBaseSelection());
const customApiBase = ref(getBaseApi());
const errorMessage = ref("");
const isCustom = computed(() => selectedApiBase.value === CUSTOM_API_BASE_OPTION);

function handleSelectChange() {
  errorMessage.value = "";

  if (isCustom.value) {
    customApiBase.value = getBaseApi();
  }
}

function applyApiBase() {
  const nextBaseApi = isCustom.value ? customApiBase.value : selectedApiBase.value;

  try {
    const baseApi = setBaseApi(nextBaseApi);

    selectedApiBase.value = getApiBaseSelection(baseApi);
    customApiBase.value = baseApi;
    errorMessage.value = "";
    emit("apiBaseChange", baseApi);
    void queryClient.invalidateQueries();
  } catch {
    errorMessage.value = "Введите корректный URL API.";
  }
}
</script>

<template>
  <form class="api-config-form ms-lg-auto mt-3 mt-lg-0" @submit.prevent="applyApiBase">
    <label class="visually-hidden" for="api-base-select">API backend</label>
    <div class="input-group input-group-sm api-config-controls">
      <span class="input-group-text">API</span>
      <select
        id="api-base-select"
        v-model="selectedApiBase"
        class="form-select api-config-select"
        name="api_base"
        aria-label="API backend"
        @change="handleSelectChange"
      >
        <option
          v-for="option in API_BASE_OPTIONS"
          :key="option.value"
          :value="option.value"
        >
          {{ option.label }}
        </option>
        <option :value="CUSTOM_API_BASE_OPTION">Другой</option>
      </select>
      <input
        v-if="isCustom"
        v-model="customApiBase"
        class="form-control api-config-custom-input"
        :class="{ 'is-invalid': errorMessage }"
        name="api_base_custom"
        type="url"
        placeholder="http://127.0.0.1:8000"
        autocomplete="off"
        required
      >
      <button class="btn btn-outline-primary" type="submit">OK</button>
    </div>
    <div v-if="errorMessage" class="api-config-error text-danger small">
      {{ errorMessage }}
    </div>
  </form>
</template>
