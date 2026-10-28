import { useEffect, useState } from "react";
import { api } from "./api";

const sections = ["Place Order", "Track Order", "Agent Dashboard", "Admin Analytics"];

function Icon({ name, size = 20 }) {
  const paths = {
    package: <><path d="m4 7 8-4 8 4-8 4-8-4Z" /><path d="M4 7v10l8 4 8-4V7M12 11v10" /></>,
    truck: <><path d="M3 6h11v10H3zM14 10h4l3 3v3h-7z" /><circle cx="7" cy="18" r="2" /><circle cx="18" cy="18" r="2" /></>,
    pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
    user: <><circle cx="12" cy="8" r="3.5" /><path d="M5 20c.7-3.3 3-5 7-5s6.3 1.7 7 5" /></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m4 7 8 6 8-6" /></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 5 5" /></>,
    arrow: <><path d="M4 12h15M14 7l5 5-5 5" /></>,
    clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3 2" /></>,
    chart: <><path d="M4 19V5M4 19h17" /><path d="m7 15 3-4 3 2 5-7" /></>,
  };
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Message({ error, children }) {
  return <>{error && <p className="error">{error}</p>}{children}</>;
}

function Logo() {
  return <div className="logo" aria-label="SmartFlow home"><span>Smart</span><strong>Flow</strong><small>DELIVER SMARTER</small></div>;
}

function UserAvatar() {
  return <div className="avatar" aria-label="Profile"><Icon name="user" size={21} /></div>;
}

function Illustration() {
  return <div className="illustration" aria-label="SmartFlow delivery route illustration">
    <div className="cloud cloud-one" /><div className="cloud cloud-two" />
    <div className="status-float"><Icon name="truck" size={24} /><div><b>On the way</b><span><i /><i /><i /><i /></span></div></div>
  </div>;
}

function Feature({ icon, title, text }) {
  return <div className="feature"><div className="feature-icon"><Icon name={icon} size={23} /></div><div><h3>{title}</h3><p>{text}</p></div></div>;
}

function PlaceOrder() {
  const [form, setForm] = useState({ name: "", email: "", item: "", pickup_lat: "19.076", pickup_lng: "72.878", drop_address: "" });
  const [result, setResult] = useState(null); const [error, setError] = useState(""); const [submitting, setSubmitting] = useState(false);
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event) => {
    event.preventDefault(); setError(""); setSubmitting(true);
    try { setResult(await api.createOrder({ ...form, pickup_lat: Number(form.pickup_lat), pickup_lng: Number(form.pickup_lng) })); }
    catch (e) { setError(e.message); } finally { setSubmitting(false); }
  };
  const fields = [
    ["name", "Name", "user", "Enter sender/receiver name"],
    ["email", "Email", "mail", "Enter email address"],
    ["item", "Item", "package", "What are you delivering?"],
    ["drop_address", "Drop Address", "pin", "Full delivery address"],
    ["pickup_lat", "Pickup Latitude", "pin", "e.g. 19.076"],
    ["pickup_lng", "Pickup Longitude", "pin", "e.g. 72.878"],
  ];
  return <section className="order-card">
    <div className="card-heading"><div className="heading-icon"><Icon name="package" size={26} /></div><div><h2>Place an order</h2><p>Enter the delivery details to create a new order.</p></div></div>
    <Message error={error}><form onSubmit={submit} className="form-grid">{fields.map(([key, label, icon, placeholder]) => <label key={key}>{label}<span className="input-wrap"><Icon name={icon} size={18} /><input required type={key === "email" ? "email" : ["pickup_lat", "pickup_lng"].includes(key) ? "number" : "text"} step={["pickup_lat", "pickup_lng"].includes(key) ? "any" : undefined} value={form[key]} placeholder={placeholder} onChange={(e) => update(key, e.target.value)} /></span></label>)}<button className="primary-button submit-button" disabled={submitting}>{submitting ? "Placing..." : <>Place order <Icon name="arrow" size={19} /></>}</button></form></Message>
    {result && <p className="success">Order <strong>#{result.order_id}</strong> placed. The worker will assign an agent.</p>}
  </section>;
}

function TrackOrder() {
  const [id, setId] = useState(""); const [order, setOrder] = useState(null); const [proof, setProof] = useState(""); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  const find = async (event) => { event.preventDefault(); setError(""); setLoading(true); try { const found = await api.getOrder(id); setOrder(found); setProof(""); try { setProof((await api.getProofUrl(id)).url); } catch { /* proof is optional */ } } catch (e) { setError(e.message); } finally { setLoading(false); } };
  const moveToDelivery = async () => { try { await api.outForDelivery(id); setOrder(await api.getOrder(id)); } catch (e) { setError(e.message); } };
  const upload = async (event) => { if (!event.target.files[0]) return; try { await api.uploadProof(id, event.target.files[0]); setOrder(await api.getOrder(id)); setProof((await api.getProofUrl(id)).url); } catch (e) { setError(e.message); } };
  return <section className="content-card"><div className="section-title"><div className="heading-icon small"><Icon name="search" size={22} /></div><div><h2>Track an order</h2><p>Follow an order and manage its delivery proof.</p></div></div><form className="inline-form" onSubmit={find}><input aria-label="Order ID" placeholder="Enter order ID" value={id} onChange={(e) => setId(e.target.value)} required /><button className="primary-button">{loading ? "Searching..." : <>Search <Icon name="arrow" size={17} /></>}</button></form><Message error={error}>{order && <div className="result-card"><div className="result-top"><div><span className="eyebrow">ORDER #{order.id}</span><h3>{order.item}</h3></div><span className={`status-pill ${order.status.toLowerCase().replaceAll(" ", "-")}`}>{order.status}</span></div><p>{order.drop_address}</p><p className="agent-line"><Icon name="user" size={17} /> Agent: <strong>{order.agent_name || "Waiting for assignment"}</strong></p>{order.history?.length > 0 && <div className="history"><b>Order history</b>{order.history.map((item, index) => <div key={`${item.status}-${index}`}><span className="history-dot" />{item.status}<time>{item.changed_at}</time></div>)}</div>}<div className="result-actions">{order.status === "Assigned" && <button className="primary-button" onClick={moveToDelivery}>Mark out for delivery</button>}{order.status === "Out for Delivery" && <label className="upload-button">Upload proof<input type="file" accept="image/*" onChange={upload} /></label>}{proof && <a className="text-link" href={proof} target="_blank" rel="noreferrer">View delivery proof <Icon name="arrow" size={16} /></a>}</div></div>}</Message></section>;
}

function Agents() {
  const [agents, setAgents] = useState([]); const [selected, setSelected] = useState(null); const [agentOrders, setAgentOrders] = useState([]); const [error, setError] = useState("");
  const load = () => api.getAgents().then(setAgents).catch((e) => setError(e.message)); useEffect(() => { load(); }, []);
  const change = async (id, status) => { try { await api.updateAgentStatus(id, status); load(); } catch (e) { setError(e.message); } };
  const inspect = async (agent) => { setSelected(agent); try { setAgentOrders(await api.getAgentOrders(agent.id)); } catch (e) { setError(e.message); } };
  return <section className="content-card"><div className="section-title"><div className="heading-icon small"><Icon name="truck" size={22} /></div><div><h2>Agent dashboard</h2><p>Monitor availability and active delivery assignments.</p></div></div><Message error={error}><div className="agent-list">{agents.length ? agents.map((agent) => <div className="agent-row" key={agent.id}><button className="agent-name" onClick={() => inspect(agent)}>{agent.name}<small>View active orders</small></button><span className={`status-pill ${agent.status.toLowerCase()}`}>{agent.status}</span><select aria-label={`Update ${agent.name} status`} value={agent.status} onChange={(e) => change(agent.id, e.target.value)}>{["Free", "Busy", "Offline"].map((status) => <option key={status}>{status}</option>)}</select></div>) : <div className="empty-state">No agents available.</div>}</div>{selected && <div className="nested-card"><h3>{selected.name}'s active orders</h3>{agentOrders.length ? agentOrders.map((order) => <p key={order.id}>#{order.id} · {order.item}<span>{order.status}</span></p>) : <p className="muted">No active orders assigned.</p>}</div>}</Message></section>;
}

function Analytics() {
  const [data, setData] = useState(null); const [error, setError] = useState("");
  useEffect(() => { api.getAnalytics().then(setData).catch((e) => setError(e.message)); }, []);
  const total = data ? Object.values(data.by_status).reduce((sum, count) => sum + count, 0) : 0;
  return <section className="content-card"><div className="section-title"><div className="heading-icon small"><Icon name="chart" size={22} /></div><div><h2>Admin analytics</h2><p>A clear view of current delivery operations.</p></div></div><Message error={error}>{data && <><div className="analytics-stats"><div><span>Total orders</span><b>{total}</b></div><div><span>Average delivery</span><b>{data.avg_delivery_minutes ?? "—"}<small>{data.avg_delivery_minutes != null ? " min" : ""}</small></b></div></div><div className="analytics-grid"><div className="nested-card"><h3>Orders by status</h3>{Object.keys(data.by_status).length ? Object.entries(data.by_status).map(([status, count]) => <p key={status}><span className="legend-dot" />{status}<strong>{count}</strong></p>) : <p className="muted">No orders yet.</p>}</div><div className="nested-card"><h3>Orders per agent</h3>{Object.keys(data.per_agent).length ? Object.entries(data.per_agent).map(([agent, count]) => <p key={agent}>{agent}<strong>{count}</strong></p>) : <p className="muted">No assignments yet.</p>}</div></div></>}</Message></section>;
}

export default function App() {
  const [active, setActive] = useState(sections[0]);
  return <div className="app-shell"><header className="site-header"><Logo /><nav aria-label="Main navigation">{sections.map((section) => <button className={active === section ? "active" : ""} onClick={() => setActive(section)} key={section}>{section}</button>)}</nav><UserAvatar /></header><main><div className="hero"><div className="hero-copy"><p className="eyebrow">DELIVERY OPERATIONS <span /></p><h1>Move every<br />order forward.</h1>  </div><Illustration /></div>{active === sections[0] && <><PlaceOrder /><div className="feature-strip"><Feature icon="truck" title="Faster Deliveries" text="Get your orders moving effortlessly." /><Feature icon="pin" title="Real-time Tracking" text="Stay updated at every step." /><Feature icon="package" title="Smooth Operations" text="Plan, assign and deliver with ease." /></div></>}{active === sections[1] && <TrackOrder />}{active === sections[2] && <Agents />}{active === sections[3] && <Analytics />}</main></div>;
}
