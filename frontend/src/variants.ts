export type Variant={id:number;product_id:number;name:string;sku?:string|null;color?:string|null;size?:string|null;model?:string|null;finish?:string|null;price?:number|null;stock:number;min_stock:number;is_active:boolean;image_url?:string|null;position:number};
export type VariantProduct={price:number;sale_price?:number|null;stock:number;has_variants?:boolean;variants?:Variant[]};
export const activeVariants=(product:VariantProduct)=>(product.variants||[]).filter(v=>v.is_active).sort((a,b)=>a.position-b.position);
export const variantPrice=(product:VariantProduct,variant?:Variant|null)=>Number(variant?.price??product.sale_price??product.price);
export const availableStock=(product:VariantProduct,variant?:Variant|null)=>product.has_variants?(variant?.stock??0):product.stock;
export const catalogPrice=(product:VariantProduct)=>{const variants=activeVariants(product);const prices=variants.map(v=>variantPrice(product,v));return {price:prices.length?Math.min(...prices):variantPrice(product),from:new Set(prices).size>1,soldOut:product.has_variants?(!variants.length||variants.every(v=>v.stock<1)):product.stock<1}}
