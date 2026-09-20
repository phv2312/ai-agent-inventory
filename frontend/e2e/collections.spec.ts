import { expect, test } from '@playwright/test';

test('creates a collection through the live API', async ({ page }, testInfo) => {
    const collectionName = `E2E collection ${Date.now()}`;

    await page.goto('/documents');
    await expect(page.getByTestId('nav-documents')).toBeVisible();
    await expect(page.getByText('No collections yet')).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath('documents-empty.png'), fullPage: true });

    await page.getByRole('button', { name: 'Create collection' }).click();
    await page.getByTestId('collection-name-input').fill(collectionName);
    await page.getByTestId('collection-description-input').fill('Created by the live browser scenario');
    await page.getByTestId('create-collection-submit').click();

    await expect(page.getByTestId('collection-item')).toContainText(collectionName);
    await page.screenshot({ path: testInfo.outputPath('collection-created.png'), fullPage: true });
});
