import{describe,expect,it}from'vitest';
import{ORDER_STATUS_LABELS,isPendingOrder,orderStatusLabel,paymentMethodLabel}from'./order-status';
describe('pedidos simplificados',()=>{
  it('solo expone los tres estados permitidos',()=>expect(Object.keys(ORDER_STATUS_LABELS)).toEqual(['pending','finalized','cancelled']));
  it('traduce estados al español',()=>{expect(orderStatusLabel('pending')).toBe('Pendiente');expect(orderStatusLabel('finalized')).toBe('Finalizado');expect(orderStatusLabel('cancelled')).toBe('Cancelado')});
  it('solo los pendientes muestran acciones',()=>{expect(isPendingOrder('pending')).toBe(true);expect(isPendingOrder('finalized')).toBe(false);expect(isPendingOrder('cancelled')).toBe(false)});
  it('traduce métodos de pago',()=>{expect(paymentMethodLabel('cash')).toBe('Efectivo');expect(paymentMethodLabel('yape')).toBe('Yape');expect(paymentMethodLabel('plin')).toBe('Plin');expect(paymentMethodLabel('transfer')).toBe('Transferencia');expect(paymentMethodLabel('other')).toBe('Otro')});
});
