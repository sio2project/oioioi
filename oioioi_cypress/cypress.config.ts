import { defineConfig } from 'cypress'

export default defineConfig({
  chromeWebSecurity: false,
  browser: 'electron',
  video: false,
  e2e: {},
})
