import { describe, expect, it } from 'vitest';
import { buildWhatsAppUrl, normalizeWhatsAppNumber } from './whatsapp';

describe('WhatsApp', () => {
  it('agrega 51 a un número peruano de nueve dígitos', () => expect(normalizeWhatsAppNumber('987 654 321')).toBe('51987654321'));
  it('no duplica el prefijo 51', () => expect(normalizeWhatsAppNumber('+51 987-654-321')).toBe('51987654321'));
  it('codifica el mensaje', () => expect(buildWhatsAppUrl('987654321', 'Hola KittyBoom ✨\nTotal: S/ 10')).toBe(`https://wa.me/51987654321?text=${encodeURIComponent('Hola KittyBoom ✨\nTotal: S/ 10')}`));
  it('rechaza una configuración vacía', () => expect(() => buildWhatsAppUrl('', 'Hola')).toThrow('No hay un número'));
});

