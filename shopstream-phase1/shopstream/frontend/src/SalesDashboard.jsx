
import React, { useEffect, useState } from "react";

const API_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const money = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);

export default function SalesDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadSales() {
      try {
        const response = await fetch(
          `${API_URL}/analytics/summary`
        );

        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }

        const result = await response.json();

        if (active) {
          setData(result);
          setError("");
        }
      } catch (err) {
        if (active) {
          setError(err.message);
        }
      }
    }

    loadSales();

    // Refresh analytics every 10 seconds
    const interval = setInterval(loadSales, 10000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  if (!data) {
    return <p>{error || "Loading sales analytics..."}</p>;
  }

  const maxRevenue = Math.max(
    1,
    ...data.products.map((p) => p.total_revenue)
  );

  return (
    <main style={{ padding: 32, maxWidth: 1100, margin: "auto" }}>
      <h1>ShopStream Sales Analytics</h1>
      <p>Automatically refreshes every 10 seconds</p>

      {error && <p role="alert">Refresh failed: {error}</p>}

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        gap: 16,
        marginBottom: 32,
      }}>
        {[
          ["Total revenue", money(data.revenue)],
          ["Units sold", data.units_sold],
          ["Products sold", data.products_sold],
          ["Order lines", data.order_lines],
        ].map(([label, value]) => (
          <div key={label} style={{
            padding: 22,
            border: "1px solid #ddd",
            borderRadius: 12,
          }}>
            <p>{label}</p>
            <h2>{value}</h2>
          </div>
        ))}
      </div>

      <h2>Revenue by Product</h2>

      {data.products.map((product) => (
        <div key={product.product_id} style={{ marginBottom: 20 }}>
          <div style={{
            display: "flex",
            justifyContent: "space-between",
          }}>
            <strong>
              {product.product_name || "Unknown product"}{" "}
              <small style={{ fontWeight: "normal", color: "#6b7280" }}>
                (ID {product.product_id})
              </small>
            </strong>
            <span>{money(product.total_revenue)}</span>
          </div>

          <div style={{
            height: 14,
            background: "#e5e7eb",
            borderRadius: 8,
            marginTop: 8,
            overflow: "hidden",
          }}>
            <div style={{
              height: "100%",
              width: `${product.total_revenue / maxRevenue * 100}%`,
              background: "#0d9488",
            }} />
          </div>

          <small>{product.units_sold} units sold</small>
        </div>
      ))}
    </main>
  );
}

