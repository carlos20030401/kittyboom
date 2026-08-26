import { describe, expect, it } from 'vitest';
import { calculateTotal } from './cart';
describe('carrito', () => {
  it('calcula cantidades y respeta el precio de oferta', () => {
    expect(calculateTotal([{ price: 40, quantity: 2 }, { price: 60, sale_price: 50, quantity: 1 }])).toBe(130);
  });
});
