import { defineConfig, devices } from '@playwright/test';

const artifactDir = process.env.E2E_ARTIFACTS_DIR ?? '../.e2e-artifacts';

export default defineConfig({
    testDir: './e2e',
    fullyParallel: false,
    forbidOnly: Boolean(process.env.CI),
    retries: process.env.CI ? 1 : 0,
    reporter: [
        ['list'],
        ['json', { outputFile: `${artifactDir}/playwright-summary.json` }],
        ['html', { outputFolder: `${artifactDir}/playwright-report`, open: 'never' }],
    ],
    outputDir: `${artifactDir}/test-results`,
    use: {
        baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:4173',
        trace: 'retain-on-failure',
        video: 'retain-on-failure',
    },
    projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
