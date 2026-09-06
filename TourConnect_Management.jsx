import React, { useState, useRef } from "react";
import {
  Lock, ClipboardList, ChevronRight, ChevronLeft, Check, Store,
  Star, Mail, ShieldCheck, Plus, Trash2, Tag, ImagePlus, X,
  MapPin, FolderPlus, Clock, CheckCircle2, XCircle, Play,
  Sparkles, Coins, ShieldAlert, Building2, LayoutList,
} from "lucide-react";

/* ---------------------------------------------------------------------
   TOKENS — shared system: forest = sustainability, deep slate =
   navigation / business & admin chrome, amber = ratings, points, offers.
------------------------------------------------------------------------ */
const T = {
  forest: "#21C45D",
  forestDark: "#157A3D",
  forestTint: "#E7F8EE",
  slate: "#0E2238",
  slateMid: "#173A57",
  slateSoft: "#DCE6EE",
  amber: "#F59E0B",
  amberDark: "#8A5A05",
  amberTint: "#FEF3D9",
  rose: "#DC5B5B",
  roseTint: "#FBEAEA",
  paper: "#F5F7F3",
  card: "#FFFFFF",
  ink: "#101E17",
  sub: "#5B6B62",
  line: "#E1E7E0",
};

const fontImport = `@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap');`;

function Trail({ width = 90 }) {
  return (
    <svg width={width} height="12" viewBox="0 0 90 12" fill="none">
      <circle cx="4" cy="6" r="3.5" fill={T.forest} />
      <line x1="9" y1="6" x2="82" y2="6" stroke={T.forest} strokeWidth="2" strokeDasharray="1 6" strokeLinecap="round" />
      <path d="M87 6c0 2.5-3 5-3 5s-3-2.5-3-5a3 3 0 116 0z" fill={T.amber} />
    </svg>
  );
}

function H({ title, subtitle }) {
  return (
    <div className="mb-5">
      <h1 style={{ fontFamily: "Fraunces, serif", color: T.ink, fontWeight: 600 }} className="text-2xl mb-1.5">{title}</h1>
      <div className="mb-2"><Trail /></div>
      {subtitle && <p className="text-sm max-w-lg" style={{ color: T.sub }}>{subtitle}</p>}
    </div>
  );
}

function StatusPill({ status }) {
  const map = {
    Pending: { bg: T.amberTint, fg: T.amberDark, Icon: Clock },
    Approved: { bg: T.forestTint, fg: T.forestDark, Icon: CheckCircle2 },
    Rejected: { bg: T.roseTint, fg: "#A33232", Icon: XCircle },
  };
  const s = map[status];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium" style={{ background: s.bg, color: s.fg }}>
      <s.Icon size={12} /> {status}
    </span>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs font-medium mb-1 block" style={{ color: T.sub }}>{label}</span>
      {children}
    </label>
  );
}

const inputStyle = { background: T.card, border: `1px solid ${T.line}`, color: T.ink };
const inputClass = "w-full text-sm rounded-lg px-3 py-2.5 outline-none";

/* =======================================================================
   1. BUSINESS PORTAL
======================================================================= */

const LOCATION_TREE = {
  INDIA: {
    RAJASTHAN: { "JAIPUR": ["JAIPUR CITY"] },
    "UTTAR PRADESH": { "GAUTAM BUDDH NAGAR": ["NOIDA"] },
  },
};
const CATEGORIES = ["HOTEL", "RESTAURANT", "TRAVEL AGENCY", "TAXI SERVICE", "VEHICLE RENTAL", "TOUR GUIDE", "HERITAGE SITE", "ADVENTURE SPORTS"];

function AuthTabs({ tabs, active, setActive }) {
  return (
    <div className="flex rounded-lg overflow-hidden w-fit mb-5" style={{ border: `1px solid ${T.line}` }}>
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => setActive(t.key)}
          className="text-xs font-medium px-4 py-2.5 flex items-center gap-1.5"
          style={{ background: active === t.key ? T.slate : T.card, color: active === t.key ? "#fff" : T.sub }}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

function LoginForm({ role, onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  return (
    <div className="rounded-2xl p-5 max-w-sm" style={{ background: T.card, border: `1px solid ${T.line}` }}>
      <div className="space-y-3">
        <Field label="Email">
          <input className={inputClass} style={inputStyle} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@business.com" />
        </Field>
        <Field label="Password">
          <input type="password" className={inputClass} style={inputStyle} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        </Field>
        <button
          onClick={() => onLogin(email || `${role}@example.com`)}
          className="w-full text-sm font-medium rounded-lg py-2.5"
          style={{ background: T.forest, color: "#fff" }}
        >
          Log in
        </button>
        <p className="text-xs text-center" style={{ color: T.sub }}>Demo login — any email &amp; password works.</p>
      </div>
    </div>
  );
}

function ApplicationForm({ onSubmitted }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    ownerName: "", businessName: "", category: "", contact: "", email: "", description: "",
    country: "", state: "", district: "", city: "",
  });
  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const states = form.country ? Object.keys(LOCATION_TREE[form.country] || {}) : [];
  const districts = form.state ? Object.keys(LOCATION_TREE[form.country]?.[form.state] || {}) : [];
  const cities = form.district ? (LOCATION_TREE[form.country]?.[form.state]?.[form.district] || []) : [];

  const steps = ["Business details", "Location", "Review"];

  return (
    <div className="rounded-2xl p-5 max-w-xl" style={{ background: T.card, border: `1px solid ${T.line}` }}>
      <div className="flex items-center gap-2 mb-5">
        {steps.map((s, i) => (
          <React.Fragment key={s}>
            <div className="flex items-center gap-1.5">
              <span
                className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-semibold"
                style={{ background: step > i + 1 ? T.forest : step === i + 1 ? T.slate : T.paper, color: step >= i + 1 ? "#fff" : T.sub }}
              >
                {step > i + 1 ? <Check size={11} /> : i + 1}
              </span>
              <span className="text-xs" style={{ color: step === i + 1 ? T.ink : T.sub, fontWeight: step === i + 1 ? 600 : 400 }}>{s}</span>
            </div>
            {i < steps.length - 1 && <div className="flex-1"><Trail width={40} /></div>}
          </React.Fragment>
        ))}
      </div>

      {step === 1 && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Owner name"><input className={inputClass} style={inputStyle} value={form.ownerName} onChange={(e) => set({ ownerName: e.target.value })} /></Field>
            <Field label="Business name"><input className={inputClass} style={inputStyle} value={form.businessName} onChange={(e) => set({ businessName: e.target.value })} /></Field>
          </div>
          <Field label="Category">
            <select className={inputClass} style={inputStyle} value={form.category} onChange={(e) => set({ category: e.target.value })}>
              <option value="">Select a category</option>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Contact number"><input className={inputClass} style={inputStyle} value={form.contact} onChange={(e) => set({ contact: e.target.value })} /></Field>
            <Field label="Email"><input className={inputClass} style={inputStyle} value={form.email} onChange={(e) => set({ email: e.target.value })} /></Field>
          </div>
          <Field label="Description"><textarea rows={3} className={inputClass} style={inputStyle} value={form.description} onChange={(e) => set({ description: e.target.value })} /></Field>
        </div>
      )}

      {step === 2 && (
        <div className="grid grid-cols-2 gap-3">
          <Field label="Country">
            <select className={inputClass} style={inputStyle} value={form.country} onChange={(e) => set({ country: e.target.value, state: "", district: "", city: "" })}>
              <option value="">Select</option>
              {Object.keys(LOCATION_TREE).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="State">
            <select className={inputClass} style={inputStyle} disabled={!form.country} value={form.state} onChange={(e) => set({ state: e.target.value, district: "", city: "" })}>
              <option value="">Select</option>
              {states.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="District">
            <select className={inputClass} style={inputStyle} disabled={!form.state} value={form.district} onChange={(e) => set({ district: e.target.value, city: "" })}>
              <option value="">Select</option>
              {districts.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </Field>
          <Field label="City">
            <select className={inputClass} style={inputStyle} disabled={!form.district} value={form.city} onChange={(e) => set({ city: e.target.value })}>
              <option value="">Select</option>
              {cities.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-2 text-sm">
          {[["Owner", form.ownerName], ["Business", form.businessName], ["Category", form.category], ["Contact", form.contact], ["Email", form.email], ["Location", [form.city, form.district, form.state, form.country].filter(Boolean).join(", ")]].map(([k, v]) => (
            <div key={k} className="flex justify-between py-1.5" style={{ borderBottom: `1px solid ${T.line}` }}>
              <span style={{ color: T.sub }}>{k}</span>
              <span style={{ color: T.ink, fontWeight: 500 }}>{v || "—"}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-between mt-5">
        <button
          onClick={() => setStep((s) => Math.max(1, s - 1))}
          disabled={step === 1}
          className="text-xs font-medium rounded-lg px-3.5 py-2 flex items-center gap-1 disabled:opacity-30"
          style={{ background: T.paper, color: T.ink }}
        >
          <ChevronLeft size={13} /> Back
        </button>
        {step < 3 ? (
          <button onClick={() => setStep((s) => s + 1)} className="text-xs font-medium rounded-lg px-3.5 py-2 flex items-center gap-1" style={{ background: T.slate, color: "#fff" }}>
            Next <ChevronRight size={13} />
          </button>
        ) : (
          <button onClick={onSubmitted} className="text-xs font-medium rounded-lg px-4 py-2 flex items-center gap-1.5" style={{ background: T.forest, color: "#fff" }}>
            <ClipboardList size={13} /> Submit application
          </button>
        )}
      </div>
    </div>
  );
}

function BusinessAuthGate({ onLogin }) {
  const [tab, setTab] = useState("login");
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <div className="rounded-2xl p-6 max-w-md text-center" style={{ background: T.forestTint, border: `1px solid ${T.forest}` }}>
        <CheckCircle2 size={26} color={T.forestDark} className="mx-auto mb-2" />
        <p className="text-sm font-medium mb-1" style={{ color: T.forestDark }}>Application submitted</p>
        <p className="text-xs" style={{ color: T.sub }}>An admin will review it under Pending Approvals. You'll be able to log in once it's approved.</p>
      </div>
    );
  }

  return (
    <div>
      <AuthTabs
        tabs={[{ key: "login", label: "🔑 Business Owner Login" }, { key: "apply", label: "📋 New Business Application" }]}
        active={tab} setActive={setTab}
      />
      {tab === "login" ? <LoginForm role="business" onLogin={onLogin} /> : <ApplicationForm onSubmitted={() => setSubmitted(true)} />}
    </div>
  );
}

function MetricsBar({ email }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      <div className="rounded-xl p-3.5 flex items-center gap-3" style={{ background: T.card, border: `1px solid ${T.line}` }}>
        <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: T.forestTint }}><ShieldCheck size={16} color={T.forestDark} /></div>
        <div><p className="text-xs" style={{ color: T.sub }}>Account status</p><StatusPill status="Approved" /></div>
      </div>
      <div className="rounded-xl p-3.5 flex items-center gap-3" style={{ background: T.card, border: `1px solid ${T.line}` }}>
        <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: T.amberTint }}><Star size={16} color={T.amber} fill={T.amber} /></div>
        <div><p className="text-xs" style={{ color: T.sub }}>Badge rating</p><p className="text-sm font-semibold" style={{ color: T.ink }}>4.6 / 5</p></div>
      </div>
      <div className="rounded-xl p-3.5 flex items-center gap-3" style={{ background: T.card, border: `1px solid ${T.line}` }}>
        <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: T.slateSoft }}><Mail size={16} color={T.slateMid} /></div>
        <div><p className="text-xs" style={{ color: T.sub }}>Account email</p><p className="text-sm font-semibold truncate" style={{ color: T.ink }}>{email}</p></div>
      </div>
    </div>
  );
}

function CatalogDealManager() {
  const [items, setItems] = useState([{ name: "Heritage walking tour", price: "899" }]);
  const [offers, setOffers] = useState([{ title: "10% off stays", discount: "10", until: "2026-12-31" }]);
  const [itemForm, setItemForm] = useState({ name: "", price: "" });
  const [offerForm, setOfferForm] = useState({ title: "", discount: "", until: "" });

  const addItem = () => {
    if (!itemForm.name || !itemForm.price) return;
    setItems((l) => [...l, itemForm]);
    setItemForm({ name: "", price: "" });
  };
  const addOffer = () => {
    if (!offerForm.title || !offerForm.discount) return;
    setOffers((l) => [...l, offerForm]);
    setOfferForm({ title: "", discount: "", until: "" });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
      <div className="rounded-2xl p-4" style={{ background: T.card, border: `1px solid ${T.line}` }}>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5" style={{ color: T.ink }}><LayoutList size={15} /> Catalog</h3>
        <div className="flex gap-2 mb-3">
          <input placeholder="Item name" className={inputClass} style={inputStyle} value={itemForm.name} onChange={(e) => setItemForm((f) => ({ ...f, name: e.target.value }))} />
          <input placeholder="₹ price" className={inputClass} style={{ ...inputStyle, width: 100 }} value={itemForm.price} onChange={(e) => setItemForm((f) => ({ ...f, price: e.target.value }))} />
          <button onClick={addItem} className="rounded-lg px-3 flex items-center justify-center shrink-0" style={{ background: T.slate, color: "#fff" }}><Plus size={15} /></button>
        </div>
        <div className="space-y-1.5">
          {items.map((it, i) => (
            <div key={i} className="flex items-center justify-between text-sm rounded-lg px-3 py-2" style={{ background: T.paper }}>
              <span style={{ color: T.ink }}>{it.name}</span>
              <div className="flex items-center gap-2">
                <span style={{ color: T.slateMid, fontWeight: 500 }}>₹{it.price}</span>
                <button onClick={() => setItems((l) => l.filter((_, x) => x !== i))}><Trash2 size={13} color={T.sub} /></button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl p-4" style={{ background: T.card, border: `1px solid ${T.line}` }}>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5" style={{ color: T.ink }}><Tag size={15} /> Promotional offers</h3>
        <div className="space-y-2 mb-3">
          <input placeholder="Offer title" className={inputClass} style={inputStyle} value={offerForm.title} onChange={(e) => setOfferForm((f) => ({ ...f, title: e.target.value }))} />
          <div className="flex gap-2">
            <input placeholder="Discount %" className={inputClass} style={inputStyle} value={offerForm.discount} onChange={(e) => setOfferForm((f) => ({ ...f, discount: e.target.value }))} />
            <input type="date" className={inputClass} style={inputStyle} value={offerForm.until} onChange={(e) => setOfferForm((f) => ({ ...f, until: e.target.value }))} />
          </div>
          <button onClick={addOffer} className="w-full text-xs font-medium rounded-lg py-2 flex items-center justify-center gap-1.5" style={{ background: T.forestTint, color: T.forestDark }}>
            <Plus size={13} /> Publish offer
          </button>
        </div>
        <div className="space-y-1.5">
          {offers.map((o, i) => (
            <div key={i} className="flex items-center justify-between text-sm rounded-lg px-3 py-2" style={{ background: T.amberTint }}>
              <span style={{ color: T.amberDark, fontWeight: 500 }}>{o.title}</span>
              <span className="text-xs" style={{ color: T.amberDark }}>{o.discount}% · until {o.until || "—"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MediaGallery() {
  const [images, setImages] = useState([]);
  const inputRef = useRef(null);

  const handleFiles = (files) => {
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => setImages((l) => [...l, { id: Math.random(), src: e.target.result }]);
      reader.readAsDataURL(file);
    });
  };

  return (
    <div className="rounded-2xl p-4 mb-6" style={{ background: T.card, border: `1px solid ${T.line}` }}>
      <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5" style={{ color: T.ink }}><ImagePlus size={15} /> Media gallery</h3>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); handleFiles(e.dataTransfer.files); }}
        className="rounded-xl py-6 flex flex-col items-center justify-center gap-1.5 cursor-pointer mb-3"
        style={{ border: `1.5px dashed ${T.line}`, background: T.paper }}
      >
        <input ref={inputRef} type="file" accept="image/*" multiple className="hidden" onChange={(e) => handleFiles(e.target.files)} />
        <ImagePlus size={20} color={T.sub} />
        <p className="text-sm font-medium" style={{ color: T.ink }}>Drop images, or click to browse</p>
        <p className="text-xs" style={{ color: T.sub }}>PNG or JPG</p>
      </div>
      {images.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2">
          {images.map((img) => (
            <div key={img.id} className="relative aspect-square rounded-lg overflow-hidden group">
              <img src={img.src} alt="" className="w-full h-full object-cover" />
              <button
                onClick={() => setImages((l) => l.filter((i) => i.id !== img.id))}
                className="absolute top-1 right-1 w-5 h-5 rounded-full flex items-center justify-center"
                style={{ background: "rgba(0,0,0,0.55)" }}
              >
                <X size={11} color="#fff" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ExpansionRequests() {
  const [locationReqs, setLocationReqs] = useState([{ type: "City", name: "Rishikesh", status: "Pending" }]);
  const [categoryReqs, setCategoryReqs] = useState([{ name: "Homestay", status: "Pending" }]);
  const [locForm, setLocForm] = useState({ type: "City", name: "" });
  const [catForm, setCatForm] = useState("");

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="rounded-2xl p-4" style={{ background: T.card, border: `1px solid ${T.line}` }}>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5" style={{ color: T.ink }}><MapPin size={15} /> Request a missing location</h3>
        <div className="flex gap-2 mb-3">
          <select className={inputClass} style={{ ...inputStyle, width: 100 }} value={locForm.type} onChange={(e) => setLocForm((f) => ({ ...f, type: e.target.value }))}>
            <option>City</option><option>District</option>
          </select>
          <input placeholder="Name" className={inputClass} style={inputStyle} value={locForm.name} onChange={(e) => setLocForm((f) => ({ ...f, name: e.target.value }))} />
          <button
            onClick={() => { if (!locForm.name) return; setLocationReqs((l) => [...l, { ...locForm, status: "Pending" }]); setLocForm({ type: "City", name: "" }); }}
            className="rounded-lg px-3 shrink-0" style={{ background: T.slate, color: "#fff" }}
          ><Plus size={15} /></button>
        </div>
        <div className="space-y-1.5">
          {locationReqs.map((r, i) => (
            <div key={i} className="flex items-center justify-between text-sm rounded-lg px-3 py-2" style={{ background: T.paper }}>
              <span style={{ color: T.ink }}>{r.type}: {r.name}</span>
              <StatusPill status={r.status} />
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl p-4" style={{ background: T.card, border: `1px solid ${T.line}` }}>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5" style={{ color: T.ink }}><FolderPlus size={15} /> Request a new category</h3>
        <div className="flex gap-2 mb-3">
          <input placeholder="Category name" className={inputClass} style={inputStyle} value={catForm} onChange={(e) => setCatForm(e.target.value)} />
          <button
            onClick={() => { if (!catForm) return; setCategoryReqs((l) => [...l, { name: catForm, status: "Pending" }]); setCatForm(""); }}
            className="rounded-lg px-3 shrink-0" style={{ background: T.slate, color: "#fff" }}
          ><Plus size={15} /></button>
        </div>
        <div className="space-y-1.5">
          {categoryReqs.map((r, i) => (
            <div key={i} className="flex items-center justify-between text-sm rounded-lg px-3 py-2" style={{ background: T.paper }}>
              <span style={{ color: T.ink }}>{r.name}</span>
              <StatusPill status={r.status} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function BusinessPortal() {
  const [session, setSession] = useState(null);
  if (!session) {
    return (
      <div>
        <H title="Business Portal" subtitle="Log in to manage your listing, or apply to join TourConnect." />
        <BusinessAuthGate onLogin={(email) => setSession({ email })} />
      </div>
    );
  }
  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 style={{ fontFamily: "Fraunces, serif", color: T.ink, fontWeight: 600 }} className="text-2xl mb-1.5">Green Leaf Resorts</h1>
          <Trail />
        </div>
        <button onClick={() => setSession(null)} className="text-xs font-medium rounded-lg px-3 py-2" style={{ background: T.paper, color: T.sub }}>Log out</button>
      </div>
      <MetricsBar email={session.email} />
      <CatalogDealManager />
      <MediaGallery />
      <ExpansionRequests />
    </div>
  );
}

/* =======================================================================
   2. ADMIN PANEL
======================================================================= */

function AdminAuthGate({ onLogin }) {
  const [tab, setTab] = useState("login");
  return (
    <div>
      <AuthTabs tabs={[{ key: "login", label: "🔐 Admin Login" }]} active={tab} setActive={setTab} />
      <LoginForm role="admin" onLogin={onLogin} />
    </div>
  );
}

const INITIAL_APPROVALS = [
  { id: 1, name: "Riverside Homestay", owner: "N. Verma", category: "Hotel", location: "Rishikesh" },
  { id: 2, name: "Desert Trails Tours", owner: "K. Singh", category: "Travel Agency", location: "Jaipur" },
];

function ApprovalsQueue() {
  const [queue, setQueue] = useState(INITIAL_APPROVALS);
  const [decided, setDecided] = useState([]);
  const decide = (id, status) => {
    const item = queue.find((q) => q.id === id);
    setQueue((q) => q.filter((x) => x.id !== id));
    setDecided((d) => [{ ...item, status }, ...d]);
  };
  return (
    <div className="mb-8">
      <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5" style={{ color: T.ink }}><Building2 size={15} /> Business approvals queue</h3>
      <div className="space-y-2.5">
        {queue.length === 0 && <p className="text-xs" style={{ color: T.sub }}>Queue is clear.</p>}
        {queue.map((b) => (
          <div key={b.id} className="rounded-xl p-3.5 flex items-center justify-between flex-wrap gap-2" style={{ background: T.card, border: `1px solid ${T.line}` }}>
            <div>
              <p className="text-sm font-medium" style={{ color: T.ink }}>{b.name}</p>
              <p className="text-xs" style={{ color: T.sub }}>{b.owner} · {b.category} · {b.location}</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => decide(b.id, "Approved")} className="text-xs font-medium rounded-lg px-3 py-1.5" style={{ background: T.forestTint, color: T.forestDark }}>✅ Approve</button>
              <button onClick={() => decide(b.id, "Rejected")} className="text-xs font-medium rounded-lg px-3 py-1.5" style={{ background: T.roseTint, color: "#A33232" }}>❌ Reject</button>
            </div>
          </div>
        ))}
      </div>
      {decided.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {decided.map((d, i) => (
            <div key={i} className="flex items-center justify-between text-xs rounded-lg px-3 py-2" style={{ background: T.paper }}>
              <span style={{ color: T.sub }}>{d.name}</span>
              <StatusPill status={d.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const INITIAL_SUBMISSIONS = [
  { id: 1, tourist: "R. Sharma", activity: "Tree Plantation", verdict: "Genuine", confidence: 92, reasoning: "Continuous, unedited footage consistent with the claimed activity; natural hand movement and matching tools.", aiPoints: 50 },
  { id: 2, tourist: "A. Kapoor", activity: "Waste Cleanup", verdict: "Uncertain", confidence: 48, reasoning: "Lighting and framing are consistent, but only one frame clearly shows the activity — recommend manual review.", aiPoints: 10 },
];

function EcoReviewCard({ s, onDecide }) {
  const [points, setPoints] = useState(s.aiPoints);
  const verdictStyle = {
    Genuine: { bg: T.forestTint, fg: T.forestDark, Icon: CheckCircle2 },
    Fake: { bg: T.roseTint, fg: "#A33232", Icon: XCircle },
    Uncertain: { bg: T.slateSoft, fg: T.slateMid, Icon: ShieldAlert },
  }[s.verdict];

  return (
    <div className="rounded-2xl p-4 grid grid-cols-1 md:grid-cols-[160px_1fr] gap-4" style={{ background: T.card, border: `1px solid ${T.line}` }}>
      <div className="rounded-xl aspect-video md:aspect-square flex items-center justify-center" style={{ background: T.slate }}>
        <Play size={22} color="#fff" fill="#fff" />
      </div>
      <div>
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            <p className="text-sm font-medium" style={{ color: T.ink }}>{s.activity}</p>
            <p className="text-xs" style={{ color: T.sub }}>{s.tourist}</p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium" style={{ background: verdictStyle.bg, color: verdictStyle.fg }}>
            <verdictStyle.Icon size={12} /> {s.verdict} · {s.confidence}%
          </span>
        </div>
        <div className="rounded-lg p-3 text-xs leading-relaxed mb-3" style={{ background: T.paper, color: T.sub }}>
          <span className="inline-flex items-center gap-1 font-medium mb-1" style={{ color: T.ink }}><Sparkles size={11} color={T.amber} /> AI reasoning</span>
          <p>{s.reasoning}</p>
        </div>
        <div className="flex items-center flex-wrap gap-3">
          <label className="flex items-center gap-2 text-xs" style={{ color: T.sub }}>
            <Coins size={13} color={T.amber} /> Points to award
            <input
              type="number" value={points} onChange={(e) => setPoints(Number(e.target.value))}
              className="w-20 text-sm rounded-lg px-2 py-1.5 outline-none" style={inputStyle}
            />
          </label>
          <div className="flex items-center gap-2 ml-auto">
            <button onClick={() => onDecide(s.id, "Approved", points)} className="text-xs font-medium rounded-lg px-3 py-1.5" style={{ background: T.forestTint, color: T.forestDark }}>✅ Approve</button>
            <button onClick={() => onDecide(s.id, "Rejected", 0)} className="text-xs font-medium rounded-lg px-3 py-1.5" style={{ background: T.roseTint, color: "#A33232" }}>❌ Reject</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function EcoReviewQueue() {
  const [queue, setQueue] = useState(INITIAL_SUBMISSIONS);
  const [decided, setDecided] = useState([]);
  const decide = (id, status, points) => {
    const item = queue.find((q) => q.id === id);
    setQueue((q) => q.filter((x) => x.id !== id));
    setDecided((d) => [{ ...item, status, points }, ...d]);
  };
  return (
    <div className="mb-8">
      <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5" style={{ color: T.ink }}><Sparkles size={15} color={T.amber} /> AI eco-action review queue</h3>
      <div className="space-y-3">
        {queue.length === 0 && <p className="text-xs" style={{ color: T.sub }}>Queue is clear.</p>}
        {queue.map((s) => <EcoReviewCard key={s.id} s={s} onDecide={decide} />)}
      </div>
      {decided.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {decided.map((d, i) => (
            <div key={i} className="flex items-center justify-between text-xs rounded-lg px-3 py-2" style={{ background: T.paper }}>
              <span style={{ color: T.sub }}>{d.tourist} · {d.activity}</span>
              <div className="flex items-center gap-2">
                {d.status === "Approved" && <span className="flex items-center gap-1" style={{ color: T.amberDark }}><Coins size={12} /> {d.points} pts</span>}
                <StatusPill status={d.status} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SystemRequests() {
  const [locations, setLocations] = useState([{ id: 1, type: "City", name: "Rishikesh", from: "Riverside Homestay" }]);
  const [categories, setCategories] = useState([{ id: 1, name: "Homestay", from: "Riverside Homestay" }]);

  const decideLoc = (id, status) => setLocations((l) => l.map((x) => x.id === id ? { ...x, status } : x).filter((x) => !x.status || x.status === status));
  const decideCat = (id, status) => setCategories((l) => l.map((x) => x.id === id ? { ...x, status } : x).filter((x) => !x.status || x.status === status));

  return (
    <div>
      <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5" style={{ color: T.ink }}><MapPin size={15} /> System expansion requests</h3>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-2.5">
          {locations.map((r) => (
            <div key={r.id} className="rounded-xl p-3.5 flex items-center justify-between" style={{ background: T.card, border: `1px solid ${T.line}` }}>
              <div>
                <p className="text-sm font-medium" style={{ color: T.ink }}>{r.type}: {r.name}</p>
                <p className="text-xs" style={{ color: T.sub }}>Requested by {r.from}</p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => decideLoc(r.id, "Approved")} className="text-xs font-medium rounded-lg px-2.5 py-1.5" style={{ background: T.forestTint, color: T.forestDark }}>Approve</button>
                <button onClick={() => decideLoc(r.id, "Rejected")} className="text-xs font-medium rounded-lg px-2.5 py-1.5" style={{ background: T.roseTint, color: "#A33232" }}>Reject</button>
              </div>
            </div>
          ))}
          {locations.length === 0 && <p className="text-xs" style={{ color: T.sub }}>No pending location requests.</p>}
        </div>
        <div className="space-y-2.5">
          {categories.map((r) => (
            <div key={r.id} className="rounded-xl p-3.5 flex items-center justify-between" style={{ background: T.card, border: `1px solid ${T.line}` }}>
              <div>
                <p className="text-sm font-medium" style={{ color: T.ink }}>{r.name}</p>
                <p className="text-xs" style={{ color: T.sub }}>Requested by {r.from}</p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => decideCat(r.id, "Approved")} className="text-xs font-medium rounded-lg px-2.5 py-1.5" style={{ background: T.forestTint, color: T.forestDark }}>Approve</button>
                <button onClick={() => decideCat(r.id, "Rejected")} className="text-xs font-medium rounded-lg px-2.5 py-1.5" style={{ background: T.roseTint, color: "#A33232" }}>Reject</button>
              </div>
            </div>
          ))}
          {categories.length === 0 && <p className="text-xs" style={{ color: T.sub }}>No pending category requests.</p>}
        </div>
      </div>
    </div>
  );
}

function AdminPanel() {
  const [session, setSession] = useState(null);
  if (!session) {
    return (
      <div>
        <H title="Admin Panel" subtitle="Sign in to review approvals and eco-action submissions." />
        <AdminAuthGate onLogin={(email) => setSession({ email })} />
      </div>
    );
  }
  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div><H title="Admin Panel" subtitle={`Signed in as ${session.email}`} /></div>
        <button onClick={() => setSession(null)} className="text-xs font-medium rounded-lg px-3 py-2 h-fit" style={{ background: T.paper, color: T.sub }}>Log out</button>
      </div>
      <ApprovalsQueue />
      <EcoReviewQueue />
      <SystemRequests />
    </div>
  );
}

/* =======================================================================
   APP SHELL
======================================================================= */

export default function TourConnectManagement() {
  const [tab, setTab] = useState("business");
  return (
    <div style={{ background: T.paper, fontFamily: "Inter, sans-serif", minHeight: "100vh" }}>
      <style>{fontImport}</style>
      <div className="flex items-center gap-2 px-4 md:px-8 pt-6 pb-2">
        {[{ k: "business", l: "🏢 Business Portal" }, { k: "admin", l: "👨‍💼 Admin Panel" }].map((t) => (
          <button
            key={t.k}
            onClick={() => setTab(t.k)}
            className="text-sm font-medium rounded-full px-4 py-2"
            style={{ background: tab === t.k ? T.slate : T.card, color: tab === t.k ? "#fff" : T.sub, border: `1px solid ${tab === t.k ? T.slate : T.line}` }}
          >
            {t.l}
          </button>
        ))}
      </div>
      <div className="px-4 py-4 md:px-8 md:py-6 max-w-6xl">
        {tab === "business" ? <BusinessPortal /> : <AdminPanel />}
      </div>
    </div>
  ); #
}
