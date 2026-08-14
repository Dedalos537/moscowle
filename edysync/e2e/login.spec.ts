import { test, expect } from '@playwright/test';

const LOGIN_URL = '/auth/login';

test.describe('Login Page - UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(LOGIN_URL, { waitUntil: 'load', timeout: 20000 });
    await page.waitForTimeout(3000);
  });

  test('page loads with correct title', async ({ page }) => {
    await expect(page).toHaveTitle(/EdySync|Moscowle|Login|Centro Juan Pablo II/i);
  });

  test('login form has email and password fields', async ({ page }) => {
    const emailInput = page.locator('#email');
    const passwordInput = page.locator('#password');
    await expect(emailInput).toBeVisible({ timeout: 10000 });
    await expect(passwordInput).toBeVisible({ timeout: 5000 });
  });

  test('login form has a submit button', async ({ page }) => {
    const submitBtn = page.locator('#login-btn');
    await expect(submitBtn).toBeVisible({ timeout: 10000 });
  });

  test('submit button is disabled when form is empty', async ({ page }) => {
    const submitBtn = page.locator('#login-btn');
    await expect(submitBtn).toBeVisible({ timeout: 10000 });
    await expect(submitBtn).toBeDisabled();
  });

  test('brand heading is present', async ({ page }) => {
    const brandHeading = page.locator('h2, h3').filter({ hasText: /Centro de Terapias|Juan Pablo II/i }).first();
    await expect(brandHeading).toBeAttached();
  });

  test('password field masks input', async ({ page }) => {
    const passwordInput = page.locator('#password');
    await expect(passwordInput).toHaveAttribute('type', /password/i);
  });
});
