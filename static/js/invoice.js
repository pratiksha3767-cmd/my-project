function esc(v){ return String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function dateText(v){ try{return new Date(v).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short'});}catch{return v;} }
async function loadInvoice(){
  const msg=document.getElementById('invoiceMessage');
  const r=await fetch('/api/orders/'+encodeURIComponent(window.ORDER_ID));
  const d=await r.json();
  if(!r.ok){msg.textContent=d.message||'Invoice unavailable';return;}
  const o=d.order, c=o.customer||{};
  document.getElementById('invoice').innerHTML=`
    <div class="invoice-top"><div><img src="/static/images/logo.png" alt="Mini Fresh Basket" class="invoice-logo"><h1>Tax / Order Invoice</h1></div><div class="invoice-meta"><b>Order ID</b><span>#${esc(o.id.slice(-10).toUpperCase())}</span><b>Date</b><span>${esc(dateText(o.created_at))}</span></div></div>
    <div class="invoice-status"><span>Order Status: <b>${esc(o.status)}</b></span><span>Payment: <b>${esc(o.payment_status)}</b> (${esc(o.payment_method)})</span></div>
    <div class="customer-box"><h3>Customer & Delivery Details</h3><p><b>${esc(c.name)}</b><br>${esc(c.phone)}<br>${esc(c.email)}<br>${esc(c.address)}, ${esc(c.city)} - ${esc(c.pincode)}</p></div>
    <table class="invoice-table"><thead><tr><th>Item</th><th>Unit</th><th>Qty</th><th>Price</th><th>Amount</th></tr></thead><tbody>${o.items.map(i=>`<tr><td>${esc(i.name)}</td><td>${esc(i.unit)}</td><td>${i.qty}</td><td>₹${Number(i.price).toFixed(2)}</td><td>₹${Number(i.line_total).toFixed(2)}</td></tr>`).join('')}</tbody></table>
    <div class="invoice-totals"><div><span>Subtotal</span><b>₹${o.subtotal.toFixed(2)}</b></div><div><span>Delivery</span><b>₹${o.delivery_charge.toFixed(2)}</b></div><div><span>Tax</span><b>₹${o.tax.toFixed(2)}</b></div><div class="grand"><span>Grand Total</span><b>₹${o.total.toFixed(2)}</b></div></div>
    <div class="transaction"><b>Transaction Reference:</b> ${esc(o.transaction_id)}<br><small>For this college-project demo, UPI/Card payments are simulated. No card/UPI credentials are stored.</small></div>
    <div class="invoice-actions no-print"><button class="btn" onclick="window.print()">🖨️ Print / Save as PDF</button><a class="btn secondary" href="/">Continue Shopping</a></div>
    <p class="thanks">Thank you for shopping with Mini Fresh Basket! 🌿</p>`;
  document.getElementById('invoice').classList.remove('hidden');
}
loadInvoice();
