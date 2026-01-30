<template>
  <div class="page-container">
    <slot />
  </div>
</template>

<style scoped>
.page-container {
  width: 100%;
  max-width: 1600px;
  margin-left: auto;
  margin-right: auto;

  padding: 1.5rem 1rem; /* default */

  /* sm */
  @media (min-width: 640px) {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }

  /* lg */
  @media (min-width: 1024px) {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}
</style>
