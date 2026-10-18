import { describe, expect, it } from 'vitest';
import { asLink, levelOf, ratingWord } from './words';

describe('levelOf', () => {
  it('maps every stored weight to the nearest level, rounding ties up', () => {
    expect([0, 1, 2, 3, 4, 5].map(levelOf)).toEqual([0, 1, 3, 3, 5, 5]);
  });
  it('treats a missing weight as Important', () => {
    expect(levelOf(undefined)).toBe(3);
  });
});

describe('ratingWord', () => {
  it('names each band', () => {
    expect([0, 1.5, 2.5, 3, 4.5, 5].map(ratingWord)).toEqual(['Bad', 'Poor', 'OK', 'Good', 'Great', 'Perfect']);
  });
});

describe('asLink', () => {
  it('only treats a bare URL as a link', () => {
    expect(asLink(' https://example.com/a ')).toBe('https://example.com/a');
    expect(asLink('see https://example.com')).toBeNull();
    expect(asLink('javascript:alert(1)')).toBeNull();
  });
});
