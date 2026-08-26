import { describe, expect, it } from 'vitest';
import { imageFingerprint, validateImage } from './image-selection';
describe('selector de imágenes', () => {
  it('acepta JPEG, PNG y WebP', () => { expect(validateImage({ type: 'image/jpeg', size: 100 })).toBeNull(); expect(validateImage({ type: 'image/png', size: 100 })).toBeNull(); expect(validateImage({ type: 'image/webp', size: 100 })).toBeNull(); });
  it('rechaza formato inválido y archivos mayores a 5 MB', () => { expect(validateImage({ type: 'image/gif', size: 100 })).toMatch(/JPG/); expect(validateImage({ type: 'image/png', size: 5 * 1024 * 1024 + 1 })).toMatch(/5 MB/); });
  it('detecta duplicados por nombre, tamaño y modificación', () => expect(imageFingerprint({ name: 'joya.jpg', size: 10, lastModified: 5 })).toBe('joya.jpg:10:5'));
});
