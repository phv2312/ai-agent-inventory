import { chromium } from 'playwright';

const frontendUrl = requiredEnv('E2E_FRONTEND_URL');
const apiUrl = requiredEnv('E2E_API_URL');
const pdfPath = requiredEnv('E2E_PDF_PATH');
const collectionName = 'E2E UI GraphRAG';
const message = 'Compare GraphRAG and traditional RAG using the uploaded paper.';

function requiredEnv(name) {
    const value = process.env[name];
    if (!value) {
        throw new Error(`Missing required environment variable: ${name}`);
    }
    return value;
}

async function waitForIndexedReference(page) {
    await expectEventually(async () => {
        const response = await page.request.get(`${apiUrl}/api/v1/collections/`);
        const payload = await response.json();
        const collection = payload.items.find((item) => item.name === collectionName);
        if (!collection) return false;
        const references = await page.request.get(
            `${apiUrl}/api/v1/collections/${collection.id}/references`,
        );
        const items = await references.json();
        return items.some((item) => item.doc_name === 'GraphRAG.pdf' && item.status === 'completed');
    }, 180_000, 'Uploaded PDF did not finish indexing');
}

async function expectEventually(check, timeoutMs, messageText) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        if (await check()) return;
        await new Promise((resolve) => setTimeout(resolve, 1_000));
    }
    throw new Error(messageText);
}

const browser = await chromium.launch({ headless: true });
try {
    const page = await browser.newPage();
    await page.goto(`${frontendUrl}/documents`, { waitUntil: 'networkidle' });

    await page.getByRole('button', { name: 'Create collection' }).click();
    await page.locator('#collection-name').fill(collectionName);
    await page.getByRole('button', { name: 'Create Collection', exact: true }).click();
    await page.getByText(collectionName, { exact: true }).waitFor();

    await page.getByRole('button', { name: 'Upload Files' }).click();
    await page.locator('input[type="file"]').setInputFiles(pdfPath);
    const uploadResponse = page.waitForResponse(
        (response) => response.url().includes('/api/v1/references/')
            && response.request().method() === 'POST'
            && response.status() === 202,
    );
    await page.getByRole('button', { name: 'Upload 1 File' }).click();
    await uploadResponse;
    await waitForIndexedReference(page);

    await page.getByRole('link', { name: 'Chat' }).click();
    await page.getByRole('button', { name: 'New conversation' }).click();
    await page.getByTitle('Manage collections for this conversation').click();
    await page.getByText(collectionName, { exact: true }).click();
    await page.getByRole('button', { name: 'Update Collections' }).click();
    await page.locator('textarea').fill(message);
    await page.getByRole('button', { name: 'Send message' }).click();
    const stopButton = page.getByRole('button', { name: 'Stop' });
    await stopButton.waitFor({ state: 'visible', timeout: 20_000 });
    await stopButton.waitFor({ state: 'hidden', timeout: 180_000 });
    await page.locator('.prose').last().waitFor({ timeout: 20_000 });
} finally {
    await browser.close();
}
