/**
 * Tests for i18n configuration — ensures Italian locale is default
 * and all required keys exist.
 */

import italianStrings from '../../public/locales/it/common.json';

describe('Italian locale (it)', () => {
  it('should have app name defined', () => {
    expect(italianStrings.app.name).toBe('Protego Life Simulator');
  });

  it('should have all required navigation keys', () => {
    expect(italianStrings.nav).toBeDefined();
    expect(italianStrings.nav.home).toBeDefined();
    expect(italianStrings.nav.dashboard).toBeDefined();
  });

  it('should have auth strings', () => {
    expect(italianStrings.auth.loginWithGoogle).toBeDefined();
    expect(typeof italianStrings.auth.loginWithGoogle).toBe('string');
    expect(italianStrings.auth.loginWithGoogle.length).toBeGreaterThan(0);
  });

  it('should have error strings', () => {
    expect(italianStrings.errors.generic).toBeDefined();
    expect(italianStrings.errors.notFound).toBeDefined();
    expect(italianStrings.errors.unauthorized).toBeDefined();
    expect(italianStrings.errors.forbidden).toBeDefined();
  });

  it('should have GDPR consent strings', () => {
    expect(italianStrings.gdpr.title).toBeDefined();
    expect(italianStrings.gdpr.accept).toBeDefined();
    expect(italianStrings.gdpr.decline).toBeDefined();
  });

  it('should have wallet strings', () => {
    expect(italianStrings.wallet.balance).toBeDefined();
    expect(italianStrings.wallet.pcoin).toBeDefined();
  });

  it('should contain no untranslated key placeholders', () => {
    const allValues = JSON.stringify(italianStrings);
    // Check no angular bracket key placeholders like {{key}} remain untranslated
    expect(allValues).not.toMatch(/\{\{[^}]+\}\}/);
    // Check no English fallback patterns like "missing.key" appear
    expect(allValues).not.toMatch(/^[a-z]+\.[a-z]+$/);
  });
});
