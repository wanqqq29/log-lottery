<template>
  <div class="card bg-base-100 shadow-xl w-full">
    <div class="card-body">
      <h2 class="card-title">
        {{ t("config.marqueeSetting") }}
      </h2>
      <div class="form-control">
        <label class="label">
          <span class="label-text">{{ t("config.marqueeBgColor") }}</span>
        </label>
        <input
          type="color"
          class="input input-bordered"
          :value="marqueeBgColor"
          @input="$emit('update:marqueeBgColor', ($event.target as HTMLInputElement).value)"
        >
      </div>
      <div class="form-control">
        <label class="label">
          <span class="label-text">{{ t("config.marqueeFontColor") }}</span>
        </label>
        <input
          type="color"
          class="input input-bordered"
          :value="marqueeFontColor"
          @input="$emit('update:marqueeFontColor', ($event.target as HTMLInputElement).value)"
        >
      </div>
      <div class="form-control">
        <label class="label">
          <span class="label-text">{{ t("config.marqueeFontSize") }}</span>
        </label>
        <input
          type="number"
          class="input input-bordered"
          :value="marqueeFontSize"
          @input="$emit('update:marqueeFontSize', Number(($event.target as HTMLInputElement).value))"
        >
      </div>
      <div class="form-control">
        <label class="label">
          <span class="label-text">{{ t("config.marqueeRowHeight") }}</span>
        </label>
        <input
          type="number"
          class="input input-bordered"
          :value="marqueeRowHeight"
          @input="$emit('update:marqueeRowHeight', Number(($event.target as HTMLInputElement).value))"
        >
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

defineProps<{
  marqueeBgColor: string;
  marqueeFontColor: string;
  marqueeFontSize: number;
  marqueeRowHeight: number;
}>();

defineEmits<{
  (e: 'update:marqueeBgColor', value: string): void;
  (e: 'update:marqueeFontColor', value: string): void;
  (e: 'update:marqueeFontSize', value: number): void;
  (e: 'update:marqueeRowHeight', value: number): void;
}>();
</script>
