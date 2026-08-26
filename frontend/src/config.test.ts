import{describe,expect,it}from'vitest';import{API_URL,assetUrl}from'./config';
describe('configuración de despliegue',()=>{it('centraliza la API',()=>expect(API_URL).toMatch(/\/api\/v1$/));it('conserva URL HTTPS de Cloudinary',()=>expect(assetUrl('https://res.cloudinary.com/demo/image/upload/a.webp')).toBe('https://res.cloudinary.com/demo/image/upload/a.webp'))});
