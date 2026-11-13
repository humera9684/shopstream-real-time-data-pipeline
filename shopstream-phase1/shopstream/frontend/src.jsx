import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ShoppingBag, Search, ArrowRight, Minus, Plus, X, CheckCircle2, Package, Database, Menu } from 'lucide-react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SalesDashboard from './src/SalesDashboard.jsx';
import './style.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const art = {
  headphones: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=85',
  backpack: 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800&q=85',
  coffee: 'https://images.unsplash.com/photo-1511920170033-f8396924c348?w=800&q=85',
  lamp: 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=800&q=85',
  shoes: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=85',
  watch: 'https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=800&q=85',
  camera: 'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=800&q=85',
  sofa: 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800&q=85',
  latte: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800&q=85',
  sunglasses: 'https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=800&q=85',
  handbag: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=800&q=85',
  yoga: 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&q=85',
  dumbbells: 'https://images.unsplash.com/photo-1594737625785-a6cbdabd333c?w=800&q=85',
  barbell: 'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=800&q=85',
  cream: 'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=800&q=85',
  makeup: 'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=800&q=85',
  books: 'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=800&q=85',
  poetry: 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=800&q=85',
  // keys used by seed_data.py
  'wireless-earbuds': 'https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?w=800&q=85',
  'bluetooth-speaker': 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=800&q=85',
  'mechanical-keyboard': 'https://images.unsplash.com/photo-1595225476474-87563907a212?w=800&q=85',
  'usb-c-hub': 'https://images.unsplash.com/photo-1586210579191-33b45e38fa2c?w=800&q=85',
  webcam: 'https://images.unsplash.com/photo-1623949556303-b0d17d198863?w=800&q=85',
  'power-bank': 'https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=800&q=85',
  'water-bottle': 'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=800&q=85',
  'yoga-mat': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&q=85',
  'travel-mug': 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=800&q=85',
  'tote-bag': 'https://images.unsplash.com/photo-1544816155-12df9643f363?w=800&q=85',
  'notebook-set': 'https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=800&q=85',
  'scented-candle': 'https://images.unsplash.com/photo-1602874801007-bd458bb1b8b6?w=800&q=85',
  'throw-blanket': 'https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=800&q=85',
  'cutting-board': 'https://images.unsplash.com/photo-1610701596007-11502861dcfa?w=800&q=85',
  'plant-pot': 'https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=800&q=85',
  'wall-clock': 'https://images.unsplash.com/photo-1563861826100-9cb868fdbe1c?w=800&q=85',
  'denim-jacket': 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800&q=85',
  'wool-scarf': 'https://images.unsplash.com/photo-1457545195570-67f207084966?w=800&q=85',
  'leather-wallet': 'https://images.unsplash.com/photo-1627123424574-724758594e93?w=800&q=85',
  'canvas-cap': 'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=800&q=85'
};
const byCategory = {Electronics:'headphones',Lifestyle:'backpack',Home:'sofa',Fashion:'shoes',Sports:'yoga',Beauty:'cream',Books:'books'};
const img = p => art[p.image] || art[byCategory[p.category]] || art.backpack;
let refreshing = null;
const money = n => new Intl.NumberFormat('en-US', {style:'currency',currency:'USD'}).format(Number(n));

function App(){
  const [products,setProducts]=useState([]),[cart,setCart]=useState({}),[category,setCategory]=useState('All'),[search,setSearch]=useState('');
  const [open,setOpen]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState(''),[confirmation,setConfirmation]=useState(null);
  const [token,setToken]=useState(()=>{try{return localStorage.getItem('ss_token')||''}catch{return ''}});
  const [user,setUser]=useState(()=>{try{return JSON.parse(localStorage.getItem('ss_user')||'null')}catch{return null}});
  const [authOpen,setAuthOpen]=useState(false),[mode,setMode]=useState('login'),[form,setForm]=useState({name:'',email:'',password:''}),[authError,setAuthError]=useState(''),[authLoading,setAuthLoading]=useState(false);
  const tokenRef=useRef(token),resumeRef=useRef(false);
  const saveSession=(t,u)=>{tokenRef.current=t;setToken(t);setUser(u);try{if(t){localStorage.setItem('ss_token',t);localStorage.setItem('ss_user',JSON.stringify(u))}else{localStorage.removeItem('ss_token');localStorage.removeItem('ss_user')}}catch{}};
  const refreshSession=()=>{
    if(!refreshing)refreshing=fetch(`${API}/auth/refresh`,{method:'POST',credentials:'include'}).then(async r=>{
      const d=await r.json().catch(()=>({}));if(!r.ok)throw Error('Session expired');
      saveSession(d.token,d.user);return d.token;
    }).finally(()=>{refreshing=null});
    return refreshing;
  };
  async function authed(path,opts={}){
    const send=t=>fetch(`${API}${path}`,{...opts,credentials:'include',headers:{...opts.headers,Authorization:`Bearer ${t}`}});
    const first=await send(tokenRef.current);
    if(first.status!==401)return first;
    try{return await send(await refreshSession())}catch{return first}
  }
  async function signOut(){
    try{await fetch(`${API}/auth/logout`,{method:'POST',credentials:'include'})}catch{}
    saveSession('',null);
  }
  const setField=k=>e=>setForm(f=>({...f,[k]:e.target.value}));
  async function authSubmit(e){
    e.preventDefault();setAuthError('');setAuthLoading(true);
    try{
      const body=mode==='register'?form:{email:form.email,password:form.password};
      const r=await fetch(`${API}/auth/${mode}`,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      const d=await r.json().catch(()=>({}));
      if(!r.ok)throw Error(Array.isArray(d.detail)?d.detail[0].msg:d.detail||'Could not sign in');
      saveSession(d.token,d.user);setAuthOpen(false);setForm({name:'',email:'',password:''});
      if(resumeRef.current){resumeRef.current=false;setOpen(true)}
    }catch(e){setAuthError(e.message)}finally{setAuthLoading(false)}
  }
  const openAuth=(m,resume=false)=>{resumeRef.current=resume;setMode(m);setAuthError('');setAuthOpen(true)};
  const refresh=()=>fetch(`${API}/products`).then(r=>{if(!r.ok)throw Error('Could not load products');return r.json()}).then(setProducts).catch(e=>setError(e.message));
  useEffect(()=>{refresh()},[]);
  const categories=['All',...new Set(products.map(p=>p.category))];
  const shown=products.filter(p=>(category==='All'||p.category===category)&&`${p.name} ${p.description} ${p.category}`.toLowerCase().includes(search.toLowerCase()));
  const items=products.filter(p=>cart[p.id]>0),count=Object.values(cart).reduce((a,b)=>a+b,0),total=items.reduce((a,p)=>a+cart[p.id]*Number(p.price),0);
  const change=(id,delta)=>setCart(old=>({...old,[id]:Math.max(0,Math.min(products.find(p=>p.id===id)?.stock??0,(old[id]||0)+delta))}));
  async function checkout(e){
    e.preventDefault();setError('');
    if(!token){setOpen(false);openAuth('login',true);return}
    setLoading(true);
    try{
      const response=await authed('/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items:items.map(p=>({product_id:p.id,quantity:cart[p.id]}))})});
      const data=await response.json();
      if(response.status===401){saveSession('',null);setOpen(false);openAuth('login',true);setAuthError('Your session expired. Please sign in again.');return}
      if(!response.ok)throw Error(data.detail||'Checkout failed');
      setConfirmation(data);setCart({});await refresh();
    }catch(e){setError(e.message)}finally{setLoading(false)}
  }
  return <>
    <div className="announcement">A fresh take on everyday essentials <span>✦</span> Free shipping on orders over $150</div>
    <header><a href="#top" className="logo"><span className="mark">S<span>✦</span></span> shopstream<span className="logo-dot">.</span></a><nav><a href="#shop">Shop all</a><a href="#story">Our story</a><a href="http://localhost:8000/docs" target="_blank">API docs ↗</a></nav>{user?<span className="account"><span>Hi, {user.name.split(' ')[0]}</span><button className="account-btn" onClick={signOut}>Sign out</button></span>:<button className="account-btn" onClick={()=>openAuth('login')}>Sign in</button>}<button className="bag" onClick={()=>{setOpen(true);setConfirmation(null)}} aria-label="Open cart"><ShoppingBag size={21}/><span>{count}</span></button></header>
    <main id="top">
      <section className="hero"><div className="hero-copy"><span className="eyebrow">THE EVERYDAY EDIT · 2026</span><h1>Good things.<br/><em>Better days.</em></h1><p>Considered essentials for work, home, and everything in between. Discover pieces worth making room for.</p><a className="cta" href="#shop">Explore the collection <ArrowRight size={18}/></a><div className="hero-foot"><span>✦ Thoughtfully selected</span><span>✦ Made for real life</span></div></div><div className="hero-photo"><img src="https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=1300&q=85" alt="Curated apparel and essentials"/><span className="hero-note">THE ART OF<br/>EVERYDAY LIVING</span></div></section>
      <section id="shop" className="collection"><div className="section-heading"><div><span className="eyebrow">DISCOVER YOUR NEW FAVORITES</span><h2>The good stuff.</h2></div><p>Simple choices, better everyday moments.<br/>Explore our handpicked collection.</p></div><div className="tools"><div className="categories">{categories.map(c=><button key={c} className={category===c?'active':''} onClick={()=>setCategory(c)}>{c}</button>)}</div><label className="search"><Search size={17}/><input placeholder="Search products" value={search} onChange={e=>setSearch(e.target.value)}/></label></div>
      <div className="products">{shown.map((p,i)=><article className="product" key={p.id}><div className="product-image"><img src={img(p)} alt={p.name}/><span className="product-tag">{i===0?'POPULAR':p.category.toUpperCase()}</span><button className="quick-add" disabled={!p.stock||cart[p.id]>=p.stock} onClick={()=>{change(p.id,1);setConfirmation(null);setOpen(true)}}><Plus size={17}/> Add to bag</button></div><div className="product-info"><div><span className="product-category">{p.category}</span><h3>{p.name}</h3></div><strong>{money(p.price)}</strong></div><p>{p.description}</p><span className="inventory">{p.stock>0?`${p.stock} in stock`:'Sold out'}</span></article>)}</div>{shown.length===0&&<div className="empty">No products found. Try another search.</div>}</section>
      <section className="story" id="story"><div><span className="eyebrow">BEHIND THE STORE</span><h2>Built for shopping.<br/><em>Designed for data.</em></h2></div><div><p>ShopStream is a hands-on e-commerce and data engineering project. Every test order is written to PostgreSQL—and will become a streaming event in the next phase.</p><div className="tech"><span><Package size={17}/> React storefront</span><span><Database size={17}/> FastAPI + PostgreSQL</span></div></div></section>
    </main><footer><span className="logo">shopstream<span className="logo-dot">.</span></span><span>A learning project. Test orders only — no real payments.</span><span>© 2026 ShopStream</span></footer>
    {open&&<div className="overlay" onMouseDown={e=>{if(e.target===e.currentTarget)setOpen(false)}}><aside className="drawer"><div className="drawer-header"><div><span className="eyebrow">YOUR SELECTION</span><h2>Shopping bag <small>({count})</small></h2></div><button className="iconbtn" onClick={()=>setOpen(false)} aria-label="Close cart"><X/></button></div>{confirmation?<div className="success"><CheckCircle2 size={50}/><h3>Order placed!</h3><p>Test order #{confirmation.order_id} has been saved to PostgreSQL.</p><strong>{money(confirmation.total)}</strong><button className="checkout" onClick={()=>{setConfirmation(null);setOpen(false)}}>Keep shopping</button></div>:<><div className="cart-items">{items.length===0?<div className="cart-empty"><ShoppingBag size={45}/><h3>Your bag is empty</h3><p>Good things are waiting.</p></div>:items.map(p=><div className="cart-item" key={p.id}><img src={img(p)} alt=""/><div><h3>{p.name}</h3><p>{money(p.price)}</p><div className="qty"><button onClick={()=>change(p.id,-1)}><Minus size={13}/></button><span>{cart[p.id]}</span><button onClick={()=>change(p.id,1)} disabled={cart[p.id]>=p.stock}><Plus size={13}/></button></div></div><strong>{money(Number(p.price)*cart[p.id])}</strong></div>)}</div>{items.length>0&&<form className="checkout-form" onSubmit={checkout}><div className="subtotal"><span>Subtotal</span><strong>{money(total)}</strong></div><p className="fineprint">Demo checkout · no payment collected</p>{user&&<p className="fineprint">Ordering as {user.name} ({user.email})</p>}{error&&<p className="error">{error}</p>}<button className="checkout" disabled={loading}>{loading?'Placing order...':token?'Place test order':'Sign in to check out'} <ArrowRight size={18}/></button></form>}</>}</aside></div>}
    {authOpen&&<div className="overlay auth-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)setAuthOpen(false)}}><form className="auth-modal" onSubmit={authSubmit}><div className="drawer-header"><div><span className="eyebrow">{mode==='login'?'WELCOME BACK':'JOIN SHOPSTREAM'}</span><h2>{mode==='login'?'Sign in':'Create account'}</h2></div><button type="button" className="iconbtn" onClick={()=>setAuthOpen(false)} aria-label="Close"><X/></button></div>{mode==='register'&&<input required maxLength="120" placeholder="Your name" value={form.name} onChange={setField('name')}/>}<input required type="email" maxLength="200" placeholder="Email address" autoComplete="email" value={form.email} onChange={setField('email')}/><input required type="password" minLength={mode==='register'?8:1} maxLength="128" placeholder={mode==='register'?'Password (min 8 characters)':'Password'} autoComplete={mode==='login'?'current-password':'new-password'} value={form.password} onChange={setField('password')}/>{authError&&<p className="error">{authError}</p>}<button className="checkout" disabled={authLoading}>{authLoading?'Please wait...':mode==='login'?'Sign in':'Create account'} <ArrowRight size={18}/></button><p className="auth-switch">{mode==='login'?'New here?':'Already have an account?'} <button type="button" onClick={()=>{setMode(mode==='login'?'register':'login');setAuthError('')}}>{mode==='login'?'Create an account':'Sign in'}</button></p></form></div>}
    {error&&!open&&<div className="toast" role="alert">{error}<button onClick={()=>setError('')}><X size={14}/></button></div>}
  </>;
}

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/analytics" element={<SalesDashboard />} />
    </Routes>
  </BrowserRouter>
);
