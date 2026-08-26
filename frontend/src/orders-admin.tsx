import React,{useCallback,useEffect,useMemo,useState}from'react';

import{Minus,Plus,Search,ShoppingCart,Trash2,X}from'lucide-react';

import{isPendingOrder,orderStatusLabel,paymentMethodLabel,paymentStatusLabel,salesChannelLabel}from'./order-status';
import{API_ORIGIN,API_URL,assetUrl}from'./config';

type Row=Record<string,any>;
 type Api=(path:string,options?:RequestInit)=>Promise<any>;
 const field='w-full rounded-xl border border-black/10 px-3 py-2.5 outline-none focus:border-[#d9909f]';

const API=API_URL;const BACKEND=API_ORIGIN;
const historyLabel=(action:string)=>({create_manual_sale:'Venta manual creada',order_finalized:'Pedido finalizado',order_cancelled:'Pedido cancelado',payment_paid:'Pago marcado como pagado',payment_pending:'Pago marcado como pendiente'}[action]??'Pedido actualizado');

function Overlay({title,close,children}:{title:string;
close:()=>void;
children:React.ReactNode}){return <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-3">
<div className="max-h-[95vh] w-full max-w-5xl overflow-auto rounded-3xl bg-[#fffaf7] p-5 md:p-7">
<div className="flex justify-between">
<h2 className="serif text-3xl">{title}</h2>
<button onClick={close}>
<X/>
</button>
</div>{children}</div>
</div>}
export default function OrdersAdmin({request}:{request:Api}){const[rows,setRows]=useState<Row[]>([]),[detail,setDetail]=useState<Row|null>(null),[manual,setManual]=useState(false),[filters,setFilters]=useState<Row>({}),[loading,setLoading]=useState(false),[error,setError]=useState('');
const load=useCallback(async(f=filters)=>{setLoading(true);
const q=new URLSearchParams(Object.entries(f).filter(([,v])=>v).map(([k,v])=>[k,String(v)]));
try{setRows(await request(`/admin/orders?${q}`))}finally{setLoading(false)}},[request,filters]);
useEffect(()=>{void load()},[]);
const open=async(id:number)=>setDetail(await request(`/admin/orders/${id}`));
const change=async(id:number,status:'finalized'|'cancelled')=>{const msg=status==='finalized'?'¿Finalizar este pedido? Se descontará el stock de los productos.':'¿Cancelar este pedido? El stock no será modificado.';
if(!confirm(msg))return;
try{await request(`/admin/orders/${id}/status?new_status=${status}`,{method:'PATCH'});
await load();
await open(id)}catch(e){setError((e as Error).message)}};
const payment=async(id:number,status:string)=>{await request(`/admin/orders/${id}/payment?payment_status=${status}`,{method:'PATCH'});
await open(id);
await load()};
return <section>
<div className="mb-6 flex flex-wrap items-center justify-between gap-3">
<div>
<h2 className="serif text-3xl">Pedidos y ventas</h2>
<p className="text-sm text-gray-500">Consulta pedidos y registra ventas de cualquier canal.</p>
</div>
<button onClick={()=>setManual(true)} className="rounded-full bg-[#231f20] px-5 py-3 text-white">Nueva venta</button>
</div>
<Filters value={filters} setValue={setFilters} apply={()=>load(filters)} clear={()=>{const empty={};
setFilters(empty);
void load(empty)}}/>{error&&<p className="my-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="mt-5 overflow-x-auto rounded-2xl bg-white soft-shadow">
<table className="w-full text-left text-sm">
<thead>
<tr className="border-b text-gray-500">
<th className="p-4">Pedido</th>
<th>Fecha</th>
<th>Total</th>
<th>Pago</th>
<th>Canal</th>
<th>Estado</th>
<th>
</th>
</tr>
</thead>
<tbody>{rows.map(order=>
<tr key={order.id} className="border-b last:border-0">
<td className="p-4">
<button onClick={()=>open(order.id)} className="font-semibold underline">{order.number}</button>
</td>
<td>{new Date(order.created_at).toLocaleString('es-PE')}</td>
<td>S/ {Number(order.total).toFixed(2)}</td>
<td>{paymentStatusLabel(order.payment_status)}</td>
<td>{salesChannelLabel(order.sales_channel)}</td>
<td>{orderStatusLabel(order.status)}</td>
<td>
<button onClick={()=>open(order.id)} className="underline">Ver detalle</button>
</td>
</tr>)}</tbody>
</table>{loading&&<p className="p-8 text-center text-gray-500">Cargando pedidos…</p>}</div>{detail&&<OrderDetail order={detail} close={()=>setDetail(null)} change={change} payment={payment}/>} {manual&&<ManualSale request={request} close={()=>setManual(false)} created={async id=>{setManual(false);
await load();
await open(id)}}/>}</section>}
function Filters({value,setValue,apply,clear}:{value:Row;
setValue:(v:Row)=>void;
apply:()=>void;
clear:()=>void}){const update=(k:string,v:string)=>setValue({...value,[k]:v});
return <div className="grid gap-3 rounded-2xl bg-white p-4 soft-shadow sm:grid-cols-2 lg:grid-cols-4">
<input className={field} placeholder="Número de pedido" value={value.number||''} onChange={e=>update('number',e.target.value)}/>
<input className={field} placeholder="Cliente o teléfono" value={value.customer||''} onChange={e=>update('customer',e.target.value)}/>
<select className={field} value={value.status_filter||''} onChange={e=>update('status_filter',e.target.value)}>
<option value="">Todos los estados</option>
<option value="pending">Pendiente</option>
<option value="finalized">Finalizado</option>
<option value="cancelled">Cancelado</option>
</select>
<select className={field} value={value.payment_status||''} onChange={e=>update('payment_status',e.target.value)}>
<option value="">Todos los pagos</option>
<option value="pending">Pago pendiente</option>
<option value="paid">Pagado</option>
</select>
<select className={field} value={value.payment_method||''} onChange={e=>update('payment_method',e.target.value)}>
<option value="">Método de pago</option>{['cash','yape','plin','transfer','other'].map(x=>
<option value={x}>{paymentMethodLabel(x)}</option>)}</select>
<select className={field} value={value.sales_channel||''} onChange={e=>update('sales_channel',e.target.value)}>
<option value="">Canal de venta</option>{['web','whatsapp','instagram','in_store','other'].map(x=>
<option value={x}>{salesChannelLabel(x)}</option>)}</select>
<input className={field} type="datetime-local" value={value.date_from||''} onChange={e=>update('date_from',e.target.value)}/>
<input className={field} type="datetime-local" value={value.date_to||''} onChange={e=>update('date_to',e.target.value)}/>
<div className="flex gap-2 lg:col-span-4">
<button onClick={apply} className="rounded-full bg-[#231f20] px-5 py-2 text-white">Aplicar filtros</button>
<button onClick={clear} className="rounded-full border px-5 py-2">Limpiar filtros</button>
</div>
</div>}
function OrderDetail({order,close,change,payment}:{order:Row;
close:()=>void;
change:(id:number,s:'finalized'|'cancelled')=>void;
payment:(id:number,s:string)=>void}){return <Overlay title={`Pedido ${order.number}`} close={close}>
<div className="mt-6 grid gap-5 md:grid-cols-3">
<Info label="Fecha" value={new Date(order.created_at).toLocaleString('es-PE')}/>
<Info label="Estado" value={orderStatusLabel(order.status)}/>
<label className="text-sm text-gray-500">Estado del pago<select className={`${field} mt-1 text-black`} value={order.payment_status} onChange={e=>payment(order.id,e.target.value)}>
<option value="pending">Pendiente</option>
<option value="paid">Pagado</option>
</select>
</label>
<Info label="Método de pago" value={paymentMethodLabel(order.payment_method)}/>
<Info label="Canal" value={salesChannelLabel(order.sales_channel)}/>
<Info label="Cliente" value={`${order.customer.name} · ${order.customer.phone||'Sin teléfono'}`}/>
<Info label="Entrega" value={order.address||'Sin dirección'}/>
<Info label="Observaciones" value={order.notes||'Sin observaciones'}/>{order.closed_by&&<Info label="Cerrado por" value={order.closed_by}/>}</div>
<div className="mt-7 overflow-x-auto rounded-2xl bg-white">
<table className="w-full text-left text-sm">
<thead>
<tr className="border-b">
<th className="p-3">Producto</th>
<th>SKU</th>
<th>Cantidad</th>
<th>Precio histórico</th>
<th>Subtotal</th>
</tr>
</thead>
<tbody>{order.items.map((item:Row)=>
<tr className="border-b last:border-0">
<td className="flex items-center gap-3 p-3">{item.image_url?<img src={assetUrl(item.image_url)||''} className="h-12 w-12 rounded-lg object-contain"/>:<span className="grid h-12 w-12 place-items-center rounded-lg bg-[#f5e9de]">✦</span>} {item.name}{item.variant_name?` — ${item.variant_name}`:''}</td>
<td>{item.sku}</td>
<td>{item.quantity}</td>
<td>S/ {Number(item.unit_price).toFixed(2)}</td>
<td>S/ {Number(item.subtotal).toFixed(2)}</td>
</tr>)}</tbody>
</table>
</div>
<div className="mt-5 text-right text-2xl font-semibold">Total: S/ {Number(order.total).toFixed(2)}</div>
<div className="mt-7">
<h3 className="font-semibold">Historial</h3>{order.history.length?order.history.map((h:Row)=>
<p className="mt-2 text-sm text-gray-600">{new Date(h.created_at).toLocaleString('es-PE')} · {historyLabel(h.action)} · {h.user||'Sistema'}</p>):<p className="mt-2 text-sm text-gray-500">Sin cambios registrados.</p>}</div>{isPendingOrder(order.status)&&<div className="mt-7 flex gap-3">
<button onClick={()=>change(order.id,'finalized')} className="rounded-full bg-green-600 px-5 py-3 text-white">Finalizar pedido</button>
<button onClick={()=>change(order.id,'cancelled')} className="rounded-full bg-gray-200 px-5 py-3">Cancelar pedido</button>
</div>}</Overlay>}
function Info({label,value}:{label:string;
value:string}){return <div>
<p className="text-sm text-gray-500">{label}</p>
<p className="mt-1 font-medium">{value}</p>
</div>}
function ManualSale({request,close,created}:{request:Api;
close:()=>void;
created:(id:number)=>void}){const[products,setProducts]=useState<Row[]>([]),[customers,setCustomers]=useState<Row[]>([]),[cart,setCart]=useState<Row[]>([]),[search,setSearch]=useState(''),[customerSearch,setCustomerSearch]=useState(''),[customerId,setCustomerId]=useState(''),[occasional,setOccasional]=useState(true),[quickName,setQuickName]=useState(''),[quickPhone,setQuickPhone]=useState(''),[idempotencyKey]=useState(()=>crypto.randomUUID()),[saving,setSaving]=useState(false),[error,setError]=useState('');
useEffect(()=>{void Promise.all([request('/admin/products'),request('/admin/customers')]).then(([p,c])=>{setProducts(p.filter((x:Row)=>x.is_active));
setCustomers(c)})},[]);
const createQuickCustomer=async()=>{if(!quickName.trim()||!quickPhone.trim()){setError('Ingresa nombre y teléfono para crear la clienta.');return}const customer=await request('/admin/customers',{method:'POST',body:JSON.stringify({name:quickName,phone:quickPhone,email:null,address:null,instagram:null,notes:null})});setCustomers(items=>[...items,customer]);setCustomerId(String(customer.id));setQuickName('');setQuickPhone('');setError('')};
const visible=products.filter(p=>(p.name+' '+p.sku).toLowerCase().includes(search.toLowerCase()));
const lineKey=(x:Row)=>`${x.id}:${x.variant?.id||0}`;const linePrice=(x:Row)=>Number(x.variant?.price??x.sale_price??x.price);const lineStock=(x:Row)=>Number(x.variant?.stock??x.stock);const total=cart.reduce((s,x)=>s+linePrice(x)*x.quantity,0);
const add=(p:Row,variant:Row|null=null)=>{if(p.has_variants&&!variant){setError(`Selecciona una variante para ${p.name}.`);return}const candidate={...p,variant};if(lineStock(candidate)<1)return;setCart(items=>items.some(x=>lineKey(x)===lineKey(candidate))?items.map(x=>lineKey(x)===lineKey(candidate)?{...x,quantity:Math.min(x.quantity+1,lineStock(x))}:x):[...items,{...candidate,quantity:1}])};
const save=async(finalize:boolean,form:HTMLFormElement)=>{
if(!cart.length){setError('Agrega al menos un producto.');
return}if(finalize&&!confirm('¿Finalizar esta venta? Se descontará el stock de los productos.'))return;
setSaving(true);
setError('');
const f=new FormData(form);
try{const result=await request('/admin/manual-sales',{method:'POST',body:JSON.stringify({customer_id:occasional?null:Number(customerId),customer_name:f.get('customer_name')||null,customer_phone:f.get('customer_phone')||null,payment_method:f.get('payment_method'),payment_status:f.get('payment_status'),sales_channel:f.get('sales_channel'),notes:f.get('notes')||null,finalize,idempotency_key:idempotencyKey,items:cart.map(x=>({product_id:x.id,variant_id:x.variant?.id||null,quantity:x.quantity}))})});
created(result.id)}catch(reason){setError((reason as Error).message);
setSaving(false)}};
return <Overlay title="Nueva venta" close={close}>
<form onSubmit={e=>{e.preventDefault();void save(false,e.currentTarget)}} className="mt-6 grid gap-6 lg:grid-cols-2">
<div>
<h3 className="font-semibold">Cliente</h3>
<div className="mt-3 flex gap-2">
<button type="button" onClick={()=>setOccasional(true)} className={`rounded-full px-4 py-2 ${occasional?'bg-[#231f20] text-white':'border'}`}>Cliente ocasional</button>
<button type="button" onClick={()=>setOccasional(false)} className={`rounded-full px-4 py-2 ${!occasional?'bg-[#231f20] text-white':'border'}`}>Cliente registrado</button>
</div>{occasional?<div className="mt-3 grid gap-3 sm:grid-cols-2">
<input className={field} name="customer_name" placeholder="Nombre opcional"/>
<input className={field} name="customer_phone" placeholder="Teléfono opcional"/>
</div>:<>
<input className={`${field} mt-3`} value={customerSearch} onChange={e=>setCustomerSearch(e.target.value)} placeholder="Buscar por nombre o teléfono"/>
<select className={`${field} mt-3`} value={customerId} onChange={e=>setCustomerId(e.target.value)} required>
<option value="">Selecciona una clienta</option>{customers.filter(c=>(c.name+' '+c.phone).toLowerCase().includes(customerSearch.toLowerCase())).map(c=>
<option value={c.id}>{c.name} · {c.phone}</option>)}</select>
<div className="mt-3 grid grid-cols-[1fr_1fr_auto] gap-2"><input className={field} value={quickName} onChange={e=>setQuickName(e.target.value)} placeholder="Nueva clienta"/><input className={field} value={quickPhone} onChange={e=>setQuickPhone(e.target.value)} placeholder="Teléfono"/><button type="button" onClick={createQuickCustomer} className="rounded-xl border px-3 text-sm">Crear</button></div>
</>}<h3 className="mt-6 font-semibold">Productos</h3>
<label className="mt-3 flex items-center gap-2 rounded-xl border px-3">
<Search size={18}/>
<input className="w-full py-3 outline-none" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar por nombre o SKU"/>
</label>
<div className="mt-3 max-h-72 space-y-2 overflow-auto">{visible.flatMap(p=>p.has_variants?(p.variants||[]).filter((v:Row)=>v.is_active).map((v:Row)=><button key={`${p.id}:${v.id}`} type="button" disabled={!v.stock} onClick={()=>add(p,v)} className="flex w-full items-center justify-between rounded-xl bg-white p-3 text-left disabled:opacity-45"><span><b>{p.name} — {v.name}</b><small className="block">{v.sku} · Stock {v.stock}</small></span><span>S/ {linePrice({...p,variant:v}).toFixed(2)}</span></button>):[<button key={`${p.id}:0`} type="button" disabled={!p.stock} onClick={()=>add(p)} className="flex w-full items-center justify-between rounded-xl bg-white p-3 text-left disabled:opacity-45"><span><b>{p.name}</b><small className="block">{p.sku} · Stock {p.stock}</small></span><span>S/ {linePrice(p).toFixed(2)}</span></button>])}</div>
</div>
<div>
<h3 className="font-semibold">Venta</h3>
<div className="mt-3 space-y-2">{cart.map(item=>
<div className="flex items-center gap-3 rounded-xl bg-white p-3">
<div className="flex-1">
<b>{item.name}{item.variant?` — ${item.variant.name}`:''}</b>
<p>{item.variant?.sku||item.sku} · S/ {linePrice(item).toFixed(2)}</p>
</div>
<button type="button" onClick={()=>setCart(xs=>xs.map(x=>lineKey(x)===lineKey(item)?{...x,quantity:Math.max(1,x.quantity-1)}:x))}>
<Minus size={16}/>
</button>{item.quantity}<button type="button" disabled={item.quantity>=lineStock(item)} onClick={()=>setCart(xs=>xs.map(x=>lineKey(x)===lineKey(item)?{...x,quantity:x.quantity+1}:x))}>
<Plus size={16}/>
</button>
<button type="button" onClick={()=>setCart(xs=>xs.filter(x=>lineKey(x)!==lineKey(item)))}>
<Trash2 size={17}/>
</button>
</div>)}{!cart.length&&<p className="rounded-xl bg-white p-6 text-center text-gray-500">
<ShoppingCart className="mx-auto mb-2"/>Sin productos</p>}</div>
<div className="mt-5 grid gap-3 sm:grid-cols-2">
<select className={field} name="payment_method" required>{['cash','yape','plin','transfer','other'].map(x=>
<option value={x}>{paymentMethodLabel(x)}</option>)}</select>
<select className={field} name="payment_status">
<option value="paid">Pagado</option>
<option value="pending">Pendiente</option>
</select>
<select className={field} name="sales_channel">
<option value="in_store">Presencial</option>
<option value="whatsapp">WhatsApp</option>
<option value="instagram">Instagram</option>
<option value="web">Tienda web</option>
<option value="other">Otro</option>
</select>
<textarea className={field} name="notes" placeholder="Observaciones"/>
</div>
<p className="mt-5 text-right text-2xl font-semibold">Total: S/ {total.toFixed(2)}</p>{error&&<p className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="mt-5 flex flex-wrap justify-end gap-3">
<button disabled={saving} className="rounded-full border px-5 py-3 disabled:opacity-50">Guardar como pendiente</button>
<button disabled={saving} type="button" onClick={e=>{if(e.currentTarget.form)void save(true,e.currentTarget.form)}} className="rounded-full bg-green-600 px-5 py-3 text-white disabled:opacity-50">Finalizar venta</button>
</div>
</div>
</form>
</Overlay>}



