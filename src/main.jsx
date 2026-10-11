import React,{useMemo,useState,useEffect} from "react";
import {createRoot} from "react-dom/client";
import {
  LayoutDashboard,ShoppingCart,Package,Boxes,Truck,ReceiptText,ShieldCheck,
  BrainCircuit,Bell,Settings,Search,Plus,CheckCircle2,AlertTriangle,
  Wifi,ChevronRight,X,ArrowUpRight,TrendingUp,Store,RefreshCw
} from "lucide-react";
import "./styles.css";


const API_BASE = "https://dream.tail716452.ts.net";
 
async function api(path, options = {}) { 
  const response = await fetch(`${API_BASE}${path}`, { 
    headers: { 
      "Content-Type": "application/json", 
      ...(options.headers || {}) 
    }, 
    ...options, 
  }); 
 
  let data = null; 
 
  try { 
    data = await response.json(); 
  } catch {} 
 
  if (!response.ok) { 
    const detail = Array.isArray(data?.detail) 
      ? data.detail.map(err => {
          const field = Array.isArray(err.loc)
            ? err.loc[err.loc.length - 1]
            : "unknown";

          return `${field}: ${err.msg}`;
        }).join(", ") 
      : data?.detail || data?.message || `HTTP ${response.status}`; 
 
    console.error("API ERROR:", data); 
 
    throw new Error(detail); 
  } 
 
  return data; 
}



const seedProducts=[
 {id:"P001",name:"Amul Milk",category:"Dairy",price:60,cost:52,weight:"1 kg",stock:20,min:5,supplier:"Amul Distributor",rfid:"RFID12345"},
 {id:"P002",name:"Brown Bread",category:"Bakery",price:45,cost:32,weight:"400 g",stock:7,min:10,supplier:"Fresh Foods",rfid:"RFID12346"},
 {id:"P003",name:"Shampoo",category:"Personal Care",price:180,cost:145,weight:"180 ml",stock:8,min:5,supplier:"Care Supplies",rfid:"RFID12347"},
 {id:"P004",name:"Bath Soap",category:"Personal Care",price:55,cost:40,weight:"100 g",stock:2,min:5,supplier:"Care Supplies",rfid:"RFID12348"},
 {id:"P005",name:"Basmati Rice",category:"Grocery",price:80,cost:68,weight:"1 kg",stock:32,min:8,supplier:"Grain Hub",rfid:"RFID12349"},
 {id:"P006",name:"Orange Juice",category:"Beverages",price:110,cost:86,weight:"1 L",stock:14,min:6,supplier:"Fresh Beverages",rfid:"RFID12350"}
];
const seedCarts=[
 {id:"Cart 01",state:"Shopping",items:4,total:560},
 {id:"Cart 02",state:"Available",items:0,total:0},
 {id:"Cart 03",state:"Alert",items:5,total:890,alert:"Weight mismatch"},
 {id:"Cart 04",state:"Shopping",items:7,total:920},
 {id:"Cart 05",state:"Shopping",items:2,total:210}
];
const seedOrders=[
 {id:"#ORD-401",supplier:"Amul Distributor",product:"Amul Milk",qty:50,received:0,status:"Pending",date:"03 Sep 2026"},
 {id:"#ORD-400",supplier:"Care Supplies",product:"Shampoo",qty:30,received:30,status:"Received",date:"02 Sep 2026"},
 {id:"#ORD-399",supplier:"Fresh Foods",product:"Brown Bread",qty:20,received:10,status:"Partially Received",date:"01 Sep 2026"}
];

const nav=[
  ["Dashboard",LayoutDashboard],
  ["Customer Trolley",ShoppingCart],
  ["Live Store",ShoppingCart],
  ["Products",Package],
  ["Inventory",Boxes],
  ["Stock Orders",Truck],
  ["Transactions",ReceiptText],
  ["Retail Guardian",ShieldCheck],
  ["AI Insights",BrainCircuit],
  ["Shopper Analytics",TrendingUp],
  ["Notifications",Bell],
  ["Settings",Settings]
];
const money=n=>"₹"+Number(n||0).toLocaleString("en-IN");

function App(){ 

  const [page,setPage]=useState("Dashboard");

  // =====================================================
  // GLOBAL STORE SETTINGS
  // =====================================================

  const [storeName, setStoreName] = useState(
    localStorage.getItem("smart-retail-store-name") ||
    "Smart Retail Store 01"
  );

  const [storeId, setStoreId] = useState(
    localStorage.getItem("smart-retail-store-id") ||
    "STORE-01"
  );

  const [currency, setCurrency] = useState(
    localStorage.getItem("smart-retail-currency") ||
    "INR"
  );
  // =====================================================
// LOCAL EDGE SERVER STATUS
// =====================================================

const [edgeStatus, setEdgeStatus] = useState("checking");
const [showEdgeDetails, setShowEdgeDetails] = useState(false);

const [systemStatus, setSystemStatus] = useState({
  fastapi: "checking",
  mqtt: "checking",
  database: "checking"
});

useEffect(() => {

  const checkEdgeServer = async () => {

    try {

      const response = await fetch(
        `${API_BASE}/health`
      );

      if (!response.ok) {
        throw new Error("Edge server unavailable");
      }

      const data = await response.json();

      if (data.status === "healthy") {
        setEdgeStatus("connected");
      } else {
        setEdgeStatus("offline");
      }

    } catch (error) {

      console.error(
        "Edge server health check failed:",
        error
      );

      setEdgeStatus("offline");

    }

  };

  // Check immediately
  checkEdgeServer();

  // Check every 5 seconds
  const interval = setInterval(
    checkEdgeServer,
    5000
  );

  return () => {
    clearInterval(interval);
  };

}, []);

// =====================================================
// CHECK FASTAPI + MQTT + DATABASE STATUS
// =====================================================

useEffect(() => {

  const checkSystemStatus = async () => {

    try {

      const response = await fetch(
        `${API_BASE}/system-status`
      );

      if (!response.ok) {
        throw new Error(
          "System status unavailable"
        );
      }

      const data = await response.json();

      console.log("SYSTEM STATUS:", data);

      setSystemStatus({
        fastapi: data.fastapi || "offline",
        mqtt: data.mqtt || "offline",
        database: data.database || "offline"
      });

    } catch (error) {

      console.error(
        "System status check failed:",
        error
      );

      setSystemStatus({
        fastapi: "offline",
        mqtt: "offline",
        database: "offline"
      });

    }

  };

  // Check immediately
  checkSystemStatus();

  // Check every 5 seconds
  const interval = setInterval(
    checkSystemStatus,
    5000
  );

  return () => {
    clearInterval(interval);
  };

}, []);

  // Keep App UI synchronized with Settings page changes
  useEffect(() => {

    const syncStoreSettings = () => {

      setStoreName(
        localStorage.getItem("smart-retail-store-name") ||
        "Smart Retail Store 01"
      );

      setStoreId(
        localStorage.getItem("smart-retail-store-id") ||
        "STORE-01"
      );

      setCurrency(
        localStorage.getItem("smart-retail-currency") ||
        "INR"
      );

    };

    window.addEventListener(
      "smart-retail-settings-changed",
      syncStoreSettings
    );

    return () => {
      window.removeEventListener(
        "smart-retail-settings-changed",
        syncStoreSettings
      );
    };

  }, []); 

  const [products,setProducts]=useState(seedProducts);

  // Notification read state
  const [notificationsRead,setNotificationsRead] = useState(() => {
    return localStorage.getItem("smart-retail-notifications-read") === "true";
  });
 const [transactions, setTransactions] = useState([]);
 
 useEffect(() => {
  const loadProducts = async () => {
    try {
      const response = await fetch(`${API_BASE}/products`);

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();

      setProducts(data.products || data);
      console.log("Products loaded from FastAPI:", data);
    } catch (error) {
      console.error("Products load error:", error);
    }
  };

  loadProducts();
}, []);
// Load Transactions from FastAPI
// Load Transactions from FastAPI
useEffect(() => {
  const loadTransactions = async () => {
    try {
      const response = await fetch(`${API_BASE}/transactions`);

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();

      const formattedTransactions = data.map(t => ({
        id: t.id,
        cart: t.trolley_number || "Unknown Cart",
        items: Number(t.items) || 0,
        total: Number(t.total_amount) || 0,
        time: t.created_at
          ? new Date(t.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit"
            })
          : "-",
        status: t.payment_status
      }));

      setTransactions(formattedTransactions);

      console.log(
        "Transactions loaded from FastAPI:",
        formattedTransactions
      );
    } catch (error) {
      console.error("Transactions load error:", error);
    }
  };

  loadTransactions();
}, []);
 // Load Stock Orders from FastAPI

useEffect(() => {
  const loadOrders = async () => {
    try {
      const response = await fetch(`${API_BASE}/stock-orders`);

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();

      const formattedOrders = data.map(order => {
        const item = order.stock_order_items?.[0];

        return {
          id: order.id,
          itemId: item?.id,
          productId: item?.product_id,
          supplier: order.supplier,
          product: item?.products?.name || "Unknown Product",
          qty: item?.quantity_ordered || 0,
          received: item?.quantity_received || 0,
          status:
            order.status === "received"
              ? "Received"
              : order.status === "partially_received"
              ? "Partially Received"
              : "Pending",
          date: order.order_date
            ? new Date(order.order_date).toLocaleDateString("en-GB")
            : "-"
        };
      });

      setOrders(formattedOrders);

      console.log("Formatted Orders from FastAPI:", formattedOrders);
    } catch (error) {
      console.error("Orders load error:", error);
    }
  };

  loadOrders();
}, []);


useEffect(() => {
  const loadMovements = async () => {
    try {
      const data = await api("/inventory-movements");
      setMovements(data || []);
    } catch (error) {
      console.error("Inventory movements load error:", error);
    }
  };
  loadMovements();
}, []);

 
 const [orders,setOrders]=useState(seedOrders);
 const [movements, setMovements] = useState([]);
 const [query,setQuery]=useState("");
 const [modal,setModal]=useState(null);
 const [editingProduct,setEditingProduct]=useState(null);
 const [toast,setToast]=useState("");
const low=products.filter(p=>p.current_stock>0&&p.current_stock<=p.minimum_stock);;
 const out=products.filter(p=>p.current_stock===0);
 const filtered=useMemo(()=>products.filter(p=>(p.name+p.id+p.category+p.rfid).toLowerCase().includes(query.toLowerCase())),[products,query]);
const notify=m=>{setToast(m);setTimeout(()=>setToast(""),2200)};
const markNotificationsRead = () => {

  setNotificationsRead(true);

  localStorage.setItem(
    "smart-retail-notifications-read",
    "true"
  );

};

const removeProduct = async (id) => {
  try {
    await api(`/products/${id}`, { method: "DELETE" });
    setProducts(current => current.filter(p => p.id !== id));
    notify("Product removed successfully");
  } catch (error) {
    console.error("Remove product error:", error);
    notify("Failed to remove product");
  }
};
const updateProduct = async (e) => {
  e.preventDefault();

  const f = new FormData(e.currentTarget);

  const updatedProduct = {
    name: f.get("name"),
    category: f.get("category"),
    price: Number(f.get("price")),
    purchase_price: Number(f.get("cost")),
    unit_weight: Number(f.get("weight")) || 0,
    current_stock: Number(f.get("stock")) || 0,
    minimum_stock: Number(f.get("min")) || 0,
    supplier: f.get("supplier"),
    rfid_tag: f.get("rfid") || null,
  };

  let data;
  try {
    data = await api(`/products/${editingProduct.id}`, {
      method: "PUT",
      body: JSON.stringify(updatedProduct)
    });
  } catch (error) {
    console.error("Update product error:", error);
    notify("Failed to update product");
    return;
  }

  setProducts(current => current.map(p => p.id === data.id ? data : p));
  setEditingProduct(null);
  setModal(null);
  notify("Product updated successfully");
};
 const addProduct = async (e) => {
  e.preventDefault();

  const f = new FormData(e.currentTarget);

  const product = {
    name: f.get("name"),
    category: f.get("category"),
    price: Number(f.get("price")),
    purchase_price: Number(f.get("cost")),
    unit_weight: Number(f.get("weight")) || 0,
    current_stock: Number(f.get("stock")) || 0,
    minimum_stock: Number(f.get("min")) || 0,
    supplier: f.get("supplier"),
    rfid_tag: f.get("rfid") || null,
  };

  let data;
  try {
    data = await api("/products", { method: "POST", body: JSON.stringify( product ) });
  } catch (error) {
    console.error("Add product error:", error);
    notify("Failed to add product");
    alert(error.message || "Failed to add product");
    return;
  }

  setProducts(current => [data, ...current]);
  setModal(null);
  notify("Product added successfully");
};
 const createOrder = async (e) => {
  e.preventDefault();
  const f = new FormData(e.currentTarget);
  const productName = f.get("product");
  const supplier = f.get("supplier");
  const quantity = Number(f.get("qty"));
  const expectedDate = f.get("arrival") || null;
  const product = products.find(p => p.name === productName);
  if (!product) { notify("Product not found"); return; }

  try {
    const result = await api("/stock-orders", {
      method: "POST",
      body: JSON.stringify({ supplier, expected_date: expectedDate })
    });
    const order = result.order;
    await api("/stock-order-items", {
      method: "POST",
      body: JSON.stringify({
        order_id: order.id,
        product_id: product.id,
        quantity_ordered: quantity,
        purchase_price: Number(product.purchase_price ?? product.cost ?? 0)
      })
    });
    setOrders(x => [{
      id: order.id, supplier, product: productName, qty: quantity,
      received: 0, status: "pending", date: expectedDate || "—"
    }, ...x]);
    setModal(null);
    notify("New stock order created");
  } catch (error) {
    console.error("Create order error:", error);
    notify("Failed to create order");
  }
};
const [receivingOrder, setReceivingOrder] = useState(null);

const receiveOrder = (i) => {
  setReceivingOrder(orders[i]);
  setModal("receive");
};
const receiveStock = async (e) => {
  e.preventDefault();
  const f = new FormData(e.currentTarget);
  const receivedNow = Number(f.get("received")) || 0;
  if (!receivingOrder) return;
  const ordered = Number(receivingOrder.qty) || 0;
  const alreadyReceived = Number(receivingOrder.received) || 0;
  const remaining = Math.max(0, ordered - alreadyReceived);
  if (receivedNow <= 0) { notify("Enter a valid received quantity"); return; }
  if (receivedNow > remaining) { notify(`Only ${remaining} units are remaining`); return; }

  try {
    const result = await api("/receive-stock", {
      method: "POST",
      body: JSON.stringify({ order_item_id: receivingOrder.itemId, quantity_received: receivedNow })
    });
    const newReceived = Number(result.item.quantity_received) || alreadyReceived + receivedNow;
    const newStatus = result.order.status;
    const product = products.find(p => p.id === receivingOrder.productId);
    if (product) {
      setProducts(current => current.map(p => p.id === product.id ? {...p, current_stock: Number(p.current_stock || 0) + receivedNow} : p));
    }
    setOrders(current => current.map(o => o.id === receivingOrder.id ? {...o, received: newReceived, status: newStatus} : o));
    setReceivingOrder(null);
    setModal(null);
    notify(`${receivingOrder.product}: ${receivedNow} units received`);
  } catch (error) {
    console.error("Receive stock error:", error);
    notify(error.message || "Failed to receive stock");
  }
};
const checkoutCart = async (trolleyNumber) => {
  try {
    const trolleys = await api("/trolleys");
    const trolleyList = trolleys.trolleys || trolleys;
    const trolley = trolleyList.find(t => t.trolley_number === trolleyNumber);
    if (!trolley) { notify("Trolley not found"); return; }
    const result = await api("/checkout", {
      method: "POST",
      body: JSON.stringify({ trolley_id: trolley.id, payment_status: "paid" })
    });
    if (result.status !== "success") { notify(result.message || "Checkout failed"); return; }
    const [productData, transactionData, movementData] = await Promise.all([
      api("/products"), api("/transactions"), api("/inventory-movements")
    ]);
    setProducts(productData.products || productData);
    setMovements(movementData || []);
    const tx = (transactionData || []).find(t => t.id === result.transaction_id);
    if (tx) {
      setTransactions(current => [{
        id: tx.id, cart: tx.trolley_number || trolley.trolley_number,
        items: Number(tx.items) || result.items_count || 0,
        total: Number(tx.total_amount) || Number(result.total_amount) || 0,
        time: tx.created_at ? new Date(tx.created_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}) : new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}),
        status: "completed"
      }, ...current.filter(t => t.id !== tx.id)]);
    }
    notify(`Checkout completed · ${money(Number(result.total_amount) || 0)}`);
  } catch (error) {
    console.error("Checkout error:", error);
    notify(error.message || "Checkout failed");
  }
};
 return <div className="app">
   <aside className="sidebar">
     <div className="logo"><div className="logo-mark">SR</div><div><b>Smart Retail</b><span>Intelligence Platform</span></div></div>
     <div className="store-switch">
      <div>
        <span className="live-dot"/>
        {storeName}
      </div>
      <small>
        {storeId} · EDGE ONLINE
      </small>
    </div>
     <nav>
  {nav.map(([name, Icon]) => (
    <button
      key={name}
      className={page === name ? "nav active" : "nav"}
      onClick={() => {
        setPage(name);

        if (name === "Notifications") {
          markNotificationsRead();
        }
      }}
    >
      <Icon size={17} />
      <span>{name}</span>

      {name === "Notifications" && !notificationsRead && (
        <em>4</em>
      )}
    </button>
  ))}
</nav>
     <div className="sidebar-foot">

  <div
  className="edge-status"
  onClick={() => setShowEdgeDetails(true)}
  style={{ cursor: "pointer" }}
>

    <div>
      <Wifi size={15}/>
      <b>Local Edge</b>
    </div>

    <strong>
      {edgeStatus === "connected"
        ? "Connected"
        : edgeStatus === "checking"
          ? "Checking..."
          : "Offline"
      }
    </strong>

    <span>
      {edgeStatus === "connected"
        ? "Edge server ready"
        : edgeStatus === "checking"
          ? "Checking edge server..."
          : "Edge server unavailable"
      }
    </span>

  </div>

  <div className="profile">

    <div>A</div>

    <span>
      <b>Admin</b>
      Store Manager
    </span>

    <button>•••</button>

  </div>

</div>
   </aside>
   <main>
    <header><div className="breadcrumb"><span>Smart Retail</span><ChevronRight size={13}/><b>{page}</b></div><div className="header-right"><div className="search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search anything..."/></div><button
  className="bell"
  onClick={() => {
    markNotificationsRead();
    setPage("Notifications");
  }}
>
  <Bell size={18}/>

  {!notificationsRead && (
    <i>4</i>
  )}

</button><div className="avatar">A</div></div></header>
    <div className="content">
      {page==="Customer Trolley"&&
        <CustomerTrolley products={products}/>
      }

      {page==="Dashboard"&&
        <Dashboard products={products} low={low} out={out} go={setPage}/>
      }
     {page==="Live Store"&&<LiveStore checkoutCart={checkoutCart}/>}
      {page==="Products"&&<Products products={filtered} openAdd={()=>setModal("product")} remove={removeProduct} edit={(product)=>{setEditingProduct(product);setModal("editProduct")}}/>}
     {page==="Inventory"&&<Inventory products={products} go={setPage} movements={movements}/>}
    {page==="Stock Orders"&&
  <Orders
    orders={orders}
    products={products}
    openNew={()=>setModal("order")}
    receive={receiveOrder}
  />
}

{modal === "receive" && (
  <ReceiveModal
    close={() => {
      setReceivingOrder(null);
      setModal(null);
    }}
    order={receivingOrder}
    submit={receiveStock}
  />
)}
     {page==="Transactions"&&<Transactions transactions={transactions}/>}
      {page==="Retail Guardian"&&<Guardian/>}
      {page==="AI Insights"&&<AI products={products}/>}
      {page==="Shopper Analytics"&&<ShopperAnalytics/>}
      {page==="Notifications"&&<Notifications/>}
      {page==="Settings"&&<SettingsPage/>}
    </div>
   </main>
   {/* EDGE SYSTEM STATUS MODAL */}

{showEdgeDetails && (
  <div
    style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,.55)",
      backdropFilter: "blur(5px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 9999
    }}
    onClick={() => setShowEdgeDetails(false)}
  >

    <div
      className="panel"
      style={{
        width: "420px",
        maxWidth: "calc(100vw - 32px)",
        padding: "24px"
      }}
      onClick={(e) => e.stopPropagation()}
    >

      {/* HEADER */}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "22px"
        }}
      >

        <div>
          <b style={{fontSize:"18px"}}>
            Edge System Status
          </b>

          <small
            style={{
              display:"block",
              marginTop:"5px",
              opacity:.65
            }}
          >
            Local system components
          </small>
        </div>

        <button
          className="ghost"
          onClick={() => setShowEdgeDetails(false)}
        >
          <X size={16}/>
        </button>

      </div>


      {/* FASTAPI */}

      <div
        style={{
          display:"flex",
          justifyContent:"space-between",
          padding:"14px 0",
          borderBottom:"1px solid rgba(148,163,184,.10)"
        }}
      >

        <span>FastAPI</span>

        <strong
          style={{
            color:
              systemStatus.fastapi === "connected"
                ? "#34d399"
                : "#fb7185"
          }}
        >
          {systemStatus.fastapi === "connected"
            ? "✓ Connected"
            : "✕ Offline"
          }
        </strong>

      </div>


      {/* MQTT */}

      <div
        style={{
          display:"flex",
          justifyContent:"space-between",
          padding:"14px 0",
          borderBottom:"1px solid rgba(148,163,184,.10)"
        }}
      >

        <span>MQTT Broker</span>

        <strong
          style={{
            color:
              systemStatus.mqtt === "connected"
                ? "#34d399"
                : "#fb7185"
          }}
        >
          {systemStatus.mqtt === "connected"
            ? "✓ Connected"
            : "✕ Offline"
          }
        </strong>

      </div>


      {/* DATABASE */}

      <div
        style={{
          display:"flex",
          justifyContent:"space-between",
          padding:"14px 0"
        }}
      >

        <span>Database</span>

        <strong
          style={{
            color:
              systemStatus.database === "connected"
                ? "#34d399"
                : "#fb7185"
          }}
        >
          {systemStatus.database === "connected"
            ? "✓ Connected"
            : "✕ Offline"
          }
        </strong>

      </div>


      {/* OVERALL */}

      <div
        style={{
          marginTop:"18px",
          padding:"12px 14px",
          borderRadius:"10px",
          background:
            systemStatus.fastapi === "connected" &&
            systemStatus.mqtt === "connected" &&
            systemStatus.database === "connected"
              ? "rgba(16,185,129,.08)"
              : "rgba(251,113,133,.08)"
        }}
      >

        <small>
          {systemStatus.fastapi === "connected" &&
           systemStatus.mqtt === "connected" &&
           systemStatus.database === "connected"

            ? "✓ All systems operational"

            : "⚠ One or more systems require attention"
          }
        </small>

      </div>


      {/* CLOSE */}

      <div
        style={{
          display:"flex",
          justifyContent:"flex-end",
          marginTop:"18px"
        }}
      >

        <button
          className="primary"
          onClick={() => setShowEdgeDetails(false)}
        >
          Close
        </button>

      </div>

    </div>

  </div>
)}
   {modal==="product"&&
  <ProductModal
    close={()=>setModal(null)}
    submit={addProduct}
  />
}

{modal==="editProduct"&&
  <ProductModal
    close={()=>{
      setEditingProduct(null);
      setModal(null);
    }}
    submit={updateProduct}
    product={editingProduct}
  />
}
   {modal==="order"&&<OrderModal close={()=>setModal(null)} products={products} submit={createOrder}/>}
   {toast&&<div className="toast"><CheckCircle2 size={17}/>{toast}</div>}
 </div>
}
function CustomerTrolley({ products = [] }) {
  const [cart, setCart] = useState([]);
  const [trolleys, setTrolleys] = useState([]);
  const [selectedTrolley, setSelectedTrolley] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cartLoading, setCartLoading] = useState(false);

  const [paymentQR, setPaymentQR] = useState(null);
  const [paymentLoading, setPaymentLoading] = useState(false);


  // ==========================================
  // GENERATE PAYMENT QR
  // ==========================================

  const generatePaymentQR = async () => {
    if (!selectedTrolley || cart.length === 0) {
      return;
    }

    setPaymentLoading(true);

    try {
      const data = await api("/payment/create-qr", {
        method: "POST",
        body: JSON.stringify({
          trolley_id: selectedTrolley.id
        })
      });

      setPaymentQR(data);

    } catch (error) {
      console.error("Payment QR error:", error);

      alert(
        error.message || "Unable to generate payment QR"
      );

    } finally {
      setPaymentLoading(false);
    }
  };


  // ==========================================
  // LOAD TROLLEYS
  // ==========================================

  useEffect(() => {
    const loadTrolleys = async () => {
      try {
        const data = await api("/trolleys");

        const list = data.trolleys || data || [];

        setTrolleys(list);

        const available =
          list.find(t => t.status === "available") || list[0];

        if (available) {
          setSelectedTrolley(available);
        }

      } catch (error) {
        console.error("Trolley load error:", error);

      } finally {
        setLoading(false);
      }
    };

    loadTrolleys();
  }, []);


  // ==========================================
  // LOAD CART FOR SELECTED TROLLEY
  // ==========================================

  useEffect(() => {
    if (!selectedTrolley) return;

    const loadCart = async () => {
      setCartLoading(true);

      try {
        const data = await api("/cart-items");

        const allItems = data.cart_items || data || [];

        const trolleyItems = allItems.filter(
          item =>
            item.trolley_id === selectedTrolley.id
        );

        const formattedCart = trolleyItems.map(item => ({
          id: item.id,
          product_id: item.product_id,
          name: item.products?.name || "Unknown Product",
          price: Number(item.products?.price || 0),
          quantity: Number(item.quantity || 1),
          trolley_id: item.trolley_id,
          expected_weight: Number(
            item.expected_weight || 0
          ),
          actual_weight: Number(
            item.actual_weight || 0
          ),
          verified: Boolean(item.verified)
        }));

        setCart(formattedCart);

      } catch (error) {
        console.error("Cart load error:", error);

      } finally {
        setCartLoading(false);
      }
    };

    loadCart();

  }, [selectedTrolley]);


  // ==========================================
  // ADD PRODUCT TO CART
  // ==========================================

  const addToCart = async (product) => {
    if (!selectedTrolley) {
      alert("No trolley available");
      return;
    }

    try {

      const existing = cart.find(
        item =>
          item.product_id === product.id
      );


      // ==========================================
      // EXISTING PRODUCT → INCREASE QUANTITY
      // ==========================================

      if (existing) {

        const newQuantity =
          existing.quantity + 1;

        const result = await api(
          `/cart-items/${existing.id}`,
          {
            method: "PUT",
            body: JSON.stringify({
              quantity: newQuantity
            })
          }
        );

        if (result.status !== "updated") {
          throw new Error(
            result.message ||
            "Quantity update failed"
          );
        }

        setCart(current =>
          current.map(item =>
            item.id === existing.id
              ? {
                  ...item,
                  quantity: newQuantity
                }
              : item
          )
        );

        return;
      }


      // ==========================================
      // NEW PRODUCT → ADD TO BACKEND
      // ==========================================

      const unitWeight =
        Number(product.unit_weight || 0);

      const payload = {
        trolley_id: selectedTrolley.id,
        product_id: product.id,
        quantity: 1,
        expected_weight: unitWeight,
        actual_weight: unitWeight,
        verified: false
      };

      const result = await api(
        "/cart-items",
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );

      if (result.status !== "added") {
        throw new Error(
          result.message ||
          "Product could not be added"
        );
      }

      const saved = result.cart_item;

      setCart(current => [
        ...current,
        {
          id: saved.id,
          product_id: product.id,
          name: product.name,
          price: Number(product.price || 0),
          quantity: 1,
          trolley_id: selectedTrolley.id,
          expected_weight: unitWeight,
          actual_weight: unitWeight,
          verified: false
        }
      ]);

    } catch (error) {

      console.error(
        "Add cart item error:",
        error
      );

      alert(
        error.message ||
        "Product could not be added"
      );
    }
  };


  // ==========================================
  // INCREASE QUANTITY
  // ==========================================

  const increaseQty = async (id) => {

    const item =
      cart.find(item => item.id === id);

    if (!item) return;

    const newQuantity =
      item.quantity + 1;

    try {

      const result = await api(
        `/cart-items/${id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            quantity: newQuantity
          })
        }
      );

      if (result.status !== "updated") {
        throw new Error(
          result.message ||
          "Quantity update failed"
        );
      }

      setCart(current =>
        current.map(item =>
          item.id === id
            ? {
                ...item,
                quantity: newQuantity
              }
            : item
        )
      );

    } catch (error) {

      console.error(
        "Increase quantity error:",
        error
      );

      alert(
        error.message ||
        "Could not increase quantity"
      );
    }
  };


  // ==========================================
  // DECREASE QUANTITY
  // ==========================================

  const decreaseQty = async (id) => {

    const item = cart.find(item => item.id === id);

    if (!item) return;


    // ==========================================
    // QUANTITY 1 ? REMOVE ITEM
    // ==========================================

    if (item.quantity === 1) {

      try {

        const result = await api(
          `/cart-items/${id}`,
          {
            method: "DELETE"
          }
        );

        // Even if the item was already removed server-side,
        // refresh from backend instead of showing a false popup.
        if (
          result.status !== "removed" &&
          result.status !== "not_found"
        ) {
          throw new Error(
            result.message ||
            "Item could not be removed"
          );
        }


        // Re-read server cart so UI always reflects real DB state.
        const data = await api("/cart-items");

        const allItems =
          data.cart_items || data || [];

        const trolleyItems =
          allItems.filter(
            x =>
              x.trolley_id === selectedTrolley.id
          );

        const refreshedCart =
          trolleyItems.map(item => ({
            id: item.id,
            product_id: item.product_id,
            name:
              item.products?.name ||
              "Unknown Product",
            price:
              Number(item.products?.price || 0),
            quantity:
              Number(item.quantity || 1),
            trolley_id:
              item.trolley_id,
            expected_weight:
              Number(item.expected_weight || 0),
            actual_weight:
              Number(item.actual_weight || 0),
            verified:
              Boolean(item.verified)
          }));

        setCart(refreshedCart);


        // Last item removed ? trolley becomes available.
        if (refreshedCart.length === 0) {

          await api(
            `/trolleys/${selectedTrolley.id}`,
            {
              method: "PUT",
              body: JSON.stringify({
                status: "available"
              })
            }
          );

          setTrolleys(current =>
            current.map(trolley =>
              trolley.id === selectedTrolley.id
                ? {
                    ...trolley,
                    status: "available"
                  }
                : trolley
            )
          );

          setSelectedTrolley(current =>
            current
              ? {
                  ...current,
                  status: "available"
                }
              : current
          );

          setPaymentQR(null);
        }

      } catch (error) {

        console.error(
          "Remove cart item error:",
          error
        );

        alert(
          error.message ||
          "Could not remove item"
        );
      }

      return;
    }


    // ==========================================
    // DECREASE QUANTITY
    // ==========================================

    const newQuantity =
      item.quantity - 1;

    try {

      const result = await api(
        `/cart-items/${id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            quantity: newQuantity
          })
        }
      );

      if (result.status !== "updated") {
        throw new Error(
          result.message ||
          "Quantity update failed"
        );
      }

      setCart(current =>
        current.map(item =>
          item.id === id
            ? {
                ...item,
                quantity: newQuantity
              }
            : item
        )
      );

    } catch (error) {

      console.error(
        "Decrease quantity error:",
        error
      );

      alert(
        error.message ||
        "Could not decrease quantity"
      );
    }
  };


  // ==========================================
  // TOTAL
  // ==========================================

  const total = cart.reduce(
    (sum, item) =>
      sum +
      Number(item.price || 0) *
      Number(item.quantity || 0),
    0
  );


  const itemCount = cart.reduce(
    (sum, item) =>
      sum +
      Number(item.quantity || 0),
    0
  );


  // ==========================================
  // UI
  // ==========================================

  return (
    <div
      style={{
        minHeight: "calc(100vh - 80px)",
        padding: "28px",
        background:
          "linear-gradient(135deg,#f7f9fc 0%,#eef4ff 55%,#f8fafc 100%)",
        boxSizing: "border-box"
      }}
    >

      <div
        style={{
          maxWidth: "1180px",
          margin: "0 auto"
        }}
      >

        {/* HEADER */}

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
            marginBottom: "22px"
          }}
        >

          <div>

            <div
              style={{
                fontSize: "11px",
                fontWeight: "800",
                letterSpacing: ".13em",
                color: "#64748b",
                marginBottom: "6px"
              }}
            >
              SMART TROLLEY
            </div>

            <h1
              style={{
                margin: 0,
                color: "#0f172a",
                fontSize: "30px",
                lineHeight: 1.1,
                letterSpacing: "-.035em"
              }}
            >
              Your shopping, made simple.
            </h1>

            <p
              style={{
                margin: "7px 0 0",
                color: "#64748b",
                fontSize: "13px"
              }}
            >
              Add products and watch your bill update in real time.
            </p>

          </div>


          {/* TROLLEY SELECTOR */}

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "10px 14px",
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: "14px",
              boxShadow: "0 8px 24px rgba(15,23,42,.06)"
            }}
          >

            <span
              style={{
                width: "9px",
                height: "9px",
                borderRadius: "50%",
                background:
                  selectedTrolley
                    ? "#22c55e"
                    : "#ef4444"
              }}
            />

            <select
              value={
                selectedTrolley?.id || ""
              }
              onChange={(e) => {

                const trolley =
                  trolleys.find(
                    t =>
                      String(t.id) ===
                      String(e.target.value)
                  );

                setSelectedTrolley(
                  trolley || null
                );

                setPaymentQR(null);
              }}
              style={{
                border: "none",
                outline: "none",
                background: "transparent",
                fontSize: "12px",
                fontWeight: "800",
                color: "#334155",
                cursor: "pointer"
              }}
            >

              <option value="">
                {loading
                  ? "Loading..."
                  : "Select Trolley"}
              </option>

              {trolleys.map(trolley => (
                <option
                  key={trolley.id}
                  value={trolley.id}
                >
                  {trolley.trolley_number} · {trolley.status}
                </option>
              ))}

            </select>

          </div>

        </div>


        {/* MAIN GRID */}

        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              "minmax(0,1fr) 350px",
            gap: "20px",
            alignItems: "start"
          }}
        >

          {/* PRODUCTS */}

          <section
            style={{
              background: "rgba(255,255,255,.92)",
              border: "1px solid #e2e8f0",
              borderRadius: "22px",
              padding: "22px",
              boxShadow:
                "0 18px 50px rgba(15,23,42,.07)"
            }}
          >

            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "16px"
              }}
            >

              <div>

                <h2
                  style={{
                    margin: 0,
                    fontSize: "19px",
                    color: "#0f172a"
                  }}
                >
                  Available products
                </h2>

                <span
                  style={{
                    display: "block",
                    marginTop: "4px",
                    color: "#94a3b8",
                    fontSize: "11px"
                  }}
                >
                  Backend connected · Cart data is saved
                </span>

              </div>


              <div
                style={{
                  padding: "7px 11px",
                  borderRadius: "10px",
                  background: "#eef2ff",
                  color: "#4f46e5",
                  fontSize: "11px",
                  fontWeight: "800"
                }}
              >
                {products.length} ITEMS
              </div>

            </div>


            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(3,minmax(0,1fr))",
                gap: "12px"
              }}
            >

              {products.map(product => {

                const inCart =
                  cart.find(
                    item =>
                      item.product_id ===
                      product.id
                  );

                return (

                  <button
                    key={product.id}
                    onClick={() =>
                      addToCart(product)
                    }
                    disabled={
                      !selectedTrolley ||
                      cartLoading
                    }
                    style={{
                      minHeight: "132px",
                      padding: "15px",
                      border: inCart
                        ? "2px solid #6366f1"
                        : "1px solid #e2e8f0",
                      borderRadius: "16px",
                      background: "#fff",
                      cursor:
                        !selectedTrolley ||
                        cartLoading
                          ? "not-allowed"
                          : "pointer",
                      textAlign: "left",
                      boxShadow: inCart
                        ? "0 8px 22px rgba(99,102,241,.13)"
                        : "0 5px 16px rgba(15,23,42,.04)",
                      position: "relative",
                      opacity:
                        !selectedTrolley ||
                        cartLoading
                          ? 0.55
                          : 1
                    }}
                  >

                    {inCart && (
                      <span
                        style={{
                          position: "absolute",
                          top: "10px",
                          right: "10px",
                          minWidth: "23px",
                          height: "23px",
                          padding: "0 6px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: "8px",
                          background: "#6366f1",
                          color: "#fff",
                          fontSize: "11px",
                          fontWeight: "800"
                        }}
                      >
                        {inCart.quantity}
                      </span>
                    )}


                    <div
                      style={{
                        width: "36px",
                        height: "36px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        borderRadius: "11px",
                        background:
                          "linear-gradient(135deg,#eef2ff,#dbeafe)",
                        color: "#4f46e5",
                        fontSize: "17px",
                        marginBottom: "12px"
                      }}
                    >
                      🛒
                    </div>


                    <strong
                      style={{
                        display: "block",
                        color: "#0f172a",
                        fontSize: "13px",
                        lineHeight: "1.25",
                        paddingRight: "20px"
                      }}
                    >
                      {product.name}
                    </strong>


                    <div
                      style={{
                        marginTop: "8px",
                        color: "#111827",
                        fontSize: "17px",
                        fontWeight: "800"
                      }}
                    >
                      ₹
                      {Number(
                        product.price || 0
                      ).toLocaleString("en-IN")}
                    </div>


                    <small
                      style={{
                        display: "block",
                        marginTop: "4px",
                        color: "#94a3b8",
                        fontSize: "10px"
                      }}
                    >
                      {inCart
                        ? "Added to trolley"
                        : "Tap to add"}
                    </small>

                  </button>
                );
              })}

            </div>

          </section>


          {/* CART */}

          <aside
            style={{
              background: "#0f172a",
              color: "#fff",
              borderRadius: "22px",
              padding: "22px",
              boxShadow:
                "0 20px 55px rgba(15,23,42,.18)",
              position: "sticky",
              top: "18px"
            }}
          >

            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingBottom: "17px",
                borderBottom:
                  "1px solid rgba(255,255,255,.10)"
              }}
            >

              <div>

                <div
                  style={{
                    fontSize: "18px",
                    fontWeight: "800"
                  }}
                >
                  Your Cart
                </div>

                <div
                  style={{
                    marginTop: "4px",
                    color: "#94a3b8",
                    fontSize: "12px"
                  }}
                >
                  {selectedTrolley
                    ? `${selectedTrolley.trolley_number} · ${itemCount} ${
                        itemCount === 1
                          ? "item"
                          : "items"
                      }`
                    : "No trolley selected"}
                </div>

              </div>


              <div
                style={{
                  width: "42px",
                  height: "42px",
                  borderRadius: "13px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background:
                    "rgba(99,102,241,.18)",
                  fontSize: "20px"
                }}
              >
                🛒
              </div>

            </div>


            <div
              style={{
                minHeight: "210px",
                maxHeight: "340px",
                overflowY: "auto",
                padding: "8px 0"
              }}
            >

              {cart.length === 0 ? (

                <div
                  style={{
                    minHeight: "205px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#64748b",
                    textAlign: "center"
                  }}
                >

                  <div
                    style={{
                      fontSize: "38px",
                      marginBottom: "10px"
                    }}
                  >
                    🛍️
                  </div>

                  <strong
                    style={{
                      color: "#cbd5e1",
                      fontSize: "14px"
                    }}
                  >
                    Your cart is empty
                  </strong>

                  <span
                    style={{
                      fontSize: "11px",
                      marginTop: "5px"
                    }}
                  >
                    Add products to see your bill
                  </span>

                </div>

              ) : (

                cart.map(item => (

                  <div
                    key={item.id}
                    style={{
                      padding: "13px 0",
                      borderBottom:
                        "1px solid rgba(255,255,255,.08)"
                    }}
                  >

                    <div
                      style={{
                        display: "flex",
                        justifyContent:
                          "space-between",
                        gap: "10px"
                      }}
                    >

                      <div
                        style={{
                          minWidth: 0
                        }}
                      >

                        <strong
                          style={{
                            display: "block",
                            fontSize: "13px",
                            color: "#f8fafc",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap"
                          }}
                        >
                          {item.name}
                        </strong>

                        <span
                          style={{
                            display: "block",
                            marginTop: "4px",
                            color: "#94a3b8",
                            fontSize: "11px"
                          }}
                        >
                          ₹{item.price} each
                        </span>

                      </div>


                      <strong
                        style={{
                          fontSize: "13px",
                          color: "#e2e8f0"
                        }}
                      >
                        ₹
                        {(
                          item.price *
                          item.quantity
                        ).toLocaleString("en-IN")}
                      </strong>

                    </div>


                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "9px",
                        marginTop: "9px"
                      }}
                    >

                      <button
                        onClick={() =>
                          decreaseQty(item.id)
                        }
                        style={{
                          width: "30px",
                          height: "30px",
                          border:
                            "1px solid rgba(255,255,255,.12)",
                          borderRadius: "9px",
                          background: "#1e293b",
                          color: "#fff",
                          cursor: "pointer",
                          fontSize: "16px"
                        }}
                      >
                        −
                      </button>


                      <strong
                        style={{
                          fontSize: "13px",
                          minWidth: "18px",
                          textAlign: "center"
                        }}
                      >
                        {item.quantity}
                      </strong>


                      <button
                        onClick={() =>
                          increaseQty(item.id)
                        }
                        style={{
                          width: "30px",
                          height: "30px",
                          border: "none",
                          borderRadius: "9px",
                          background: "#6366f1",
                          color: "#fff",
                          cursor: "pointer",
                          fontSize: "16px"
                        }}
                      >
                        +
                      </button>

                    </div>

                  </div>

                ))

              )}

            </div>


            {/* TOTAL */}

            <div
              style={{
                marginTop: "10px",
                paddingTop: "17px",
                borderTop:
                  "1px solid rgba(255,255,255,.10)"
              }}
            >

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  color: "#94a3b8",
                  fontSize: "12px",
                  marginBottom: "7px"
                }}
              >
                <span>Subtotal</span>

                <span>
                  ₹{total.toLocaleString("en-IN")}
                </span>
              </div>


              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center"
                }}
              >

                <span
                  style={{
                    fontSize: "15px",
                    fontWeight: "700"
                  }}
                >
                  Total
                </span>

                <strong
                  style={{
                    fontSize: "26px",
                    letterSpacing: "-.03em"
                  }}
                >
                  ₹{total.toLocaleString("en-IN")}
                </strong>

              </div>


              {/* ==========================================
                  PAY BUTTON
              ========================================== */}

              <button
                disabled={
                  cart.length === 0 ||
                  paymentLoading
                }
                onClick={generatePaymentQR}
                style={{
                  width: "100%",
                  marginTop: "17px",
                  padding: "16px",
                  border: "none",
                  borderRadius: "14px",
                  background:
                    cart.length === 0 ||
                    paymentLoading
                      ? "#334155"
                      : "linear-gradient(135deg,#6366f1,#4f46e5)",
                  color: "#fff",
                  fontSize: "16px",
                  fontWeight: "800",
                  cursor:
                    cart.length === 0 ||
                    paymentLoading
                      ? "not-allowed"
                      : "pointer",
                  boxShadow:
                    cart.length === 0 ||
                    paymentLoading
                      ? "none"
                      : "0 10px 25px rgba(99,102,241,.30)"
                }}
              >

                {paymentLoading
                  ? "Generating QR..."
                  : cart.length === 0
                    ? "Add items to continue"
                    : `PAY ₹${total.toLocaleString("en-IN")}`}

              </button>


              {/* ==========================================
                  PAYMENT QR
              ========================================== */}

              {paymentQR && (

                <div
                  style={{
                    marginTop: "18px",
                    padding: "20px",
                    background: "#ffffff",
                    borderRadius: "18px",
                    textAlign: "center",
                    boxShadow:
                      "0 10px 30px rgba(0,0,0,.12)"
                  }}
                >

                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: "800",
                      color: "#0f172a",
                      marginBottom: "6px"
                    }}
                  >
                    Scan to Pay
                  </div>


                  <div
                    style={{
                      fontSize: "24px",
                      fontWeight: "900",
                      color: "#111827",
                      marginBottom: "14px"
                    }}
                  >
                    ₹
                    {Number(
                      paymentQR.amount
                    ).toLocaleString("en-IN")}
                  </div>


                  <img
                    src={paymentQR.image_url}
                    alt="UPI Payment QR"
                    style={{
                      width: "320px",
                      height: "320px",
                      maxWidth: "100%",
                      objectFit: "contain",
                      display: "block",
                      margin: "0 auto"
                    }}
                  />


                  <div
                    style={{
                      marginTop: "12px",
                      fontSize: "11px",
                      color: "#64748b"
                    }}
                  >
                    Scan using any UPI app
                  </div>


                  <button
                    onClick={() =>
                      setPaymentQR(null)
                    }
                    style={{
                      marginTop: "12px",
                      padding: "8px 14px",
                      border: "none",
                      borderRadius: "8px",
                      background: "#e2e8f0",
                      color: "#334155",
                      cursor: "pointer"
                    }}
                  >
                    Close
                  </button>

                </div>

              )}


              <div
                style={{
                  marginTop: "11px",
                  textAlign: "center",
                  color: "#64748b",
                  fontSize: "10px"
                }}
              >
                🔒 Backend cart · RFID + weight verification
              </div>

            </div>

          </aside>

        </div>

      </div>

    </div>
  );
}
const Head=({eyebrow,title,sub,action})=><div className="page-head"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1><p>{sub}</p></div>{action}</div>;
const Stat=({label,value,meta,icon,trend})=><div className="stat"><div className="stat-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{trend&&<b>↗ {trend}</b>} {meta}</small></div></div>;
const Panel=({title,sub,action,children,flush=false})=><div className={"panel "+(flush?"flush":"")}><div className="panel-head">{<div>{title&&<h3>{title}</h3>}{sub&&<p>{sub}</p>}</div>}{action}</div>{children}</div>;
const Status=({p})=><span className={"tag "+(p.stock===0?"red":p.stock<=p.min?"amber":"green")}>{p.stock===0?"Out of stock":p.stock<=p.min?"Low stock":"Healthy"}</span>;

function Dashboard({products,low,out,go}){

  const [transactions,setTransactions]=useState([]);
  const [trolleys,setTrolleys]=useState([]);
  const [alerts,setAlerts]=useState([]);
  const [cartItems,setCartItems]=useState([]);

  // -------------------------
  // DYNAMIC GREETING
  // -------------------------

  const getGreeting=()=>{
    const hour=new Date().getHours();

    if(hour>=5 && hour<12){
      return "Good morning";
    }else if(hour>=12 && hour<17){
      return "Good afternoon";
    }else if(hour>=17 && hour<24){
      return "Good evening";
    }else{
      return "Good night";
    }
  };

  const [greeting,setGreeting]=useState(getGreeting());

  useEffect(()=>{

    const updateGreeting=()=>{
      setGreeting(getGreeting());
    };

    updateGreeting();

    // Update greeting every minute
    const greetingTimer=setInterval(
      updateGreeting,
      60000
    );

    return ()=>clearInterval(greetingTimer);

  },[]);


  useEffect(()=>{
    const loadDashboard=async()=>{
      // Load each resource independently so one API failure
      // cannot hide valid trolley data.
      const results = await Promise.allSettled([
        api("/transactions"),
        api("/trolleys"),
        api("/cart-items"),
        api("/alerts?include_resolved=false")
      ]);

      const [transactionResult, trolleyResult, cartResult, alertResult] = results;

      if (transactionResult.status === "fulfilled") {
        setTransactions(transactionResult.value || []);
      } else {
        console.error("Dashboard transactions error:", transactionResult.reason);
      }

      if (trolleyResult.status === "fulfilled") {
        const data = trolleyResult.value;
        const trolleyList = data?.trolleys || data || [];
        setTrolleys(Array.isArray(trolleyList) ? trolleyList : []);
      } else {
        console.error("Dashboard trolleys error:", trolleyResult.reason);
      }

      if (cartResult.status === "fulfilled") {
        const data = cartResult.value;
        const items = data?.cart_items || data || [];
        setCartItems(Array.isArray(items) ? items : []);
      } else {
        console.error("Dashboard cart items error:", cartResult.reason);
      }

      if (alertResult.status === "fulfilled") {
        const data = alertResult.value;
        setAlerts(Array.isArray(data) ? data : []);
      } else {
        console.error("Dashboard alerts error:", alertResult.reason);
      }
    };

    loadDashboard();
    const interval=setInterval(loadDashboard,5000);
    return ()=>clearInterval(interval);
  },[]);


  // -------------------------
  // DATE HELPERS
  // -------------------------

  const today=new Date();

  const startOfToday=new Date(today);
  startOfToday.setHours(0,0,0,0);

  const startOfYesterday=new Date(startOfToday);

  startOfYesterday.setDate(
    startOfYesterday.getDate()-1
  );


  // -------------------------
  // TODAY / YESTERDAY SALES
  // -------------------------

  const todayTransactions=transactions.filter(t=>{

    if(!t.created_at) return false;

    return new Date(t.created_at)>=startOfToday;

  });


  const yesterdayTransactions=transactions.filter(t=>{

    if(!t.created_at) return false;

    const date=new Date(t.created_at);

    return (
      date>=startOfYesterday &&
      date<startOfToday
    );

  });


  const todaySales=todayTransactions.reduce(
    (sum,t)=>
      sum+(Number(t.total_amount)||0),
    0
  );


  const yesterdaySales=yesterdayTransactions.reduce(
    (sum,t)=>
      sum+(Number(t.total_amount)||0),
    0
  );


  let salesTrend=null;

  if(yesterdaySales>0){

    salesTrend=
      ((todaySales-yesterdaySales)/
      yesterdaySales)*100;

  }


  // -------------------------
  // TROLLEY STATS
  // -------------------------

  const activeTrolleys=trolleys.filter(
    trolley=>trolley.status==="shopping"
  ).length;


  const connectedTrolleys=trolleys.length;


  // -------------------------
  // SALES CHART
  // -------------------------

  const hourlySales=[];

  for(let hour=0;hour<24;hour++){

    const amount=todayTransactions
      .filter(t=>{

        const date=new Date(t.created_at);

        return date.getHours()===hour;

      })
      .reduce(
        (sum,t)=>
          sum+(Number(t.total_amount)||0),
        0
      );

    hourlySales.push(amount);

  }


  const maxHourlySales=Math.max(
    ...hourlySales,
    1
  );


  // Show 12-hour window around store activity
  const chartHours=hourlySales
    .map((amount,hour)=>({
      hour,
      amount
    }))
    .filter(x=>x.hour>=8 && x.hour<=19);


  // -------------------------
  // LIVE TROLLEY ACTIVITY
  // -------------------------

  const liveCarts=trolleys.map(trolley=>{

  const items=cartItems.filter(
    item=>item.trolley_id===trolley.id
  );


  const itemCount=items.reduce(
    (sum,item)=>
      sum+(Number(item.quantity)||0),
    0
  );


  const total=items.reduce(
    (sum,item)=>
      sum+
      (Number(item.products?.price)||0)*
      (Number(item.quantity)||0),
    0
  );


  // Find active alert for this trolley
  const trolleyAlert=alerts.find(
    alert =>
      alert.trolley_id === trolley.id &&
      alert.status !== "resolved"
  );


  let alertReason=null;


  if(trolleyAlert){

    if(trolleyAlert.type==="weight_mismatch"){

      const expected=
        Number(trolleyAlert.expected_value);

      const actual=
        Number(trolleyAlert.actual_value);

      alertReason=
        actual>expected
          ? "Weight mismatch · Extra weight"
          : "Weight mismatch · Weight below expected";

    }

    else if(
      trolleyAlert.type==="unregistered_item"
    ){

      alertReason=
        "Unregistered item · No matching RFID";

    }

    else if(
      trolleyAlert.type==="inventory_discrepancy"
    ){

      alertReason=
        "Inventory discrepancy";

    }

    else{

      alertReason=
        "Verification required";

    }

  }


  return {

    id:trolley.trolley_number,


    state:
      trolley.status==="shopping"
        ? "Shopping"
        : trolley.status==="alert"
        ? "Alert"
        : "Available",


    items:itemCount,

    total:total,


    alert:
      trolleyAlert
        ? alertReason
        : null

  };

});


  return (
    <>

      <Head
        eyebrow="STORE OVERVIEW"
        title={`${greeting}, Admin.`}
        sub="Everything important across your store, in one place."
        action={
          <button
            className="primary"
            onClick={()=>go("Live Store")}
          >
            <Store size={16}/>
            Open Live Store
          </button>
        }
      />


      {/* STATS */}

      <div className="stats">

        <Stat
          label="Today's Sales"
          value={money(todaySales)}
          meta={
            yesterdaySales>0
              ? "vs yesterday"
              : "today"
          }
          trend={
            salesTrend!==null
              ? `${salesTrend>=0?"+":""}${salesTrend.toFixed(1)}%`
              : undefined
          }
          icon={<ReceiptText/>}
        />


        <Stat
          label="Active Trolleys"
          value={activeTrolleys}
          meta={`of ${connectedTrolleys} connected`}
          icon={<ShoppingCart/>}
        />


        <Stat
          label="Low Stock"
          value={low.length}
          meta="items need attention"
          icon={<AlertTriangle/>}
        />


        <Stat
          label="Out of Stock"
          value={out.length}
          meta="items unavailable"
          icon={<Package/>}
        />

      </div>


      {/* DASHBOARD GRID */}

      <div className="dashboard-grid">


        {/* SALES ACTIVITY */}

        <Panel
          title="Store activity"
          sub="Sales performance · Today"
        >

          <div className="chart">

            <div className="chart-value">

              {money(todaySales)}

              <span>
                today
              </span>

            </div>


            <div className="bars">

              {chartHours.map(x=>(

                <i
                  key={x.hour}
                  style={{
                    height:
                      `${Math.max(
                        4,
                        (x.amount/maxHourlySales)*100
                      )}%`
                  }}
                />

              ))}

            </div>


            <div className="xlabels">

              {chartHours.map(x=>{

                const suffix=
                  x.hour>=12
                    ? "PM"
                    : "AM";

                const displayHour=
                  x.hour%12===0
                    ? 12
                    : x.hour%12;

                return (
                  <span key={x.hour}>
                    {displayHour} {suffix}
                  </span>
                );

              })}

            </div>

          </div>

        </Panel>


        {/* NEEDS ATTENTION */}

        <Panel
          title="Needs attention"
          sub="Priority items"
        >

          <div className="attention">

            {[...low,...out]
              .slice(0,4)
              .map(p=>(

                <div key={p.id}>

                  <div className="product-mini">

                    <div>
                      {p.name.slice(0,1)}
                    </div>

                    <span>

                      <b>
                        {p.name}
                      </b>

                      {p.current_stock===0
                        ? "Out of stock"
                        : `${p.current_stock} units remaining`
                      }

                    </span>

                  </div>

                  <Status p={p}/>

                </div>

              ))}


            {low.length===0 &&
             out.length===0 && (

              <div style={{padding:"20px 0"}}>

                <small>
                  No inventory issues right now.
                </small>

              </div>

            )}

          </div>

        </Panel>

      </div>


      {/* LIVE TROLLEY ACTIVITY */}

      <Panel
        title="Live trolley activity"
        sub="Real-time from Local Edge"
        action={
          <button
            className="link"
            onClick={()=>go("Live Store")}
          >
            View live store
            <ChevronRight size={14}/>
          </button>
        }
      >

        <div className="cart-list">

          {liveCarts.length===0 ? (

            <div style={{padding:"20px"}}>

              <small>
                No trolley data available.
              </small>

            </div>

          ) : (

            liveCarts.map(c=>(

              <CartRow
                key={c.id}
                c={c}
              />

            ))

          )}

        </div>

      </Panel>

    </>

  );

}
function CartRow({c}){

  return (

    <div className="cart-row">

      <span
        className={
          "state " +
          c.state.toLowerCase()
        }
      />

      <div>
        <b>{c.id}</b>
        <small>{c.state}</small>
      </div>

      <span>
        {c.items} items
      </span>

      <strong>
        {money(c.total)}
      </strong>

      {c.alert ? (

        <span className="tag red">
          {c.alertReason || "Verification required"}
        </span>

      ) : (

        <span className="tag green">
          Verified
        </span>

      )}

    </div>

  );

}
function LiveStore({checkoutCart}){
  const [trolleys,setTrolleys]=useState([]);
  const [selected,setSelected]=useState(0);
  const [cartItems,setCartItems]=useState([]);
  const [alerts,setAlerts]=useState([]);

  const loadLiveStore=async()=>{
    // Keep trolley data visible even if cart/alert APIs fail.
    const results = await Promise.allSettled([
      api("/trolleys"),
      api("/cart-items"),
      api("/alerts?include_resolved=false")
    ]);

    const [trolleyResult, cartResult, alertResult] = results;

    if (trolleyResult.status === "fulfilled") {
      const data = trolleyResult.value;
      const trolleyList = data?.trolleys || data || [];
      setTrolleys(Array.isArray(trolleyList) ? trolleyList : []);
    } else {
      console.error("Live Store trolleys error:", trolleyResult.reason);
    }

    if (cartResult.status === "fulfilled") {
      const data = cartResult.value;
      const items = data?.cart_items || data || [];
      setCartItems(Array.isArray(items) ? items : []);
    } else {
      console.error("Live Store cart items error:", cartResult.reason);
    }

    if (alertResult.status === "fulfilled") {
      const data = alertResult.value;
      setAlerts(Array.isArray(data) ? data : []);
    } else {
      console.error("Live Store alerts error:", alertResult.reason);
    }
  };

  useEffect(()=>{
    loadLiveStore();

    // Refresh live data every 3 seconds
    const interval=setInterval(()=>{
      loadLiveStore();
    },3000);

    return ()=>clearInterval(interval);
  },[]);

  const selectedTrolley=trolleys[selected];

  // If selected trolley disappears after refresh
  useEffect(()=>{
    if(selected>=trolleys.length && trolleys.length>0){
      setSelected(0);
    }
  },[trolleys,selected]);

  if(!selectedTrolley){
    return (
      <>
        <Head
          eyebrow="REAL-TIME OPERATIONS"
          title="Live Store"
          sub="Monitor smart trolleys and resolve verification events."
          action={
            <span className="live-pill">
              <i/>Edge live
            </span>
          }
        />

        <Panel
          title="Smart trolleys"
          sub="Loading trolley data..."
        >
          <div style={{padding:"24px"}}>
            <small>No trolley data available.</small>
          </div>
        </Panel>
      </>
    );
  }

  // Get items belonging to selected trolley
  const trolleyItems=cartItems.filter(
    item=>item.trolley_id===selectedTrolley.id
  );

  // Calculate item count
  const itemCount=trolleyItems.reduce(
    (sum,item)=>sum+(Number(item.quantity)||0),
    0
  );

  // Calculate bill
  const totalAmount=trolleyItems.reduce(
    (sum,item)=>
      sum+
      (Number(item.products?.price)||0)*
      (Number(item.quantity)||0),
    0
  );

  // Check if any item is not verified
  const hasUnverifiedItem=trolleyItems.some(
    item=>item.verified===false
  );

  // Trolley alert status
  const isAlert=
    selectedTrolley.status==="alert" ||
    hasUnverifiedItem;

  const selectedAlert=alerts.find(
  alert =>
    alert.trolley_id===selectedTrolley.id &&
    alert.status!=="resolved"
);  

  // Stats
  const connectedTrolleys=trolleys.length;

  const shoppingNow=trolleys.filter(
    trolley=>trolley.status==="shopping"
  ).length;

  const alertCount=trolleys.filter(
    trolley=>trolley.status==="alert"
  ).length;

  const verifiedItems=cartItems.filter(
    item=>item.verified===true
  ).reduce(
    (sum,item)=>sum+(Number(item.quantity)||0),
    0
  );

  // Resolve current trolley alert
  const resolveAlert=async()=>{
    try {
      await api(`/trolleys/${selectedTrolley.id}`, {method:"PUT", body:JSON.stringify({status:"shopping"})});
      setTrolleys(current=>current.map(trolley=>trolley.id===selectedTrolley.id ? {...trolley,status:"shopping"} : trolley));
      notify(`${selectedTrolley.trolley_number} alert resolved`);
    } catch(error) {
      console.error("Resolve alert error:",error);
      notify("Could not resolve alert");
    }
  };

  return (
    <>
      <Head
        eyebrow="REAL-TIME OPERATIONS"
        title="Live Store"
        sub="Monitor smart trolleys and resolve verification events."
        action={
          <span className="live-pill">
            <i/>Edge live
          </span>
        }
      />

      {/* LIVE STATS */}
      <div className="stats compact">

        <Stat
          label="Connected Trolleys"
          value={connectedTrolleys}
          meta="local network"
          icon={<Wifi/>}
        />

        <Stat
          label="Shopping Now"
          value={shoppingNow}
          meta="active carts"
          icon={<ShoppingCart/>}
        />

        <Stat
          label="Alerts"
          value={alertCount}
          meta="needs verification"
          icon={<ShieldCheck/>}
        />

        <Stat
          label="Verified Items"
          value={verifiedItems}
          meta="current carts"
          icon={<CheckCircle2/>}
        />

      </div>

      <div className="live-grid">

        {/* TROLLEY LIST */}
        <Panel
          title="Smart trolleys"
          sub="Select a trolley to inspect"
        >
          <div className="cart-grid">

            {trolleys.map((trolley,index)=>{

              const items=cartItems.filter(
                item=>item.trolley_id===trolley.id
              );

              const count=items.reduce(
                (sum,item)=>
                  sum+(Number(item.quantity)||0),
                0
              );

              const total=items.reduce(
                (sum,item)=>
                  sum+
                  (Number(item.products?.price)||0)*
                  (Number(item.quantity)||0),
                0
              );

              const unverified=items.some(
                item=>item.verified===false
              );

              const alert=
                trolley.status==="alert" ||
                unverified;

              return (

                <button
                  key={trolley.id}
                  className={
                    "cart-card "+
                    (selected===index?"selected":"")
                  }
                  onClick={()=>setSelected(index)}
                >

                  <div className="cart-head">

                    <span
                      className={
                        "state "+
                        trolley.status
                      }
                    />

                    <b>{trolley.trolley_number}</b>

                    <small>
                      {
                        trolley.status
                          ? trolley.status.charAt(0).toUpperCase()+
                            trolley.status.slice(1)
                          : "Unknown"
                      }
                    </small>

                  </div>

                  <strong>{count}</strong>

                  <span className="items-label">
                    items in cart
                  </span>

                  <footer>

                    {money(total)}

                    <span>
                      {alert
                        ?"⚠ Alert"
                        :"✓ Verified"}
                    </span>

                  </footer>

                  {alert&&(
                    <em>
                      Verification required
                    </em>
                  )}

                </button>

              );
            })}

          </div>
        </Panel>


        {/* SELECTED TROLLEY DETAILS */}
        <Panel
          title={selectedTrolley.trolley_number}
          sub="Trolley details"
        >

          <div className="detail-top">

            <span>
              <b>Connection</b>

              <small>
                <i/>
                Connected
              </small>
            </span>

            <span>
              <b>Items</b>

              <small>
                {itemCount}
              </small>
            </span>

            <span>
              <b>Bill</b>

              <small>
                {money(totalAmount)}
              </small>
            </span>

          </div>


          {/* CURRENT ITEMS */}
          <h4>Current items</h4>

          <div className="line-items">

            {trolleyItems.length===0 ? (

              <div>
                <span>No items in trolley</span>
              </div>

            ) : (

              trolleyItems.map(item=>{

                const quantity=
                  Number(item.quantity)||0;

                const price=
                  Number(item.products?.price)||0;

                const total=
                  price*quantity;

                return (

                  <div key={item.id}>

                    <span>
                      {item.products?.name || "Unknown Product"}

                      {quantity>1 && (
                        <small style={{marginLeft:"6px"}}>
                          × {quantity}
                        </small>
                      )}
                    </span>

                    <b>
                      {money(total)}
                    </b>

                  </div>

                );

              })

            )}

          </div>


         {/* VERIFICATION */}

{isAlert ? (

  <div className="verification alert">

    <AlertTriangle/>

    <span>

      {selectedAlert?.type === "weight_mismatch" ? (

        <>

          <b>
            Weight mismatch
          </b>

          Expected{" "}
          {selectedAlert.expected_value ?? "-"} kg
          {" · "}
          Detected{" "}
          {selectedAlert.actual_value ?? "-"} kg

        </>

      ) : selectedAlert?.type === "unregistered_item" ? (

        <>

          <b>
            Unregistered item
          </b>

          No matching RFID scan was detected.

        </>

      ) : selectedAlert?.type === "inventory_discrepancy" ? (

        <>

          <b>
            Inventory discrepancy
          </b>

          Inventory count does not match.

        </>

      ) : (

        <>

          <b>
            Verification required
          </b>

          RFID identity and physical
          weight need verification.

        </>

      )}

    </span>

    <button
      className="primary"
      onClick={resolveAlert}
    >
      Resolve
    </button>

  </div>

) : (

  <div className="verification ok">

    <CheckCircle2/>

    <span>

      <b>
        All items verified
      </b>

      RFID identity and physical
      weight are consistent.

    </span>

  </div>

)}


          {/* CHECKOUT */}
          <button
            className="primary"
            style={{
              width:"100%",
              marginTop:"16px",
              justifyContent:"center"
            }}
            disabled={trolleyItems.length===0}
            onClick={()=>
              checkoutCart(
                selectedTrolley.trolley_number
              )
            }
          >
            Complete Checkout
          </button>

        </Panel>

      </div>
    </>
  );
}
function Products({products,openAdd,remove,edit}){
  return (
    <>
      <Head
        eyebrow="CATALOG"
        title="Products"
        sub="Manage products, RFID mapping, pricing and stock thresholds."
        action={
          <button className="primary" onClick={openAdd}>
            <Plus size={16}/> Add Product
          </button>
        }
      />

      <Panel flush>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>RFID</th>
                <th>Category</th>
                <th>Price</th>
                <th>Stock</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {products.map(p => (
                <tr key={p.id}>

                  <td>
                    <b>{p.name}</b>
                    <small>{p.id} · {p.unit_weight} kg</small>
                  </td>

                  <td>
                    <code>{p.rfid_tag || "Not assigned"}</code>
                  </td>

                  <td>{p.category}</td>

                  <td>
                    <strong>{money(p.price)}</strong>
                  </td>

                  <td>{p.current_stock}</td>

                  <td>
                    <Status
                      p={{
                        ...p,
                        stock: p.current_stock,
                        min: p.minimum_stock
                      }}
                    />
                  </td>

                <td>
  <button
    className="text-edit"
    onClick={() => edit(p)}
  >
    Edit
  </button>

  <button
    className="text-danger"
    onClick={() => remove(p.id)}
  >
    Remove
  </button>
</td>

                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}

function Inventory({products,go,movements}){
  return <>
    <Head
      eyebrow="STOCK CONTROL"
      title="Inventory"
      sub="Know what is available now and what needs replenishment."
      action={
        <button className="ghost" onClick={()=>go("Stock Orders")}>
          <Truck size={16}/> Manage Orders
        </button>
      }
    />

    <div className="stats compact">
      <Stat
        label="Total SKUs"
        value={products.length}
        meta="active products"
        icon={<Package/>}
      />

      <Stat
        label="Healthy"
        value={products.filter(p=>p.current_stock>p.minimum_stock).length}
        meta="normal level"
        icon={<CheckCircle2/>}
      />

      <Stat
        label="Low Stock"
        value={products.filter(
          p=>p.current_stock>0 && p.current_stock<=p.minimum_stock
        ).length}
        meta="replenish soon"
        icon={<AlertTriangle/>}
      />

      <Stat
        label="Out of Stock"
        value={products.filter(p=>p.current_stock===0).length}
        meta="replenish now"
        icon={<Boxes/>}
      />
    </div>

    <Panel flush>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Current stock</th>
              <th>Minimum</th>
              <th>Unit</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {products.map(p=>(
              <tr key={p.id}>
                <td>
                  <b>{p.name}</b>
                  <small>{p.category}</small>
                </td>

                <td>
                  <strong>{p.current_stock}</strong>
                </td>

                <td>{p.minimum_stock}</td>

                <td>{p.unit_weight} kg</td>

                <td>
                  <Status
                    p={{
                      ...p,
                      stock: p.current_stock,
                      min: p.minimum_stock
                    }}
                  />
                </td>

                <td>
                  {p.current_stock<=p.minimum_stock &&
                    <button
                      className="link"
                      onClick={()=>go("Stock Orders")}
                    >
                      Replenish <ChevronRight size={13}/>
                    </button>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
   <Panel
  title="Recent Movements"
  sub="Latest inventory updates."
  flush
>
  <div className="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Product</th>
          <th>Type</th>
          <th>Quantity</th>
          <th>Reference</th>
          <th>Date</th>
        </tr>
      </thead>

      <tbody>
        {movements.length === 0 ? (
          <tr>
            <td colSpan="5">
              <small>No inventory movements yet.</small>
            </td>
          </tr>
        ) : (
          movements.map(m => (
            <tr key={m.id}>
              <td>
                <b>{m.products?.name || "Unknown Product"}</b>
              </td>

              <td>
                <b>{m.type}</b>
              </td>

              <td>
                <strong>
                  {m.type === "PURCHASE" ? "+" : "-"}
                  {m.quantity}
                </strong>
              </td>

              <td>
                <small>{m.reference_id || "—"}</small>
              </td>

              <td>
                <small>
                  {m.created_at
                    ? new Date(m.created_at).toLocaleDateString("en-GB")
                    : "—"}
                </small>
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  </div>
</Panel>

  </>
}


function Orders({orders, products, openNew, receive}) {
  return (
    <>
      <Head
        eyebrow="PROCUREMENT"
        title="Stock Orders"
        sub="Create purchase orders and record incoming stock."
        action={
          <button className="primary" onClick={openNew}>
            <Plus size={16}/> New Order
          </button>
        }
      />

      <div className="order-summary">
        <div>
          <span>Open orders</span>
          <b>
            {orders.filter(
              o => String(o.status).toLowerCase() !== "received"
            ).length}
          </b>
        </div>

        <div>
          <span>Units on order</span>
          <b>
            {orders.reduce(
              (a, o) =>
                a +
                Math.max(
                  0,
                  (Number(o.qty) || 0) - (Number(o.received) || 0)
                ),
              0
            )}
          </b>
        </div>

        <div>
          <span>Received</span>
          <b>
            {orders.reduce(
              (a, o) => a + (Number(o.received) || 0),
              0
            )}
          </b>
        </div>
      </div>

      {/* EVERY PRODUCT */}
      <Panel
        title="Product Procurement"
        sub="Stock and incoming quantity for every product."
        flush
      >
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Current Stock</th>
                <th>Minimum</th>
                <th>On Order</th>
                <th>Received</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              {products.map(product => {
                const productOrders = orders.filter(
                  o =>
                    String(o.product).toLowerCase() ===
                    String(product.name).toLowerCase()
                );

                const onOrder = productOrders.reduce(
                  (sum, o) =>
                    sum +
                    Math.max(
                      0,
                      (Number(o.qty) || 0) -
                      (Number(o.received) || 0)
                    ),
                  0
                );

                const received = productOrders.reduce(
                  (sum, o) => sum + (Number(o.received) || 0),
                  0
                );

                const stock = Number(product.current_stock) || 0;
                const minimum = Number(product.minimum_stock) || 0;

                let status = "Healthy";
                let statusClass = "green";

                if (stock === 0) {
                  status = "Out of Stock";
                  statusClass = "red";
                } else if (stock <= minimum) {
                  status = "Low Stock";
                  statusClass = "amber";
                }

                return (
                  <tr key={product.id}>
                    <td>
                      <b>{product.name}</b>
                      <small>{product.category}</small>
                    </td>

                    <td>{stock}</td>

                    <td>{minimum}</td>

                    <td>
                      <b>{onOrder}</b>
                    </td>

                    <td>{received}</td>

                    <td>
                      <span className={"tag " + statusClass}>
                        {status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* EXISTING ORDERS */}
      <Panel
        title="Purchase Orders"
        sub="Track individual supplier orders and incoming stock."
        flush
      >
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Order</th>
                <th>Supplier</th>
                <th>Product</th>
                <th>Qty</th>
                <th>Received</th>
                <th>Status</th>
                <th/>
              </tr>
            </thead>

            <tbody>
              {orders.map((o, i) => {
                const qty = Number(o.qty) || 0;
                const received = Number(o.received) || 0;
                const status = String(
                  o.status || "pending"
                ).toLowerCase();

                return (
                  <tr key={o.id}>
                    <td>
                      <b>{o.id}</b>
                      <small>{o.date}</small>
                    </td>

                    <td>{o.supplier}</td>

                    <td>{o.product}</td>

                    <td>{qty}</td>

                    <td>{received}</td>

                    <td>
                      <span
                        className={
                          "tag " +
                          (status === "received"
                            ? "green"
                            : status === "partially_received"
                            ? "amber"
                            : "amber")
                        }
                      >
                        {status === "partially_received"
                          ? "Partially Received"
                          : status === "received"
                          ? "Received"
                          : "Pending"}
                      </span>
                    </td>

                    <td>
                      {status !== "received" && (
                        <button
                          className="small-action"
                          onClick={() => receive(i)}
                        >
                          <CheckCircle2 size={14}/>
                          Receive Stock
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
function ReceiveModal({close, order, submit}) {
  if (!order) return null;

  const ordered = Number(order.qty) || 0;
  const alreadyReceived = Number(order.received) || 0;
  const remaining = Math.max(0, ordered - alreadyReceived);

  return (
    <Modal
      title="Receive Stock"
      sub="Record the quantity received from the supplier."
      close={close}
    >
      <div className="order-summary">
        <div>
          <span>Product</span>
          <b>{order.product}</b>
        </div>

        <div>
          <span>Ordered</span>
          <b>{ordered}</b>
        </div>

        <div>
          <span>Already Received</span>
          <b>{alreadyReceived}</b>
        </div>

        <div>
          <span>Remaining</span>
          <b>{remaining}</b>
        </div>
      </div>

      <form onSubmit={submit}>
        <div className="form-grid">
          <label>
            Received Units
            <input
              name="received"
              type="number"
              min="1"
              max={remaining}
              required
              placeholder={`Enter quantity (max ${remaining})`}
            />
          </label>
        </div>

        <div className="order-note">
          <Truck size={16}/>
          <span>
            Enter the actual quantity received.
            Only received units will be added to inventory.
          </span>
        </div>

        <ModalActions
          close={close}
          label="Confirm Receipt"
        />
      </form>
    </Modal>
  );
}

function Transactions({transactions}) {
  return (
    <div className="transactions-page">
      <Head
        eyebrow="SALES"
        title="Transactions"
        sub="Completed checkout history from smart trolleys."
      />

      <Panel flush>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Transaction</th>
                <th>Cart</th>
                <th>Items</th>
                <th>Total</th>
                <th>Time</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              {transactions.map(t => (
                <tr key={t.id}>
                  <td>
                    <b>{t.id}</b>
                  </td>

                  <td>{t.cart}</td>

                  <td>{t.items}</td>

                  <td>
                    <strong>{money(t.total)}</strong>
                  </td>

                  <td>{t.time}</td>

                  <td>
                    <span className="tag green">
                      Completed
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function Guardian(){

  const [alerts,setAlerts]=useState([]);
  const [loading,setLoading]=useState(true);


  // =====================================================
  // LOAD ALERTS
  // =====================================================

  const loadAlerts=async()=>{
    try {
      const data=await api("/alerts?include_resolved=true");
      setAlerts(data || []);
      setLoading(false);
    } catch(error) {
      console.error("Alerts load error:",error);
      setLoading(false);
    }
  };


  // =====================================================
  // AUTO REFRESH
  // =====================================================

  useEffect(()=>{

    loadAlerts();

    const interval=setInterval(()=>{

      loadAlerts();

    },3000);


    return ()=>clearInterval(interval);

  },[]);


  // =====================================================
  // ALERT COUNTS
  // =====================================================

  const activeAlerts=alerts.filter(
    alert=>alert.status!=="resolved"
  );


  const resolvedAlerts=alerts.filter(
    alert=>alert.status==="resolved"
  );


  const discrepancies=alerts.length;


  // =====================================================
  // RESOLVE ALERT
  // =====================================================

  const resolveAlert=async(id)=>{
    try {
      await api(`/alerts/${id}`, {method:"PUT", body:JSON.stringify({status:"resolved"})});
      setAlerts(current=>current.map(a=>a.id===id ? {...a,status:"resolved",resolved_at:new Date().toISOString()} : a));
    } catch(error) {
      console.error("Resolve alert error:",error);
      notify("Could not resolve alert");
    }
  };


  // =====================================================
  // PAGE
  // =====================================================

  return (

    <>

      <Head
        eyebrow="VERIFICATION"
        title="Retail Guardian"
        sub="Camera-free mismatch detection using RFID identity + load-cell weight."
      />


      {/* =================================================
          STAT CARDS
          ================================================= */}

      <div className="stats compact">

        <Stat
          label="Active Alerts"
          value={activeAlerts.length}
          meta="verification required"
          icon={<ShieldCheck/>}
        />


        <Stat
          label="Verified Today"
          value={resolvedAlerts.length}
          meta="alerts resolved"
          icon={<CheckCircle2/>}
        />


        <Stat
          label="Discrepancies"
          value={discrepancies}
          meta="total events"
          icon={<AlertTriangle/>}
        />


        <Stat
          label="System Health"
          value="Edge"
          meta="local processing"
          icon={<RefreshCw/>}
        />

      </div>


      {/* =================================================
          ALERT LIST
          ================================================= */}

      <Panel
        title="Recent verification events"
        sub="Latest events from local edge"
      >

        {loading ? (

          <div
            style={{
              padding:"24px"
            }}
          >

            <small>
              Loading verification events...
            </small>

          </div>

        ) : alerts.length===0 ? (

          <div
            style={{
              padding:"24px"
            }}
          >

            <small>
              No verification events yet.
            </small>

          </div>

        ) : (

          <div
            style={{
              width:"100%"
            }}
          >

            {alerts.map(alert=>{

              // =================================================
              // TROLLEY
              // =================================================

              const trolley =
                alert.trolleys?.trolley_number ||
                "Unknown Trolley";


              // =================================================
              // PRODUCT
              // =================================================

              const product =
                alert.products?.name ||
                "Unknown Product";


              // =================================================
              // TIME
              // =================================================

              const time =
                alert.created_at

                  ? new Date(
                      alert.created_at
                    ).toLocaleTimeString(
                      [],
                      {
                        hour:"2-digit",
                        minute:"2-digit"
                      }
                    )

                  : "-";


              // =================================================
              // TITLE
              // =================================================

              let title=
                "Verification Alert";


              if(
                alert.type==="weight_mismatch"
              ){

                title=
                  "Weight mismatch";

              }

              else if(
                alert.type==="unregistered_item"
              ){

                title=
                  "Unregistered item";

              }

              else if(
                alert.type==="inventory_discrepancy"
              ){

                title=
                  "Inventory discrepancy";

              }

              else if(alert.type){

                title=
                  alert.type.replaceAll(
                    "_",
                    " "
                  );

              }


              // =================================================
              // DETAIL
              // =================================================

              let detail=
                "Verification required";


              if(
                alert.type==="weight_mismatch"
              ){

                detail=
                  `${trolley} · Expected ${
                    alert.expected_value ?? "-"
                  }, detected ${
                    alert.actual_value ?? "-"
                  }`;

              }

              else if(
                alert.type==="unregistered_item"
              ){

                detail=
                  `${trolley} · Weight changed without matching RFID`;

              }

              else if(
                alert.type==="inventory_discrepancy"
              ){

                detail=
                  `${product} · Expected ${
                    alert.expected_value ?? "-"
                  }, detected ${
                    alert.actual_value ?? "-"
                  }`;

              }


              // =================================================
              // ALERT ROW
              // =================================================

              return (

  <div
    key={alert.id}
    className="guardian-event"
  >

    {/* ALERT INFORMATION */}

    <div className="guardian-event-info">

      <div className="guardian-event-title">

        <AlertTriangle size={15}/>

        <b>
          {title}
        </b>

        <span
          className={
            alert.status==="resolved"
              ? "tag green"
              : "tag red"
          }
        >
          {
            alert.status==="resolved"
              ? "Resolved"
              : "Active"
          }
        </span>

      </div>

      <small className="guardian-event-detail">
        {detail}
      </small>

    </div>


    {/* MISMATCH REASON */}

    <div className="guardian-event-reason">

      <span>
        Mismatch reason
      </span>

      {alert.type==="weight_mismatch" && (
        <>
          <b>
            {
              Number(alert.actual_value) >
              Number(alert.expected_value)
                ? "Extra weight detected"
                : "Weight below expected"
            }
          </b>

          <small>
            Expected {alert.expected_value ?? "-"} ·
            Detected {alert.actual_value ?? "-"}
          </small>
        </>
      )}

      {alert.type==="unregistered_item" && (
        <b>
          No matching RFID scan
        </b>
      )}

      {alert.type==="inventory_discrepancy" && (
        <b>
          Inventory count mismatch
        </b>
      )}

      {![
        "weight_mismatch",
        "unregistered_item",
        "inventory_discrepancy"
      ].includes(alert.type) && (
        <b>
          Verification required
        </b>
      )}

    </div>


    {/* TIME + RESOLVE */}

    <div className="guardian-event-action">

      <small className="guardian-event-time">
        {time}
      </small>

      {alert.status!=="resolved" ? (

        <button
          className="primary"
          onClick={()=>
            resolveAlert(alert.id)
          }
        >
          Resolve
        </button>

      ) : (

        <span className="guardian-event-placeholder"/>

      )}

    </div>

  </div>

);

            })}

          </div>

        )}

      </Panel>

    </>

  );

}

function AI({products}){
  const [ai,setAi]=useState({
    control:null,
    inventory:null,
    leaks:null,
    shopper:null,
    queue:null
  });
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [question,setQuestion]=useState("");
  const [answer,setAnswer]=useState(null);
  const [asking,setAsking]=useState(false);

  const loadAI=async()=>{
    try{
      setError("");
      const results=await Promise.allSettled([
        api("/ai/control-room"),
        api("/ai/inventory"),
        api("/ai/revenue-leaks"),
        api("/ai/shopper"),
        api("/ai/queue")
      ]);

      const [control,inventory,leaks,shopper,queue]=results.map(r=>
        r.status==="fulfilled" ? r.value : null
      );

      if(!control && !inventory && !leaks && !shopper && !queue){
        throw new Error("AI backend endpoints are unavailable");
      }

      setAi({control,inventory,leaks,shopper,queue});
    }catch(err){
      console.error("AI dashboard load error:",err);
      setError(err.message || "Unable to load AI intelligence");
    }finally{
      setLoading(false);
    }
  };

  useEffect(()=>{
    loadAI();
    const interval=setInterval(loadAI,10000);
    return()=>clearInterval(interval);
  },[]);

  const inventory=ai.inventory?.products || ai.control?.inventory || [];
  const leaks=ai.leaks?.items || ai.control?.revenue_leaks?.items || [];
  const actions=ai.control?.actions || [];
  const shopper=ai.shopper || ai.control?.shopper || {};
  const queue=ai.queue || ai.control?.queue || {};
  const kpis=ai.control?.kpis || {};

  const risky=inventory.filter(p=>
    ["critical","high"].includes(String(p.risk||"").toLowerCase())
  );

  const askAI=async()=>{
    const q=question.trim();
    if(!q) return;

    setAsking(true);
    setAnswer(null);

    try{
      const data=await api(`/ai/ask?q=${encodeURIComponent(q)}`);
      setAnswer(data);
    }catch(err){
      console.error("AI ask error:",err);
      setAnswer({
        answer:err.message || "AI answer unavailable",
        source:"local AI"
      });
    }finally{
      setAsking(false);
    }
  };

  const riskClass=(risk)=>{
    const r=String(risk||"").toLowerCase();
    if(r==="critical" || r==="high") return "tag red";
    if(r==="medium") return "tag amber";
    return "tag green";
  };

  const metricValue=(value,fallback="—")=>
    value===null || value===undefined ? fallback : value;

  return <>
    <Head
      eyebrow="LOCAL EDGE AI"
      title="AI Insights"
      sub="Detect → Explain → Recommend → Act using locally processed store data."
      action={
        <span className="tag green">
          <BrainCircuit size={13}/> CAMERA-FREE AI
        </span>
      }
    />

    {error && (
      <div
        className="panel"
        style={{marginBottom:"18px",borderColor:"rgba(251,113,133,.25)"}}
      >
        <div style={{display:"flex",alignItems:"center",gap:"10px"}}>
          <AlertTriangle size={17}/>
          <span>{error}</span>
          <button className="ghost" onClick={loadAI} style={{marginLeft:"auto"}}>
            <RefreshCw size={14}/> Retry
          </button>
        </div>
      </div>
    )}

    <div className="stats compact">
      <Stat
        label="High-risk SKUs"
        value={loading ? "…" : risky.length}
        meta="AI inventory risk"
        icon={<Boxes/>}
      />
      <Stat
        label="Revenue Exposure"
        value={loading ? "…" : money(kpis.revenue_exposure ?? ai.leaks?.estimated_exposure ?? 0)}
        meta="estimated local exposure"
        icon={<TrendingUp/>}
      />
      <Stat
        label="Avg Basket"
        value={loading ? "…" : money(shopper.avg_basket_value || 0)}
        meta="per completed transaction"
        icon={<ReceiptText/>}
      />
      <Stat
        label="Queue Risk"
        value={loading ? "…" : String(queue.congestion_risk || "low").toUpperCase()}
        meta={`15-min load ${metricValue(queue.predicted_load_in_15min,0)}`}
        icon={<AlertTriangle/>}
      />
    </div>

    <div className="two" style={{marginTop:"18px"}}>
      <Panel
        title="AI Action Engine"
        sub="Recommended actions generated from current store signals."
      >
        {actions.length===0 ? (
          <div style={{padding:"18px 0"}}>
            <small>{loading ? "Generating recommendations…" : "No action currently requires attention."}</small>
          </div>
        ) : actions.map((a,i)=>(
          <div
            key={`${a.action||"action"}-${i}`}
            className="recommend"
          >
            <div>
              <b>{a.title}</b>
              <span>{a.reason}</span>
            </div>
            <strong>
              {a.quantity ? `${a.quantity} units` : a.priority || "Review"}
              <ArrowUpRight size={14}/>
            </strong>
          </div>
        ))}
      </Panel>

      <Panel
        title="Queue Intelligence"
        sub={queue.data_note || "Local checkout demand prediction."}
      >
        <div className="detail-top">
          <span>
            <b>Waiting proxy</b>
            <small>{metricValue(queue.current_waiting_proxy,0)}</small>
          </span>
          <span>
            <b>Arrivals / 2h</b>
            <small>{metricValue(queue.arrivals_last_2h,0)}</small>
          </span>
          <span>
            <b>Service time</b>
            <small>{queue.avg_service_seconds != null ? `${queue.avg_service_seconds}s` : "—"}</small>
          </span>
        </div>

        <div style={{marginTop:"18px",display:"flex",alignItems:"center",justifyContent:"space-between",gap:"12px"}}>
          <span>Predicted 15-min load</span>
          <strong style={{fontSize:"22px"}}>{metricValue(queue.predicted_load_in_15min,0)}</strong>
        </div>
        <div style={{marginTop:"10px"}}>
          <span className={riskClass(queue.congestion_risk)}>
            {String(queue.congestion_risk || "low").toUpperCase()} CONGESTION RISK
          </span>
        </div>
      </Panel>
    </div>

    <Panel
      title="Inventory AI"
      sub="Demand forecast, stock-out prediction and reorder recommendation."
      flush
    >
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Stock</th>
              <th>7-day Forecast</th>
              <th>Stock-out</th>
              <th>Risk</th>
              <th>AI Recommendation</th>
            </tr>
          </thead>
          <tbody>
            {inventory.length===0 ? (
              <tr><td colSpan="6"><small>{loading ? "Loading AI inventory…" : "No AI inventory data available."}</small></td></tr>
            ) : inventory.slice(0,12).map(p=>(
              <tr key={p.id}>
                <td><b>{p.name}</b><small>{p.category || ""}</small></td>
                <td><strong>{p.current_stock}</strong></td>
                <td>{p.forecast_7d}</td>
                <td>{p.days_to_stockout == null ? "—" : `${p.days_to_stockout} days`}</td>
                <td><span className={riskClass(p.risk)}>{String(p.risk || "healthy")}</span></td>
                <td><strong>{Number(p.recommended_order_qty||0)>0 ? `Order ${p.recommended_order_qty}` : "Monitor"}</strong></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>

    <div className="two" style={{marginTop:"18px"}}>
      <Panel
        title="Revenue Leak Radar"
        sub="Potential exposure from stock-out risk, slow-moving capital and active Guardian events."
      >
        {leaks.length===0 ? (
          <div style={{padding:"18px 0"}}>
            <small>{loading ? "Scanning store signals…" : "No revenue-leak signals detected."}</small>
          </div>
        ) : leaks.slice(0,6).map((item,i)=>(
          <div key={`${item.type||"leak"}-${i}`} className="recommend">
            <div>
              <b>{item.title}</b>
              <span>{item.reason}</span>
            </div>
            <strong>{money(item.estimated_impact || 0)}</strong>
          </div>
        ))}
      </Panel>

      <Panel
        title="Shopper Intelligence"
        sub={shopper.analytics_mode || "Anonymous basket and interaction analytics."}
      >
        <div className="detail-top">
          <span>
            <b>Sessions</b>
            <small>{metricValue(shopper.sessions,0)}</small>
          </span>
          <span>
            <b>Items / Basket</b>
            <small>{metricValue(shopper.avg_items_per_basket,0)}</small>
          </span>
          <span>
            <b>Top Pairs</b>
            <small>{(shopper.top_product_pairs||[]).length}</small>
          </span>
        </div>
        <div style={{marginTop:"18px"}}>
          {(shopper.top_product_pairs||[]).slice(0,5).map((pair,i)=>(
            <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"10px 0",borderBottom:"1px solid rgba(148,163,184,.10)"}}>
              <span>{(pair.products||[]).join(" + ")}</span>
              <b>{pair.transactions} baskets</b>
            </div>
          ))}
        </div>
      </Panel>
    </div>

    <Panel
      title="Ask Local AI"
      sub="Ask the edge intelligence layer about inventory, shopper behaviour or checkout demand."
      action={<span className="tag green">OFFLINE-CAPABLE</span>}
    >
      <div style={{display:"flex",gap:"10px",flexWrap:"wrap"}}>
        {[
          "Which products need reorder?",
          "What is the queue risk?",
          "What is the average basket?"
        ].map(q=>(
          <button key={q} className="ghost" onClick={()=>setQuestion(q)}>{q}</button>
        ))}
      </div>

      <div style={{display:"flex",gap:"10px",marginTop:"14px"}}>
        <input
          value={question}
          onChange={e=>setQuestion(e.target.value)}
          onKeyDown={e=>{if(e.key==="Enter") askAI();}}
          placeholder="Ask: which products are at stock-out risk?"
          style={{flex:1,minWidth:"0"}}
        />
        <button className="primary" onClick={askAI} disabled={asking || !question.trim()}>
          {asking ? "Thinking…" : "Ask AI"}
        </button>
      </div>

      {answer && (
        <div
          style={{
            marginTop:"16px",
            padding:"16px",
            borderRadius:"14px",
            background:"rgba(99,102,241,.08)",
            border:"1px solid rgba(99,102,241,.16)"
          }}
        >
          <b style={{display:"block",marginBottom:"5px"}}>AI Response</b>
          <span>{answer.answer}</span>
          {answer.source && <small style={{display:"block",marginTop:"8px",opacity:.7}}>Source: {answer.source}</small>}
        </div>
      )}
    </Panel>
  </>;
}

function ShopperAnalytics(){
  const [shopper,setShopper]=useState(null);
  const [queue,setQueue]=useState(null);
  const [inventory,setInventory]=useState(null);
  const [loading,setLoading]=useState(true);

  const load=async()=>{
    try{
      const [s,q,i]=await Promise.all([
        api("/ai/shopper"),
        api("/ai/queue"),
        api("/ai/inventory")
      ]);
      setShopper(s || {});
      setQueue(q || {});
      setInventory(i || {});
    }catch(error){
      console.error("Shopper analytics AI error:",error);
    }finally{
      setLoading(false);
    }
  };

  useEffect(()=>{
    load();
    const interval=setInterval(load,10000);
    return()=>clearInterval(interval);
  },[]);

  const pairs=shopper?.top_product_pairs || [];
  const zones=shopper?.zone_activity || [];
  const queueRisk=String(queue?.congestion_risk || "low").toLowerCase();

  return <>
    <Head
      eyebrow="CUSTOMER INTELLIGENCE"
      title="Shopper Analytics"
      sub="Anonymous basket, product-pair and local checkout intelligence."
      action={<span className="tag green"><BrainCircuit size={13}/> CAMERA-FREE AI</span>}
    />

    <div className="stats compact">
      <Stat label="Avg Basket" value={loading ? "…" : money(shopper?.avg_basket_value || 0)} meta="per completed transaction" icon={<ReceiptText/>}/>
      <Stat label="Items / Basket" value={loading ? "…" : shopper?.avg_items_per_basket ?? 0} meta="average units" icon={<ShoppingCart/>}/>
      <Stat label="15-min Load" value={loading ? "…" : queue?.predicted_load_in_15min ?? 0} meta="predicted local demand" icon={<TrendingUp/>}/>
      <Stat label="Queue Risk" value={loading ? "…" : queueRisk.toUpperCase()} meta={queue?.data_ready ? "event data ready" : "proxy mode"} icon={<AlertTriangle/>}/>
    </div>

    <div className="two" style={{marginTop:"18px"}}>
      <Panel title="Basket Intelligence" sub={shopper?.data_note || shopper?.analytics_mode || "Local shopper intelligence."}>
        <div className="detail-top">
          <span><b>Sessions</b><small>{shopper?.sessions ?? 0}</small></span>
          <span><b>Avg basket</b><small>{money(shopper?.avg_basket_value || 0)}</small></span>
          <span><b>Items / basket</b><small>{shopper?.avg_items_per_basket ?? 0}</small></span>
        </div>

        <h4 style={{marginTop:"22px"}}>Frequently co-purchased</h4>
        {pairs.length===0 ? (
          <small>No product-pair data available yet.</small>
        ) : pairs.slice(0,8).map((pair,i)=>(
          <div key={i} className="recommend">
            <div><b>{(pair.products||[]).join(" + ")}</b><span>Observed together in completed baskets</span></div>
            <strong>{pair.transactions}</strong>
          </div>
        ))}
      </Panel>

      <Panel title="Queue Intelligence" sub={queue?.data_note || "Checkout load prediction."}>
        <div style={{padding:"18px 0"}}>
          <div style={{fontSize:"12px",opacity:.7}}>Current waiting proxy</div>
          <div style={{fontSize:"36px",fontWeight:800,marginTop:"5px"}}>{queue?.current_waiting_proxy ?? 0}</div>
        </div>
        <div className="detail-top">
          <span><b>Arrivals / 2h</b><small>{queue?.arrivals_last_2h ?? 0}</small></span>
          <span><b>Completed / 2h</b><small>{queue?.completions_last_2h ?? 0}</small></span>
          <span><b>Service</b><small>{queue?.avg_service_seconds != null ? `${queue.avg_service_seconds}s` : "—"}</small></span>
        </div>
        <div style={{marginTop:"18px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <span>Predicted 15-min load</span>
          <strong style={{fontSize:"22px"}}>{queue?.predicted_load_in_15min ?? 0}</strong>
        </div>
        <div style={{marginTop:"10px"}}><span className={queueRisk==="high" ? "tag red" : queueRisk==="medium" ? "tag amber" : "tag green"}>{queueRisk.toUpperCase()} RISK</span></div>
      </Panel>
    </div>

    <Panel title="Zone Activity" sub="Anonymous zone event analytics when local edge events are available.">
      {zones.length===0 ? (
        <div style={{padding:"18px 0"}}><small>Zone event data is not available yet. This panel stays ready for local sensor events.</small></div>
      ) : (
        <div className="table-wrap"><table><thead><tr><th>Zone</th><th>Visits</th><th>Avg Dwell</th></tr></thead><tbody>{zones.map((z,i)=><tr key={i}><td><b>{z.zone}</b></td><td>{z.visits}</td><td>{z.avg_dwell_seconds == null ? "—" : `${z.avg_dwell_seconds}s`}</td></tr>)}</tbody></table></div>
      )}
    </Panel>

    <Panel title="Inventory Signals for Shopper Context" sub="Cross-reference shopper demand with products at risk.">
      <div className="table-wrap"><table><thead><tr><th>Product</th><th>Units Sold</th><th>Forecast 7d</th><th>Risk</th></tr></thead><tbody>
        {(inventory?.products||[]).slice(0,8).map(p=><tr key={p.id}><td><b>{p.name}</b></td><td>{p.units_sold}</td><td>{p.forecast_7d}</td><td><span className={String(p.risk).toLowerCase()==="critical"||String(p.risk).toLowerCase()==="high"?"tag red":String(p.risk).toLowerCase()==="medium"?"tag amber":"tag green"}>{p.risk}</span></td></tr>)}
      </tbody></table></div>
    </Panel>
  </>;
}

function Notifications({ onMarkRead }) {

  const [alerts, setAlerts] = useState([]);
  const [movements, setMovements] = useState([]);
  const [products, setProducts] = useState([]);

  // ---------------------------------------------------------
  // Read notification IDs
  // ---------------------------------------------------------

  const [readNotificationIds, setReadNotificationIds] = useState(() => {

    try {

      const saved =
        localStorage.getItem(
          "smart-retail-read-notification-ids"
        );

      return saved
        ? JSON.parse(saved)
        : [];

    } catch (error) {

      console.error(
        "Read notification state error:",
        error
      );

      return [];

    }

  });


  // ---------------------------------------------------------
  // Load notifications data
  // ---------------------------------------------------------

  useEffect(() => {

    const loadNotifications = async () => {
      try {
        const [alertData, movementData, productResponse] = await Promise.all([
          api("/alerts?include_resolved=true"),
          api("/inventory-movements"),
          api("/products")
        ]);
        setAlerts(alertData || []);
        setMovements(movementData || []);
        setProducts(productResponse.products || productResponse || []);
      } catch(error) {
        console.error("Notifications load error:",error);
      }
    };


    // Initial load
    loadNotifications();


    // Refresh every 5 seconds
    const interval = setInterval(() => {

      loadNotifications();

    }, 5000);


    return () => clearInterval(interval);

  }, []);


  // =========================================================
  // LOW STOCK
  // =========================================================

  const lowStock = products.filter(
    p =>
      Number(p.current_stock) > 0 &&
      Number(p.current_stock) <=
        Number(p.minimum_stock)
  );


  // =========================================================
  // OUT OF STOCK
  // =========================================================

  const outOfStock = products.filter(
    p =>
      Number(p.current_stock) === 0
  );


  // =========================================================
  // BUILD ALL NOTIFICATIONS
  // =========================================================

  const notifications = [];


  // =========================================================
  // LOW STOCK NOTIFICATION
  // =========================================================

  if (lowStock.length > 0) {

    const lowStockId =
      "low-stock-" +
      lowStock
        .map(p =>
          `${p.id}-${p.current_stock}`
        )
        .sort()
        .join("|");


    notifications.push({

      id: lowStockId,

      type: "stock",

      title:
        `${lowStock.length} product${
          lowStock.length > 1
            ? "s"
            : ""
        } need replenishment`,

      detail:
        lowStock
          .slice(0, 3)
          .map(p => p.name)
          .join(", ") +
        (
          lowStock.length > 3
            ? " and other low-stock items"
            : ""
        ),

      time: null,

      timestamp: null

    });

  }


  // =========================================================
  // OUT OF STOCK NOTIFICATION
  // =========================================================

  if (outOfStock.length > 0) {

    const outStockId =
      "out-stock-" +
      outOfStock
        .map(p =>
          `${p.id}-${p.current_stock}`
        )
        .sort()
        .join("|");


    notifications.push({

      id: outStockId,

      type: "stock",

      title:
        `${outOfStock.length} product${
          outOfStock.length > 1
            ? "s"
            : ""
        } out of stock`,

      detail:
        outOfStock
          .slice(0, 3)
          .map(p => p.name)
          .join(", "),

      time: null,

      timestamp: null

    });

  }


  // =========================================================
  // ALERT NOTIFICATIONS
  // =========================================================

  alerts.forEach(alert => {

    const trolley =
      alert.trolleys?.trolley_number ||
      "Unknown Trolley";


    let title =
      "Verification required";


    let detail =
      `${trolley} · Verification event detected`;


    // Weight mismatch
    if (
      alert.type === "weight_mismatch"
    ) {

      title =
        "Weight mismatch";


      detail =
        `${trolley} · Expected ${
          alert.expected_value ?? "-"
        }, detected ${
          alert.actual_value ?? "-"
        }`;

    }


    // Unregistered item
    else if (
      alert.type === "unregistered_item"
    ) {

      title =
        "Unregistered item";


      detail =
        `${trolley} · Weight changed without matching RFID`;

    }


    // Inventory discrepancy
    else if (
      alert.type === "inventory_discrepancy"
    ) {

      title =
        "Inventory discrepancy";


      detail =
        `${alert.products?.name || "Product"} · Expected ${
          alert.expected_value ?? "-"
        }, detected ${
          alert.actual_value ?? "-"
        }`;

    }


    notifications.push({

      id:
        `alert-${alert.id}`,

      type:
        "alert",

      title,

      detail,

      time:
        alert.created_at
          ? new Date(
              alert.created_at
            ).toLocaleTimeString(
              [],
              {
                hour: "2-digit",
                minute: "2-digit"
              }
            )
          : "-",

      timestamp:
        alert.created_at

    });

  });


  // =========================================================
  // RECENT STOCK RECEIPTS
  // =========================================================

  movements
    .filter(
      m =>
        m.type === "PURCHASE"
    )
    .slice(0, 3)
    .forEach(m => {

      notifications.push({

        id:
          `purchase-${m.id}`,

        type:
          "purchase",

        title:
          "Stock received",

        detail:
          `${m.products?.name || "Product"} · ` +
          `${m.quantity} units added to inventory`,

        time:
          m.created_at
            ? new Date(
                m.created_at
              ).toLocaleTimeString(
                [],
                {
                  hour: "2-digit",
                  minute: "2-digit"
                }
              )
            : "-",

        timestamp:
          m.created_at

      });

    });


  // =========================================================
  // SORT NEWEST FIRST
  // =========================================================

  notifications.sort((a, b) => {

    // Notifications without timestamps
    // stay at the top
    if (!a.timestamp) return -1;

    if (!b.timestamp) return 1;


    return (
      new Date(b.timestamp) -
      new Date(a.timestamp)
    );

  });


  // =========================================================
  // ONLY SHOW UNREAD NOTIFICATIONS
  // =========================================================

  const unreadNotifications =
    notifications.filter(
      notification =>
        !readNotificationIds.includes(
          notification.id
        )
    );


  // =========================================================
  // MARK ALL AS READ
  // =========================================================

  const handleMarkAllRead = () => {

    const currentIds =
      notifications.map(
        notification =>
          notification.id
      );


    if (currentIds.length === 0) {

      return;

    }


    const updatedIds =
      Array.from(
        new Set([
          ...readNotificationIds,
          ...currentIds
        ])
      );


    setReadNotificationIds(
      updatedIds
    );


    localStorage.setItem(
      "smart-retail-read-notification-ids",
      JSON.stringify(
        updatedIds
      )
    );


    // Update sidebar badge
    if (onMarkRead) {

      onMarkRead();

    }

  };


  // =========================================================
  // UI
  // =========================================================

  return (

    <div className="notifications-page">

      <Head
        eyebrow="INBOX"
        title="Notifications"
        sub="Alerts, verification events and store updates."
      />


      {/* =================================================
          ACTION BAR
          ================================================= */}

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          alignItems: "center",
          marginBottom: "16px"
        }}
      >

        {unreadNotifications.length > 0 && (

          <button
            className="ghost"
            onClick={
              handleMarkAllRead
            }
            style={{
              padding: "9px 14px",
              fontSize: "12px",
              fontWeight: 600
            }}
          >

            ✓ Mark all as read

          </button>

        )}

      </div>


      {/* =================================================
          NOTIFICATION PANEL
          ================================================= */}

      <Panel
        title="Store notifications"
        sub="Live updates from the local edge system."
      >

        {unreadNotifications.length === 0 ? (

          <div
            style={{
              padding: "42px 24px",
              textAlign: "center"
            }}
          >

            <div
              style={{
                fontSize: "28px",
                marginBottom: "10px",
                opacity: 0.8
              }}
            >
              ✓
            </div>


            <b
              style={{
                display: "block",
                fontSize: "14px",
                marginBottom: "5px"
              }}
            >
              No notifications yet
            </b>


            <small
              style={{
                opacity: 0.7
              }}
            >
              You're all caught up.
            </small>

          </div>

        ) : (

          unreadNotifications.map(
            n => {

              // =================================================
              // ICON
              // =================================================

              let icon =
                <AlertTriangle
                  size={16}
                />;


              if (
                n.type === "purchase"
              ) {

                icon =
                  <CheckCircle2
                    size={16}
                  />;

              }


              // =================================================
              // BADGE
              // =================================================

              let badgeText =
                "Alert";


              let badgeClass =
                "tag red";


              if (
                n.type === "stock"
              ) {

                badgeText =
                  "Inventory";

              }


              if (
                n.type === "purchase"
              ) {

                badgeText =
                  "Received";

                badgeClass =
                  "tag green";

              }


              // =================================================
              // ROW
              // =================================================

              return (

                <div
                  key={n.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "34px minmax(0,1fr) auto",
                    alignItems: "center",
                    gap: "14px",
                    padding: "15px 0",
                    borderBottom:
                      "1px solid rgba(148,163,184,.10)"
                  }}
                >

                  {/* ICON */}

                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "9px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background:
                        n.type === "purchase"
                          ? "rgba(16,185,129,.10)"
                          : "rgba(139,92,246,.12)",
                      color:
                        n.type === "purchase"
                          ? "#34d399"
                          : "#a78bfa",
                      flexShrink: 0
                    }}
                  >

                    {icon}

                  </div>


                  {/* INFORMATION */}

                  <div
                    style={{
                      minWidth: 0
                    }}
                  >

                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "9px",
                        flexWrap: "wrap"
                      }}
                    >

                      <b>
                        {n.title}
                      </b>


                      <span
                        className={
                          badgeClass
                        }
                      >
                        {badgeText}
                      </span>

                    </div>


                    <small
                      style={{
                        display: "block",
                        marginTop: "4px",
                        color:
                          "rgba(148,163,184,.85)"
                      }}
                    >

                      {n.detail}

                    </small>

                  </div>


                  {/* TIME */}

                  <small
                    style={{
                      minWidth: "48px",
                      textAlign: "right",
                      whiteSpace: "nowrap",
                      color:
                        "rgba(148,163,184,.75)"
                    }}
                  >

                    {n.time || "Current"}

                  </small>

                </div>

              );

            }
          )

        )}

      </Panel>

    </div>

  );

}
function SettingsPage(){ 
 
  const [storeName,setStoreName]=useState( 
    localStorage.getItem("smart-retail-store-name") || 
    "Smart Retail Store 01" 
  ); 
 
  const [storeId,setStoreId]=useState( 
    localStorage.getItem("smart-retail-store-id") || 
    "STORE-01" 
  ); 
 
  const [currency,setCurrency]=useState( 
    localStorage.getItem("smart-retail-currency") || 
    "INR" 
  ); 
 
  const [lowStockAlerts,setLowStockAlerts]=useState( 
    localStorage.getItem("smart-retail-low-stock-alerts") || 
    "on" 
  ); 
 
  const [minimumStock,setMinimumStock]=useState( 
    localStorage.getItem("smart-retail-default-minimum") || 
    "5" 
  ); 
 
  const [openingTime,setOpeningTime]=useState( 
    localStorage.getItem("smart-retail-opening-time") || 
    "09:00" 
  ); 
 
  const [closingTime,setClosingTime]=useState( 
    localStorage.getItem("smart-retail-closing-time") || 
    "22:00" 
  ); 

  /* =====================================================
     TROLLEY OPERATION SETTINGS
     ===================================================== */

  const [requireVerification,setRequireVerification]=useState(
    localStorage.getItem(
      "smart-retail-require-verification"
    ) !== "off"
  );

  const [autoResetTrolley,setAutoResetTrolley]=useState(
    localStorage.getItem(
      "smart-retail-auto-reset-trolley"
    ) !== "off"
  );

  const [saved,setSaved]=useState(false); 


  /* =====================================================
     SAVE ALL SETTINGS
     ===================================================== */

  const saveStoreSettings=()=>{ 

    /* ================= STORE SETTINGS ================= */

    localStorage.setItem(
      "smart-retail-store-name",
      storeName
    );

    localStorage.setItem(
      "smart-retail-store-id",
      storeId
    );

    localStorage.setItem(
      "smart-retail-currency",
      currency
    );

    localStorage.setItem(
      "smart-retail-low-stock-alerts",
      lowStockAlerts
    );

    localStorage.setItem(
      "smart-retail-default-minimum",
      minimumStock
    );

    localStorage.setItem(
      "smart-retail-opening-time",
      openingTime
    );

    localStorage.setItem(
      "smart-retail-closing-time",
      closingTime
    );


    /* ============== TROLLEY SETTINGS ============== */

    localStorage.setItem(
      "smart-retail-require-verification",
      requireVerification ? "on" : "off"
    );

    localStorage.setItem(
      "smart-retail-auto-reset-trolley",
      autoResetTrolley ? "on" : "off"
    );


    /* =================================================
       INFORM MAIN APP ABOUT SETTINGS CHANGES
       ================================================= */

    window.dispatchEvent(
      new Event("smart-retail-settings-changed")
    );

    window.dispatchEvent(
      new Event("store-settings-changed")
    );

    window.dispatchEvent(
      new Event("store-name-changed")
    );

    window.dispatchEvent(
      new Event("store-id-changed")
    );

    window.dispatchEvent(
      new Event("currency-changed")
    );

    window.dispatchEvent(
      new Event("low-stock-settings-changed")
    );

    window.dispatchEvent(
      new Event("minimum-stock-changed")
    );

    window.dispatchEvent(
      new Event("store-hours-changed")
    );

    window.dispatchEvent(
      new Event("trolley-settings-changed")
    );


    /* ================= SAVED MESSAGE ================= */

    setSaved(true);

    setTimeout(()=>{
      setSaved(false);
    },2000);

  };


  return ( 
 
    <div className="settings-page">

      <Head 
        eyebrow="CONFIGURATION" 
        title="Settings" 
        sub="Store, trolley, edge and notification preferences." 
      /> 


      {/* =====================================================
          STORE CONFIGURATION
          ===================================================== */}

      <div className="two"> 
 
        <Panel 
          title="Store configuration" 
          sub="Basic information and operating preferences." 
        > 
 
          <div className="form-grid"> 

            {/* STORE NAME */}

            <label> 
              Store name 
 
              <input 
                value={storeName} 
                onChange={e => 
                  setStoreName(e.target.value) 
                } 
                placeholder="Smart Retail Store 01" 
              /> 
            </label> 


            {/* STORE ID */}

            <label> 
              Store ID 
 
              <input 
                value={storeId} 
                onChange={e => 
                  setStoreId(e.target.value) 
                } 
                placeholder="STORE-01" 
              /> 
            </label> 


            {/* CURRENCY */}

            <label> 
              Currency 
 
              <select 
                value={currency} 
                onChange={e => 
                  setCurrency(e.target.value) 
                } 
              > 
 
                <option value="INR"> 
                  Indian Rupee (₹) 
                </option> 
 
                <option value="USD"> 
                  US Dollar ($) 
                </option> 
 
              </select> 
            </label> 


            {/* MINIMUM STOCK */}

            <label> 
              Default minimum stock 
 
              <input 
                type="number" 
                min="0" 
                value={minimumStock} 
                onChange={e => 
                  setMinimumStock(e.target.value) 
                } 
              /> 
            </label> 


            {/* OPENING TIME */}

            <label> 
              Opening time 
 
              <input 
                type="time" 
                value={openingTime} 
                onChange={e => 
                  setOpeningTime(e.target.value) 
                } 
              /> 
            </label> 


            {/* CLOSING TIME */}

            <label> 
              Closing time 
 
              <input 
                type="time" 
                value={closingTime} 
                onChange={e => 
                  setClosingTime(e.target.value) 
                } 
              /> 
            </label> 

          </div> 


          {/* SAVE BUTTON */}

          <div 
            style={{ 
              display:"flex", 
              justifyContent:"flex-end", 
              alignItems:"center", 
              gap:"12px", 
              marginTop:"20px" 
            }} 
          > 
 
            {saved && ( 
              <span className="tag green"> 
                Settings saved 
              </span> 
            )} 
 
            <button 
              className="primary" 
              onClick={saveStoreSettings} 
            > 
              Save changes 
            </button> 
 
          </div> 
 
        </Panel> 


        {/* =================================================
            STORE ALERTS
            ================================================= */}

        <Panel 
          title="Store alerts" 
          sub="Control inventory notifications." 
        > 
 
          <label className="setting"> 
 
            Low-stock alerts 
 
            <select 
              value={lowStockAlerts} 
              onChange={e => 
                setLowStockAlerts(e.target.value) 
              } 
            > 
 
              <option value="on"> 
                Enabled 
              </option> 
 
              <option value="off"> 
                Disabled 
              </option> 
 
            </select> 
 
          </label> 


          <div 
            style={{ 
              marginTop:"18px", 
              padding:"14px 16px", 
              borderRadius:"12px", 
              background:"rgba(124,77,255,.06)", 
              border:"1px solid rgba(124,77,255,.16)" 
            }} 
          > 
 
            <small> 
              Products at or below the minimum 
              stock threshold will appear in 
              inventory attention and notification 
              areas. 
            </small> 
 
          </div> 


          <div style={{marginTop:"20px"}}> 
 
            <SettingRow 
              title="Local Edge Processing" 
              sub="Store data is processed by the local edge system." 
              tag="Active" 
            /> 
 
          </div> 
 
        </Panel> 

      </div> 


      {/* =====================================================
          TROLLEY OPERATIONS
          ===================================================== */}

      <div style={{marginTop:"18px"}}>

        <Panel
          title="Trolley operations"
          sub="Control checkout and trolley reset behavior."
        >

          <SettingRow
            title="Require verification before checkout"
            sub="Prevent checkout when an item still needs verification."
            tag={requireVerification ? "Enabled" : "Disabled"}
          />

          <div
            style={{
              display:"flex",
              justifyContent:"flex-end",
              marginTop:"-48px",
              marginBottom:"28px"
            }}
          >

            <input
              type="checkbox"
              checked={requireVerification}
              onChange={e =>
                setRequireVerification(e.target.checked)
              }
              style={{
                width:"18px",
                height:"18px",
                accentColor:"#7c4dff",
                cursor:"pointer"
              }}
            />

          </div>


          <SettingRow
            title="Auto reset trolley after checkout"
            sub="Clear the trolley and make it available after successful payment."
            tag={autoResetTrolley ? "Enabled" : "Disabled"}
          />

          <div
            style={{
              display:"flex",
              justifyContent:"flex-end",
              marginTop:"-48px",
              marginBottom:"8px"
            }}
          >

            <input
              type="checkbox"
              checked={autoResetTrolley}
              onChange={e =>
                setAutoResetTrolley(e.target.checked)
              }
              style={{
                width:"18px",
                height:"18px",
                accentColor:"#7c4dff",
                cursor:"pointer"
              }}
            />

          </div>


          <div
            style={{
              display:"flex",
              justifyContent:"flex-end",
              alignItems:"center",
              gap:"12px",
              marginTop:"20px"
            }}
          >

            {saved && (
              <span className="tag green">
                Settings saved
              </span>
            )}

            <button
              className="primary"
              onClick={saveStoreSettings}
            >
              Save changes
            </button>

          </div>

        </Panel>

      </div>


      {/* =====================================================
          SYSTEM ARCHITECTURE
          ===================================================== */}

      <div style={{marginTop:"18px"}}> 
 
        <Panel 
          title="System architecture" 
          sub="Current deployment characteristics." 
        > 
 
          <SettingRow 
            title="Local Edge Server" 
            sub="Primary processing and local database" 
            tag="Active" 
          /> 
 
          <SettingRow 
            title="Cloud Dependency" 
            sub="System operates without internet access" 
            tag="Zero-Cloud" 
          /> 
 
          <SettingRow 
            title="Camera System" 
            sub="RFID + load-cell verification only" 
            tag="Camera-free" 
          /> 
 
        </Panel> 
 
      </div> 

    </div>
 
  ); 
 
}
function SettingRow({title,sub,tag}){return <div className="setting-row"><div><b>{title}</b><span>{sub}</span></div><span className="tag green">{tag}</span></div>}

function ProductModal({close,submit,product}){
  return (
    <Modal
      title="Add Product"
      sub="Create a product and map its RFID tag."
      close={close}
    >
      <form onSubmit={submit}>
        <div className="form-grid">

          <label>
            Name
           <input
  name="name"
  required
  placeholder="e.g. Amul Taaza Milk 1L"
  defaultValue={product?.name || ""}
/>
          </label>

          <label>
            RFID Tag ID
            <input
  name="rfid"
  required
  placeholder="e.g. RFID-MILK-002"
  defaultValue={product?.rfid_tag || ""}
/>
          </label>

          <label>
            Category
            <input
  name="category"
  required
  placeholder="e.g. Dairy"
  defaultValue={product?.category || ""}
/>
          </label>

          <label>
            Supplier
            <input
  name="supplier"
  required
  placeholder="e.g. Amul"
  defaultValue={product?.supplier || ""}
/>
          </label>

          <label>
            Weight (kg)
            <input
  name="weight"
  type="number"
  step="0.001"
  min="0"
  required
  defaultValue={product?.unit_weight ?? ""}
/>
          </label>

          <label>
            Selling Price (₹)
           <input
  name="price"
  type="number"
  min="0"
  required
  defaultValue={product?.price ?? ""}
/>
          </label>

          <label>
            Purchase Cost (₹)
            <input
  name="cost"
  type="number"
  min="0"
  required
  defaultValue={product?.purchase_price ?? ""}
/>
          </label>

          <label>
            Current Stock
            <input
  name="stock"
  type="number"
  min="0"
  required
  defaultValue={product?.current_stock ?? ""}
/>
          </label>

          <label>
            Minimum Stock
            <input
  name="min"
  type="number"
  min="0"
  required
  defaultValue={product?.minimum_stock ?? ""}
/>
          </label>

        </div>

        <ModalActions
          close={close}
          label={product ? "Update Product" : "Add Product"}
        />
      </form>
    </Modal>
  );
}
function OrderModal({close,submit,products}){return <Modal title="New Stock Order" sub="Record a purchase order from a supplier." close={close}><form onSubmit={submit}><div className="form-grid"><label>Supplier<input name="supplier" required placeholder="e.g. Amul Distributor"/></label><label>Product<select name="product" required>{products.map(p=><option key={p.id}>{p.name}</option>)}</select></label><label>Quantity<input name="qty" type="number" min="1" required placeholder="50"/></label><label>Expected arrival<input name="arrival" type="date"/></label></div><div className="order-note"><Truck size={16}/><span>The order stays <b>Pending</b> until stock is received. Receiving it will automatically increase inventory.</span></div><ModalActions close={close} label="Create Order"/></form></Modal>}
function Modal({title,sub,close,children}){return <div className="overlay"><div className="modal"><div className="modal-head"><div><h2>{title}</h2><p>{sub}</p></div><button onClick={close}><X size={18}/></button></div>{children}</div></div>}
function ModalActions({close,label}){return <div className="modal-actions"><button type="button" className="ghost" onClick={close}>Cancel</button><button className="primary"><CheckCircle2 size={15}/>{label}</button></div>}

createRoot(document.getElementById("root")).render(<App/>);



