<template>
  <div class="winner-marquee-container" v-if="processedWinnerList.length > 0">
    <div class="marquee-row" v-for="(row, rowIndex) in winnerRows" :key="rowIndex">
      <div :class="['marquee-content', `marquee-content-${rowIndex + 1}`]">
        <!-- Duplicate content for continuous scroll -->
        <template v-for="n in 5" :key="`duplicate-${rowIndex}-${n}`">
          <span v-for="(winner, index) in row" :key="`winner-${index}`" class="winner-item">
            恭喜 {{ winner.personName }} 获得 {{ winner.prizeName }}
          </span>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { usePersonConfig } from '@/store/personConfig';
import './style.scss';

const personStore = usePersonConfig();

// Process the raw winner list
const processedWinnerList = computed(() => {
  return personStore.getAllPersonList
    .filter(person => person.isWin)
    .flatMap(person => {
      if (Array.isArray(person.prizeName) && person.prizeName.length > 0) {
        return person.prizeName.map((prize, index) => ({
          personName: person.name,
          prizeName: prize,
          prizeTime: person.prizeTime?.[index]
        }));
      }
      return [];
    })
    .sort((a, b) => {
      const timeA = a.prizeTime ? new Date(a.prizeTime).getTime() : 0;
      const timeB = b.prizeTime ? new Date(b.prizeTime).getTime() : 0;
      return timeB - timeA;
    });
});

// Distribute winners into 3 rows
const winnerRows = computed(() => {
  const rows: Array<Array<any>> = [[], [], []];
  processedWinnerList.value.forEach((winner, index) => {
    rows[index % 3].push(winner);
  });
  return rows;
});
</script>
