# Быстрый старт - Лабораторная работа №2

## Запуск проекта

```bash
cd lab_02
docker-compose up --build
```

## Что нужно сделать

### Шаг 1: Реализовать PaymentService

Откройте `backend/app/application/payment_service.py`

Реализуйте три метода:

1. **pay_order_unsafe()** - НЕ использует FOR UPDATE, НЕ меняет isolation level
2. **pay_order_safe()** - использует REPEATABLE READ + FOR UPDATE
3. **get_payment_history()** - возвращает историю оплат

Следуйте TODO комментариям в файле - там подробные инструкции.

### Шаг 2: Реализовать тесты

#### Тест 1: test_concurrent_payment_unsafe.py

Откройте `backend/app/tests/test_concurrent_payment_unsafe.py`

Реализуйте:
- Фикстуру `db_session` - создание сессии БД
- Фикстуру `test_order` - создание тестового заказа
- Тест, который запускает два параллельных `pay_order_unsafe()`

```python
results = await asyncio.gather(
    service1.pay_order_unsafe(order_id),
    service2.pay_order_unsafe(order_id),
    return_exceptions=True
)

# Проверить, что в истории ДВЕ записи 'paid'
history = await service.get_payment_history(order_id)
assert len(history) == 2, "Ожидалось 2 записи (RACE CONDITION!)"
```

#### Тест 2: test_concurrent_payment_safe.py

Откройте `backend/app/tests/test_concurrent_payment_safe.py`

Реализуйте аналогичный тест, но с `pay_order_safe()`:

```python
results = await asyncio.gather(
    service1.pay_order_safe(order_id),
    service2.pay_order_safe(order_id),
    return_exceptions=True
)

# Проверить, что в истории ОДНА запись 'paid'
history = await service.get_payment_history(order_id)
assert len(history) == 1, "Ожидалась 1 запись (БЕЗ RACE CONDITION!)"
```

### Шаг 3: Запустить тесты

```bash
cd backend
export PYTHONPATH=$(pwd)

# Тест с проблемой
pytest app/tests/test_concurrent_payment_unsafe.py -v -s

# Тест с решением
pytest app/tests/test_concurrent_payment_safe.py -v -s
```

### Шаг 4: Заполнить отчёт

Откройте `REPORT.md` и заполните все секции с TODO.

## Ожидаемый результат

### test_concurrent_payment_unsafe.py

```
test_concurrent_payment_unsafe_demonstrates_race_condition PASSED

⚠️ RACE CONDITION DETECTED!
Order b0000000-0000-0000-0000-000000000001 was paid TWICE:
  - 2024-02-21 10:30:45: status = paid
  - 2024-02-21 10:30:45: status = paid
```

### test_concurrent_payment_safe.py

```
test_concurrent_payment_safe_prevents_race_condition PASSED

✅ RACE CONDITION PREVENTED!
Order b0000000-0000-0000-0000-000000000002 was paid only ONCE:
  - 2024-02-21 10:31:15: status = paid
Second attempt was rejected: OrderAlreadyPaidError('Order already paid')
```

## Подсказки

### Создание независимых сессий

Каждая "попытка оплаты" должна иметь свою сессию (имитируя независимые HTTP-запросы):

```python
async def payment_attempt_1():
    async with AsyncSession(engine) as session1:
        service = PaymentService(session1)
        return await service.pay_order_unsafe(order_id)

async def payment_attempt_2():
    async with AsyncSession(engine) as session2:
        service = PaymentService(session2)
        return await service.pay_order_unsafe(order_id)

results = await asyncio.gather(
    payment_attempt_1(),
    payment_attempt_2(),
    return_exceptions=True
)
```

### Установка isolation level

```python
await session.execute(
    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
)
```

### Использование FOR UPDATE

```python
result = await session.execute(
    text("SELECT status FROM orders WHERE id = :order_id FOR UPDATE"),
    {"order_id": order_id}
)
status = result.scalar()
```

### Работа с транзакциями

```python
async with session.begin():
    # Все операции внутри транзакции
    # Автоматический COMMIT или ROLLBACK
    pass
```

## Частые ошибки

❌ **Использовать одну сессию для обеих попыток оплаты**  
✅ Создавать ДВЕ независимые сессии

❌ **Забыть `return_exceptions=True` в `asyncio.gather()`**  
✅ Всегда использовать `return_exceptions=True`

❌ **Использовать FOR UPDATE в pay_order_unsafe()**  
✅ В unsafe версии БЕЗ блокировок!

❌ **Не устанавливать REPEATABLE READ в pay_order_safe()**  
✅ Обязательно установить уровень изоляции

❌ **Ожидать, что test_concurrent_payment_unsafe НЕ пройдет**  
✅ Тест ДОЛЖЕН ПРОЙТИ, подтверждая наличие проблемы

## Проверка работы блокировок

Чтобы убедиться, что FOR UPDATE действительно блокирует:

```python
async def payment_attempt_1():
    async with AsyncSession(engine) as session:
        await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        await session.execute(text("SELECT * FROM orders WHERE id = :id FOR UPDATE"), {"id": order_id})
        
        # Добавить задержку
        await asyncio.sleep(2)
        
        # Остальная логика...
        await session.commit()

# Вторая попытка будет ЖДАТЬ эти 2 секунды
```

## Структура файлов

```
lab_02/backend/app/
├── application/
│   └── payment_service.py       # TODO: Реализовать 3 метода
└── tests/
    ├── test_concurrent_payment_unsafe.py   # TODO: Реализовать тест
    └── test_concurrent_payment_safe.py     # TODO: Реализовать тест
```

## Дополнительно

После успешного прохождения тестов:

1. Проверьте базу данных напрямую:
```sql
-- Подключитесь к PostgreSQL
docker exec -it lab_02-db-1 psql -U postgres -d marketplace

-- Посмотрите историю оплат
SELECT * FROM order_status_history WHERE status = 'paid' ORDER BY changed_at;
```

2. Заполните отчёт REPORT.md со своими выводами

3. Обоснуйте выбор ISOLATION LEVEL для продакшена
