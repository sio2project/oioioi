import { defineConfig } from 'cypress'

export default defineConfig({
  chromeWebSecurity: false,
  browser: 'electron',
  video: false,
  // Required even if empty: without it Cypress reports e2e as not configured.
  e2e: {},
})
