import {describe,expect,it} from 'vitest';
import {addOrMergeLine,movementQuery,type CashFilters} from './cash-admin';
const filters:CashFilters={date_from:'2026-08-01',date_to:'2026-08-25',direction:'expense',movement_type:'business_expense',payment_method:'yape',user_id:'7',order_number:'KB-100',search:'publicidad'};
describe('Caja administrativa',()=>{
 it('combina productos repetidos sin crear líneas duplicadas',()=>{const once=addOrMergeLine([],4);const twice=addOrMergeLine(once,4);expect(twice).toHaveLength(1);expect(twice[0].quantity).toBe(2)});
 it('conserva todos los filtros al cambiar de página',()=>{const query=movementQuery(filters,20);const params=new URLSearchParams(query.split('?')[1]);expect(params.get('skip')).toBe('20');expect(params.get('direction')).toBe('expense');expect(params.get('movement_type')).toBe('business_expense');expect(params.get('payment_method')).toBe('yape');expect(params.get('user_id')).toBe('7');expect(params.get('order_number')).toBe('KB-100');expect(params.get('search')).toBe('publicidad');expect(params.get('date_from')).toBe('2026-08-01T00:00:00');expect(params.get('date_to')).toBe('2026-08-25T23:59:59')});
 it('omite filtros vacíos',()=>{const empty=Object.fromEntries(Object.keys(filters).map(key=>[key,''])) as CashFilters;expect(movementQuery(empty,0)).toBe('/admin/cash/movements?skip=0&limit=20')});
});
