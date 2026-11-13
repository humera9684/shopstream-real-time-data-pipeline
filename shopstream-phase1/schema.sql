CREATE TABLE IF NOT EXISTS product_sales (
    product_id INTEGER PRIMARY KEY,
    units_sold BIGINT NOT NULL DEFAULT 0,
    total_revenue NUMERIC(18, 2) NOT NULL DEFAULT 0,
    order_lines BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS analytics_processed_events (
    event_id UUID PRIMARY KEY,
    order_id VARCHAR(100) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS processed_order_events (
    event_id UUID PRIMARY KEY,
    order_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS public.orders
(
    id serial NOT NULL,
    customer_name character varying(120) COLLATE pg_catalog."default" NOT NULL,
    customer_email character varying(200) COLLATE pg_catalog."default" NOT NULL,
    total numeric(12,2) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    status character varying(30) COLLATE pg_catalog."default" NOT NULL,
    user_id integer,
    CONSTRAINT orders_pkey PRIMARY KEY (id),
    CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;




CREATE TABLE IF NOT EXISTS public.product_sales
(
    product_id integer NOT NULL,
    units_sold bigint NOT NULL DEFAULT 0,
    total_revenue numeric(18,2) NOT NULL DEFAULT 0,
    order_lines bigint NOT NULL DEFAULT 0,
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT product_sales_pkey PRIMARY KEY (product_id)
)

TABLESPACE pg_default;