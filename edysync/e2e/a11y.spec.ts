import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const SCREEN_URLS = [
  { path: '/auth/login', name: 'login' },
];

SCREEN_URLS.forEach(({ path, name }) => {
  test.describe(`a11y - ${name}`, () => {
    test(`scan ${name} for accessibility violations`, async ({ page }) => {
      await page.goto(path, { waitUntil: 'load', timeout: 20000 });
      await page.waitForTimeout(3000);

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
        .analyze();

      console.log(`[${name}] axe report:`);
      console.log(`  Violaciones: ${results.violations.length}`);
      console.log(`  Pasaron: ${results.passes.length}`);
      console.log(`  Inaplicables: ${results.inapplicable.length}`);

      if (results.violations.length > 0) {
        console.log(`\n  Detalle:`);
        results.violations.forEach(v => {
          console.log(`    ${v.impact?.toUpperCase()}: ${v.id}`);
          console.log(`      ${v.help}`);
          console.log(`      ${v.helpUrl}`);
          v.nodes.slice(0, 3).forEach(n => {
            console.log(`      → ${n.target.join(', ')}`);
          });
        });
      }

      const knownCriticalIds = ['button-name'];
      const unknownCriticals = results.violations.filter(
        v => v.impact === 'critical' && !knownCriticalIds.includes(v.id)
      );
      expect(unknownCriticals).toEqual([]);
    });
  });
});
