<script setup lang="ts">
const sectionLinks = [
  { label: "Дэшборд", path: "/dashboard", note: "Сводка по продажам и остаткам" },
  { label: "Товары", path: "/products", note: "Список товаров и поставщиков" },
  { label: "Компании", path: "/companies", note: "Производители и бренды" },
  { label: "Поставщики", path: "/suppliers", note: "Контакты и связи с товарами" },
  { label: "Пополнения", path: "/restocks", note: "Поступления на склад" },
  { label: "Продажи", path: "/sales", note: "Списания и выручка" },
];
</script>

<template>
  <section class="home-page">
    <div class="home-main">
      <div class="home-intro">
        <p class="home-kicker">Coregrid</p>
        <h1>Учет товаров, поставщиков и складских движений</h1>
        <p class="home-summary">
          Публичная стартовая страница без данных бизнеса. Рабочие разделы будут
          привязаны к аккаунту и рабочему пространству.
        </p>
        <div class="home-actions">
          <RouterLink
            class="btn btn-outline-primary"
            :to="{ path: '/auth', query: { mode: 'login' } }"
          >
            Войти
          </RouterLink>
          <RouterLink
            class="btn btn-primary"
            :to="{ path: '/auth', query: { mode: 'register' } }"
          >
            Регистрация
          </RouterLink>
        </div>
      </div>

      <div class="home-access-panel">
        <h2>Текущий доступ</h2>
        <dl class="home-access-list">
          <div>
            <dt>Сессия</dt>
            <dd>Войдите или создайте аккаунт</dd>
          </div>
          <div>
            <dt>Рабочее пространство</dt>
            <dd>Доступно после входа</dd>
          </div>
          <div>
            <dt>Данные бизнеса</dt>
            <dd>Не отображаются на этой странице</dd>
          </div>
        </dl>
      </div>
    </div>

    <div class="home-sections">
      <RouterLink
        v-for="link in sectionLinks"
        :key="link.path"
        class="home-section-link"
        :to="link.path"
      >
        <span>{{ link.label }}</span>
        <small>{{ link.note }}</small>
      </RouterLink>
    </div>
  </section>
</template>
