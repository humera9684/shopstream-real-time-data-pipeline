
import os

from fastapi import APIRouter
from sqlalchemy import create_engine, text

router = APIRouter(prefix="/analytics", tags=["Analytics"])

engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_pre_ping=True
)


@router.get("/summary")
def sales_summary():
    with engine.connect() as conn:
        summary = conn.execute(text("""
            SELECT
                COALESCE(SUM(total_revenue), 0) AS revenue,
                COALESCE(SUM(units_sold), 0) AS units_sold,
                COUNT(*) AS products_sold,
                COALESCE(SUM(order_lines), 0) AS order_lines
            FROM product_sales
        """)).mappings().one()

        products = conn.execute(text("""
            SELECT
                ps.product_id,
                p.name AS product_name,
                ps.units_sold,
                ps.total_revenue,
                ps.order_lines
            FROM product_sales ps
            LEFT JOIN products p ON p.id = ps.product_id
            ORDER BY ps.total_revenue DESC
        """)).mappings().all()

    return {
        "revenue": float(summary["revenue"]),
        "units_sold": int(summary["units_sold"]),
        "products_sold": int(summary["products_sold"]),
        "order_lines": int(summary["order_lines"]),
        "products": [
            {
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "units_sold": row["units_sold"],
                "total_revenue": float(row["total_revenue"]),
                "order_lines": row["order_lines"]
            }
            for row in products
        ]
    }
