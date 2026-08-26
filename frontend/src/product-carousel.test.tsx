import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import ProductCarousel, { nextIndex, prepareImages, previousIndex, selectIndex, swipeIndex } from './product-carousel';

const one = [{ id: 1, url: '/one.jpg', is_primary: true, position: 0 }];
const many = [{ id: 1, url: '/one.jpg', position: 0 }, { id: 2, url: '/two.jpg', is_primary: true, position: 4 }, { id: 3, url: '/three.jpg', position: 2 }];
describe('ProductCarousel', () => {
  it('una sola imagen no muestra flechas', () => { const html = renderToStaticMarkup(<ProductCarousel images={one} productName="Anillo" />); expect(html).not.toContain('Imagen anterior'); expect(html).not.toContain('Imagen siguiente'); });
  it('varias imágenes muestran flechas y miniaturas', () => { const html = renderToStaticMarkup(<ProductCarousel images={many} productName="Anillo" />); expect(html).toContain('Imagen anterior'); expect(html).toContain('Imagen siguiente'); expect(html).toContain('Mostrar imagen 3'); });
  it('la flecha derecha avanza y vuelve al inicio', () => { expect(nextIndex(0, 3)).toBe(1); expect(nextIndex(2, 3)).toBe(0); });
  it('la flecha izquierda retrocede y vuelve al final', () => { expect(previousIndex(2, 3)).toBe(1); expect(previousIndex(0, 3)).toBe(2); });
  it('seleccionar una miniatura cambia al índice pedido', () => expect(selectIndex(2, 3)).toBe(2));
  it('pone la principal primero, conserva el orden y elimina duplicados', () => expect(prepareImages([...many, { id: 9, url: '/one.jpg' }]).map(image => image.url)).toEqual(['/two.jpg', '/one.jpg', '/three.jpg']));
  it('los gestos táctiles avanzan, retroceden y respetan el umbral', () => { expect(swipeIndex(120, 40, 0, 3)).toBe(1); expect(swipeIndex(40, 120, 0, 3)).toBe(2); expect(swipeIndex(100, 80, 1, 3)).toBe(1); });
});
