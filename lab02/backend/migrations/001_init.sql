-- ============================================
-- Схема базы данных маркетплейса
-- ============================================

-- Включаем расширение UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


CREATE TYPE status_type AS ENUM ('created', 'paid', 'cancelled', 'shipped', 'completed');


CREATE TABLE IF NOT EXISTS order_statuses (
    status      VARCHAR(100) PRIMARY KEY,
    description VARCHAR(100)
);

INSERT INTO order_statuses (status, description) VALUES
    ('created',   'Заказ создан'),
    ('paid',      'Заказ оплачен'),
    ('cancelled', 'Заказ отменён'),
    ('shipped',   'Заказ отправлен'),
    ('completed', 'Заказ завершён')
ON CONFLICT (status) DO NOTHING;


CREATE TABLE IF NOT EXISTS users (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email      VARCHAR(254) NOT NULL UNIQUE,
    name       VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT check_name_not_empty
        CHECK (TRIM(name) <> ''),

    CONSTRAINT check_email_not_empty
        CHECK (TRIM(email) <> ''),

    CONSTRAINT check_email_format 
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);


CREATE TABLE IF NOT EXISTS orders (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL,
    status       VARCHAR(100) NOT NULL DEFAULT 'created',
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT orders_user_fk 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

    CONSTRAINT orders_status_fk 
        FOREIGN KEY (status) REFERENCES order_statuses(status),

    CONSTRAINT orders_total_amount_not_negative 
        CHECK (total_amount >= 0)
);


CREATE TABLE IF NOT EXISTS order_items (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id     UUID NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    price        NUMERIC(10,2) NOT NULL,
    quantity     INTEGER NOT NULL,

    CONSTRAINT order_items_order_fk 
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,

    CONSTRAINT order_items_price_not_negative 
        CHECK (price >= 0),

    CONSTRAINT order_items_quantity_positive 
        CHECK (quantity > 0),

    CONSTRAINT order_items_product_name_not_empty 
        CHECK (TRIM(product_name) <> '')
);


CREATE TABLE IF NOT EXISTS order_status_history (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id   UUID NOT NULL,
    status     VARCHAR(100) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT order_status_history_order_fk 
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,

    CONSTRAINT order_status_history_status_fk 
        FOREIGN KEY (status) REFERENCES order_statuses(status)
);

-- ============================================
-- КРИТИЧЕСКИЙ ИНВАРИАНТ: Нельзя оплатить заказ дважды
-- ============================================


CREATE OR REPLACE FUNCTION check_order_not_already_paid()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'paid' AND OLD.status <> 'paid' THEN
        IF EXISTS (
            SELECT 1 
            FROM order_status_history 
            WHERE order_id = NEW.id 
              AND status = 'paid'
        ) THEN
            RAISE EXCEPTION 'Order % cannot be paid twice!', NEW.id
            USING ERRCODE = '23505';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_order_not_already_paid
    BEFORE UPDATE ON orders
    FOR EACH ROW
    WHEN (NEW.status IS DISTINCT FROM OLD.status)
    EXECUTE FUNCTION check_order_not_already_paid();


-- ============================================
-- БОНУС (опционально)
-- ============================================


-- 1. Автоматическая запись начального статуса при создании заказа
CREATE OR REPLACE FUNCTION record_initial_order_status()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO order_status_history (order_id, status, changed_at)
    VALUES (NEW.id, 'created', NEW.created_at);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_record_initial_status
    AFTER INSERT ON orders
    FOR EACH ROW
    EXECUTE FUNCTION record_initial_order_status();

-- 2. Автоматическая запись в историю при изменении статуса
CREATE OR REPLACE FUNCTION record_order_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO order_status_history (order_id, status, changed_at)
        VALUES (NEW.id, NEW.status, NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_record_status_history
    AFTER UPDATE OF status ON orders
    FOR EACH ROW
    EXECUTE FUNCTION record_order_status_change();

-- 3. Автоматический пересчёт total_amount при изменении позиций
CREATE OR REPLACE FUNCTION recalculate_order_total()
RETURNS TRIGGER AS $$
DECLARE
    new_total NUMERIC(12,2);
BEGIN
    SELECT COALESCE(SUM(price * quantity), 0)
    INTO new_total
    FROM order_items
    WHERE order_id = COALESCE(NEW.order_id, OLD.order_id);

    UPDATE orders
    SET total_amount = new_total
    WHERE id = COALESCE(NEW.order_id, OLD.order_id);

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_recalculate_total_on_item_change
    AFTER INSERT OR UPDATE OR DELETE ON order_items
    FOR EACH ROW
    EXECUTE FUNCTION recalculate_order_total();