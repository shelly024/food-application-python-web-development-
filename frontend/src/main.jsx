import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./styles.css";

const money = (value) => `\u00a3${Number(value).toFixed(2)}`;

function App() {
  const [stores, setStores] = useState([]);
  const [activeStore, setActiveStore] = useState(null);
  const [foodCache, setFoodCache] = useState({});
  const [cart, setCart] = useState({});
  const [authOpen, setAuthOpen] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [checkout, setCheckout] = useState(null);
  const [user, setUser] = useState(null);  //no need to save user in localstorage
  /*() => {
    const saved = localStorage.getItem("delivery_user");
    return saved ? JSON.parse(saved) : null;
  }*/

  useEffect(() => {
    api.stores().then(setStores).catch(console.error);
  }, []);

  const cartItems = useMemo(() => {
    return Object.entries(cart)
      .map(([id, quantity]) => ({ ...foodCache[Number(id)], quantity }))
      .filter((item) => item.id);
  }, [cart, foodCache]);

  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);
  const subtotal = cartItems.reduce((sum, item) => sum + item.quantity * item.price, 0);

  const openStore = async (store) => {
    const detail = await api.store(store.id);
    setFoodCache((current) => ({
      ...current,
      ...Object.fromEntries(detail.foods.map((food) => [food.id, food])),
    })); //need a filter to avoid repeat?  no need
    setActiveStore(detail);
    setCheckout(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const updateCart = (food, delta) => {
    setCart((current) => {
      const nextQuantity = (current[food.id] || 0) + delta;
      const next = { ...current };
      if (nextQuantity <= 0) delete next[food.id];
      else next[food.id] = nextQuantity;
      return next;
    });
  };

  const handleAuth = ({ user: nextUser, token }) => {
    //localStorage.setItem("delivery_user", JSON.stringify(nextUser)); //it saved per login or update?
    localStorage.setItem("delivery_token", token);
    setUser(nextUser);
    setAuthOpen(false);
  };

  const placeOrder = async () => {
    if (!user) {
      setAuthOpen(true);
      return;
    }
    const items = cartItems.map((item) => ({ food_id: item.id, quantity: item.quantity }));
    const order = await api.createOrder(items);
    setCheckout(order);
    setCartOpen(false);
  };

  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={() => setActiveStore(null)}>
          <span className="brand-mark">C</span>
          Courier Kitchen
        </button>
        <div className="top-actions">
          <span className="location">London</span>
          {user ? (
            <button className="quiet-button">{user.name}</button>
          ) : (
            <button className="quiet-button" onClick={() => setAuthOpen(true)}>Log in/Register</button>
          )}
          <button className="cart-button" onClick={() => setCartOpen(true)}>
            Basket <span>{cartCount}</span>
          </button>
        </div>
      </header>

      <main>
        {checkout ? (
          <PaymentPlaceholder order={checkout} onBack={() => setCheckout(null)} />  //back just cancel this page and auto to last page
        ) : activeStore ? (
          <StoreDetail store={activeStore} cart={cart} onBack={() => setActiveStore(null)} onAdd={updateCart} />
        ) : (
          <Home stores={stores} onOpenStore={openStore} />
        )}
      </main>

      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} onAuth={handleAuth} />}
      {cartOpen && (
        <CartDrawer
          items={cartItems}
          subtotal={subtotal}
          onClose={() => setCartOpen(false)}
          onChange={updateCart}
          onCheckout={placeOrder}
        />
      )}
    </>
  );
}

function Home({ stores, onOpenStore }) {
  const [query,SetQuery] = useState('')
  const [response, SetResponse] = useState([])
  const [loading,SetLoading] = useState(false)
  async function handleSearch(e){
    e.preventDefault()
    SetLoading(true)
    try{
      const result = await api.recommendations({user_input:query})
      SetResponse(result) //how to handle error？
    }
    finally{
      SetLoading(false)
    }

  }

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p>Premium delivery, without the wait</p>
          <h1>Restaurant food that feels close to the table.</h1>
          <div className="search-pill">
            <span>Search dishes, cuisines, or restaurants</span>
            <button>Explore</button>
          </div>
        </div>
      </section>
      <section className="AI-search">
        <div className="section-search">
          <h2>AI Search</h2>
          <div className="section-search-row">
            <input
              type="text"
              placeholder="what do you want right now? you can type here."
              value={query}
              onChange={(e) => SetQuery(e.target.value)}
            />
            <button onClick={handleSearch} disabled={loading}>{loading ? "Loading...":"Search"}</button>
          </div>
        </div>
        <div className="recommendation-card">
          {response.map((store) => (
              <div className="response-card" key={store.store_id}>
                <button className="store-info" onClick={() => onOpenStore({id:store.store_id})}> {/*构建对象包含一个id的字段*/}
                  <img src={store.store_image}/>
                  <h2>{store.store_name}</h2>
                  <p>{store.store_recommend_reason}</p>
                  <p>rating:{store.rating}</p>
                  <p>delivery time:{store.delivery_minute}</p>
                </button>

                {store.foodlist && store.foodlist.length > 0 && (
                    <div className="foodlist">
                      {store.foodlist.map((food) => (
                          <div className="food-info" key={food.food_id}>
                            <img src={food.food_image}/>
                            <h3>{food.food_name}</h3>
                            <p>{food.food_recommend_reason}</p>
                            <p>price:{food.food_price}</p>
                          </div>
                      ))}
                    </div>
                )}
              </div>
          ))}
        </div>
      </section>
      <section className="content-band">
        <div className="section-heading">
          <div>
            <p>Selected for tonight</p>
            <h2>Top restaurants near you</h2>
          </div>
          <button className="text-button">Sort by rating</button>
        </div>
        <div className="store-grid">
          {stores.map((store) => (
            <button className="store-card" key={store.id} onClick={() => onOpenStore(store)}>
              <img src={store.hero_image} alt={store.name} />
              <span className="store-badge">{store.delivery_minutes} min</span>
              <div className="store-card-copy">
                <h3>{store.name}</h3>
                <p>{store.cuisine} / {money(store.delivery_fee)} delivery / {money(store.minimum_order)} min</p>
                <strong>{store.rating.toFixed(1)}</strong>
              </div>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

function StoreDetail({ store, cart, onBack, onAdd }) {
  const categories = [...new Set(store.foods.map((food) => food.category))];

  return (
    <>
      <section className="store-hero" style={{ backgroundImage: `url(${store.hero_image})` }}>
        <button className="back-button" onClick={onBack}>Back</button>
      </section>
      <section className="store-shell">
        <div className="store-title">
          <div>
            <p>{store.cuisine} / {store.delivery_minutes} min / {money(store.delivery_fee)} delivery</p>
            <h1>{store.name}</h1>
            <span>{store.description}</span>
          </div>
          <strong>{store.rating.toFixed(1)}</strong>
        </div>

        {categories.map((category) => (
          <div className="menu-section" key={category}>
            <h2>{category}</h2>
            <div className="menu-grid">
              {store.foods.filter((food) => food.category === category).map((food) => (
                <article className="food-card" key={food.id}>
                  <div>
                    {food.popular ? <span className="popular">Popular</span> : null}
                    <h3>{food.name}</h3>
                    <p>{food.description}</p>
                    <strong>{money(food.price)}</strong>
                  </div>
                  <div className="food-image">
                    <img src={food.image} alt={food.name} />
                    <button onClick={() => onAdd(food, 1)}>
                      {cart[food.id] ? `Add / ${cart[food.id]}` : "Add"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        ))}
      </section>
    </>
  );
}

function CartDrawer({ items, subtotal, onClose, onChange, onCheckout }) {
  const serviceFee = items.length ? 1.2 : 0;
  const total = subtotal + serviceFee;

  return (
    <div className="overlay">
      <aside className="drawer">
        <div className="drawer-head">
          <div>
            <p>Your order</p>
            <h2>Basket</h2>
          </div>
          <button className="icon-button" onClick={onClose}>x</button>
        </div>

        {items.length ? (
          <>
            <div className="cart-list">
              {items.map((item) => (
                <div className="cart-row" key={item.id}>
                  <img src={item.image} alt={item.name} />
                  <div>
                    <strong>{item.name}</strong>
                    <span>{money(item.price)}</span>
                  </div>
                  <div className="stepper">
                    <button onClick={() => onChange(item, -1)}>-</button>
                    <span>{item.quantity}</span>
                    <button onClick={() => onChange(item, 1)}>+</button>
                  </div>
                </div>
              ))}
            </div>
            <div className="totals">
              <span>Subtotal <strong>{money(subtotal)}</strong></span>
              <span>Service <strong>{money(serviceFee)}</strong></span>
              <span>Total <strong>{money(total)}</strong></span>
            </div>
            <button className="checkout-button" onClick={onCheckout}>Go to checkout</button>
          </>
        ) : (
          <div className="empty-cart">
            <h3>Your basket is empty</h3>
            <p>Add something delicious and it will appear here.</p>
          </div>
        )}
      </aside>
    </div>
  );
}

function AuthModal({ onClose, onAuth }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      const payload = mode === "login" ? { email: form.email, password: form.password } : form;
      const result = mode === "login" ? await api.login(payload) : await api.register(payload);
      onAuth(result); //it need create new Error for http exception
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="overlay">
      <form className="auth-modal" onSubmit={submit}>
        <button type="button" className="icon-button close-auth" onClick={onClose}>x</button>
        <p>Welcome to Courier Kitchen</p>
        <h2>{mode === "login" ? "Log in" : "Create account"}</h2>
        <div className="segment">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Log in</button>
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Register</button>
        </div>
        {mode === "register" && (
          <label>
            Name
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
        )}
        <label>
          Email
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        </label>
        <label>
          Password {/*password directly saved in form*/}
          <input type="password" minLength="6" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
        </label>
        {error && <span className="form-error">{error}</span>}
        <button className="checkout-button" type="submit">{mode === "login" ? "Log in" : "Create account"}</button>
      </form>
    </div>
  );
}

function PaymentPlaceholder({ order, onBack }) {
  return (
    <section className="payment-page">
      <div className="payment-panel">
        <span>Order #{order.order_id}</span>
        <h1>Payment is ready to connect.</h1>
        <p>Your order has been created with a pending payment status. The next step can be Stripe, PayPal, or a mock payment sandbox.</p>
        <strong>{money(order.total)}</strong>
        <button className="checkout-button" onClick={onBack}>Back to restaurants</button>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);


//except back button, when click web back arrow it will guide back to google