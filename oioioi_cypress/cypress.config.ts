import { defineConfig } from 'cypress'

export default defineConfig({
  chromeWebSecurity: false,
  browser: 'electron',
  video: false,
  e2e: {
    setupNodeEvents(on, config) {
      return require('./cypress/plugins/index.ts')(on, config)
    },
  },
})
