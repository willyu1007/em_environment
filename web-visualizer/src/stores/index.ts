import { defineStore } from 'pinia';

export const useAppStore = defineStore('app', {
  state: () => ({
    bandName: 'S'
  }),
  actions: {
    setBand(name: string) {
      this.bandName = name;
    }
  }
});



