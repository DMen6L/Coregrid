<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiRequestError, loginUser, registerUser } from "../lib/api";
import { saveAuthToken } from "../lib/authSession";

type AuthMode = "login" | "register";

const router = useRouter();
const route = useRoute();

const mode = ref<AuthMode>(getModeFromQuery(route.query.mode));
const loginEmail = ref("");
const loginPassword = ref("");
const registerName = ref("");
const registerEmail = ref("");
const registerPassword = ref("");
const isSubmitting = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

const submitLabel = computed(() =>
  mode.value === "login" ? "Войти" : "Создать аккаунт",
);

function setMode(nextMode: AuthMode) {
  mode.value = nextMode;
  errorMessage.value = "";
  successMessage.value = "";
  void router.replace({
    path: "/auth",
    query: nextMode === "register" ? { mode: "register" } : { mode: "login" },
  });
}

function getModeFromQuery(value: unknown): AuthMode {
  if (Array.isArray(value)) {
    return value[0] === "register" ? "register" : "login";
  }

  return value === "register" ? "register" : "login";
}

watch(
  () => route.query.mode,
  (nextMode) => {
    mode.value = getModeFromQuery(nextMode);
    errorMessage.value = "";
    successMessage.value = "";
  },
);

async function submitAuthForm() {
  errorMessage.value = "";
  successMessage.value = "";
  isSubmitting.value = true;

  try {
    if (mode.value === "login") {
      const token = await loginUser({
        email: loginEmail.value,
        password: loginPassword.value,
      });

      saveAuthToken(token);
      await router.push("/dashboard");
      return;
    }

    await registerUser({
      name: registerName.value,
      email: registerEmail.value,
      password: registerPassword.value,
    });

    loginEmail.value = registerEmail.value;
    loginPassword.value = "";
    registerPassword.value = "";
    setMode("login");
    successMessage.value = "Аккаунт создан. Войдите с новым паролем.";
  } catch (error) {
    errorMessage.value = formatAuthError(error);
  } finally {
    isSubmitting.value = false;
  }
}

function formatAuthError(error: unknown) {
  if (!(error instanceof ApiRequestError)) {
    return "Не удалось выполнить запрос.";
  }

  const detail = getErrorDetail(error.data);
  if (detail) {
    return detail;
  }

  if (error.status === 401) {
    return "Почта или пароль указаны неверно.";
  }

  if (error.status === 409) {
    return "Пользователь с такой почтой уже существует.";
  }

  if (error.status === 422) {
    return "Проверьте заполненные поля.";
  }

  return "Не удалось выполнить запрос.";
}

function getErrorDetail(data: unknown) {
  if (!data || typeof data !== "object" || !("detail" in data)) {
    return "";
  }

  const detail = (data as { detail?: unknown }).detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return "";
      })
      .filter(Boolean);

    return messages.join(" ");
  }

  return "";
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-panel">
      <div class="auth-mode-tabs" role="tablist" aria-label="Авторизация">
        <button
          class="btn"
          :class="mode === 'login' ? 'btn-primary' : 'btn-outline-primary'"
          type="button"
          role="tab"
          :aria-selected="mode === 'login'"
          @click="setMode('login')"
        >
          Войти
        </button>
        <button
          class="btn"
          :class="mode === 'register' ? 'btn-primary' : 'btn-outline-primary'"
          type="button"
          role="tab"
          :aria-selected="mode === 'register'"
          @click="setMode('register')"
        >
          Регистрация
        </button>
      </div>

      <form class="auth-form" @submit.prevent="submitAuthForm">
        <div v-if="mode === 'register'" class="mb-3">
          <label class="form-label" for="register-name">Имя</label>
          <input
            id="register-name"
            v-model.trim="registerName"
            class="form-control"
            name="name"
            type="text"
            autocomplete="name"
            maxlength="255"
            required
          >
        </div>

        <div class="mb-3">
          <label class="form-label" :for="mode === 'login' ? 'login-email' : 'register-email'">
            Почта
          </label>
          <input
            v-if="mode === 'login'"
            id="login-email"
            v-model.trim="loginEmail"
            class="form-control"
            name="email"
            type="email"
            autocomplete="email"
            maxlength="254"
            required
          >
          <input
            v-else
            id="register-email"
            v-model.trim="registerEmail"
            class="form-control"
            name="email"
            type="email"
            autocomplete="email"
            maxlength="254"
            required
          >
        </div>

        <div class="mb-3">
          <label
            class="form-label"
            :for="mode === 'login' ? 'login-password' : 'register-password'"
          >
            Пароль
          </label>
          <input
            v-if="mode === 'login'"
            id="login-password"
            v-model="loginPassword"
            class="form-control"
            name="password"
            type="password"
            autocomplete="current-password"
            required
          >
          <input
            v-else
            id="register-password"
            v-model="registerPassword"
            class="form-control"
            name="password"
            type="password"
            autocomplete="new-password"
            minlength="12"
            maxlength="128"
            required
          >
        </div>

        <div v-if="errorMessage" class="alert alert-danger" role="alert">
          {{ errorMessage }}
        </div>

        <div v-if="successMessage" class="alert alert-success" role="status">
          {{ successMessage }}
        </div>

        <button class="btn btn-primary w-100" type="submit" :disabled="isSubmitting">
          <span
            v-if="isSubmitting"
            class="spinner-border spinner-border-sm me-2"
            aria-hidden="true"
          ></span>
          {{ isSubmitting ? "Отправка..." : submitLabel }}
        </button>
      </form>
    </div>
  </section>
</template>
