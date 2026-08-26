export type PricedItem = { price: number; sale_price?: number; quantity: number };
export function calculateTotal(items: PricedItem[]) {
  return items.reduce((sum, item) => sum + (item.sale_price ?? item.price) * item.quantity, 0);
}

