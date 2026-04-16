# Лабораторная работа №2
## Управление конкурентными транзакциями в маркетплейсе

## Цель работы

Изучить механизмы управления конкурентным доступом в PostgreSQL, продемонстрировать проблемы race condition при одновременных оплатах и решить их с помощью правильных уровней изоляции транзакций и блокировок **в коде приложения**.

Работа выполняется в **Python/FastAPI/PostgreSQL** на основе проекта из лабораторной работы №1.

## Постановка задачи

В реальном маркетплейсе часто возникают ситуации, когда **две сессии пытаются одновременно оплатить один и тот же заказ**. Например:
- Пользователь нажал кнопку "Оплатить" дважды
- Два микросервиса обрабатывают один платеж параллельно
- Сбой в сети привел к повторной отправке запроса

**Ваша задача:** реализовать в коде приложения (Python/FastAPI):
1. **Сценарий с проблемой** — метод оплаты, который ломается при конкурентных запросах (READ COMMITTED)
2. **Исправленный сценарий** — метод оплаты с правильной изоляцией (REPEATABLE READ + FOR UPDATE)
3. **Тесты** — автоматические тесты, демонстрирующие проблему и её решение

## Функциональные требования

### 1. PaymentService с двумя методами оплаты

Вы должны реализовать класс `PaymentService` с двумя методами:

#### `pay_order_unsafe(order_id)` - Небезопасная реализация
```python
async def pay_order_unsafe(self, order_id: UUID) -> dict:
    """
    Использует READ COMMITTED (по умолчанию) без блокировок.
    ЛОМАЕТСЯ при конкурентных запросах - может привести к двойной оплате!
    
    TODO: Реализовать:
    1. SELECT status FROM orders WHERE id = :order_id
    2. Проверить, что status = 'created'
    3. UPDATE orders SET status = 'paid' WHERE id = :order_id
    4. INSERT в order_status_history
    5. COMMIT
    
    ВАЖНО: НЕ используйте FOR UPDATE!
    ВАЖНО: НЕ меняйте уровень изоляции!
    """
```

#### `pay_order_safe(order_id)` - Безопасная реализация
```python
async def pay_order_safe(self, order_id: UUID) -> dict:
    """
    Использует REPEATABLE READ + FOR UPDATE.
    Корректно работает при конкурентных запросах.
    
    TODO: Реализовать:
    1. SET TRANSACTION ISOLATION LEVEL REPEATABLE READ
    2. SELECT status FROM orders WHERE id = :order_id FOR UPDATE
    3. Проверить, что status = 'created'
    4. UPDATE orders SET status = 'paid' WHERE id = :order_id
    5. INSERT в order_status_history
    6. COMMIT
    
    ВАЖНО: Обязательно используйте FOR UPDATE!
    ВАЖНО: Обязательно установите REPEATABLE READ!
    """
```

### 2. Автоматические тесты

#### `test_concurrent_payment_unsafe.py`
Тест, который **ПРОХОДИТ**, подтверждая наличие race condition:
- Создает заказ со статусом `created`
- Запускает два параллельных вызова `pay_order_unsafe()` с помощью `asyncio.gather()`
- **Проверяет, что произошла двойная оплата** (две записи в order_status_history)
- Выводит: `⚠️ RACE CONDITION DETECTED!`

#### `test_concurrent_payment_safe.py`
Тест, который **ПРОХОДИТ**, подтверждая отсутствие race condition:
- Создает заказ со статусом `created`
- Запускает два параллельных вызова `pay_order_safe()` с помощью `asyncio.gather()`
- **Проверяет, что заказ оплачен только один раз** (одна запись в order_status_history)
- Одна попытка успешна, вторая выбрасывает исключение
- Выводит: `✅ RACE CONDITION PREVENTED!`

## Что нужно реализовать

### 1. PaymentService (`backend/app/application/payment_service.py`)

Файл уже создан с TODO. Реализуйте три метода:
- `pay_order_unsafe()` - небезопасная версия
- `pay_order_safe()` - безопасная версия
- `get_payment_history()` - для проверки истории оплат

### 2. Тесты

Реализуйте два файла тестов:
- `backend/app/tests/test_concurrent_payment_unsafe.py`
- `backend/app/tests/test_concurrent_payment_safe.py`

Каждый тест должен:
1. Создавать фикстуры для БД-сессии и тестового заказа
2. Запускать параллельные попытки оплаты
3. Проверять количество записей в истории
4. Выводить информацию о результатах

### 3. Отчёт `REPORT.md`

Заполните отчёт со следующими разделами:

#### Раздел 1: Описание проблемы
- Что такое race condition?
- Почему `READ COMMITTED` не защищает от двойной оплаты?
- Примеры из реальной жизни

#### Раздел 2: Уровни изоляции в PostgreSQL
Опишите: `READ UNCOMMITTED`, `READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE`

#### Раздел 3: Решение проблемы
- Почему `REPEATABLE READ` + `FOR UPDATE` решает проблему?
- Что произойдет без `FOR UPDATE`?
- Разница между `FOR UPDATE` и `FOR SHARE`

#### Раздел 4: Рекомендации для продакшена
**Главный вопрос:** Какой ISOLATION LEVEL использовать для продакшена маркетплейса и почему?

## Запуск проекта

```bash
# Запуск через Docker
cd lab_02
docker-compose up --build

# Проверка
curl http://localhost:8080/health
```

## Тестирование

### Автоматические тесты (Python)

```bash
cd backend
export PYTHONPATH=$(pwd)

# Тест с проблемой (должен ПРОЙТИ, показывая двойную оплату)
pytest app/tests/test_concurrent_payment_unsafe.py -v -s

# Тест с решением (должен ПРОЙТИ, показывая однократную оплату)
pytest app/tests/test_concurrent_payment_safe.py -v -s
```

### Визуальное тестирование (Frontend)

**Добавлена специальная страница для тестирования через браузер!**

1. Запустите проект:
```bash
docker-compose up --build
```

2. Откройте в браузере:
```
http://localhost:5173/test-concurrent
```

3. На странице:
   - Нажмите "Создать тестовый заказ"
   - Выберите режим: **Unsafe** (с проблемой) или **Safe** (без проблемы)
   - Нажмите "Запустить 2 параллельные оплаты"
   - Увидите результаты в реальном времени:
     - Количество успешных/неудачных попыток
     - Количество записей в истории БД
     - **⚠️ RACE CONDITION DETECTED!** или **✅ No race condition**

**Это отличный способ визуально показать проблему и её решение!**

### Ожидаемый вывод

**test_concurrent_payment_unsafe.py:**
```
⚠️ RACE CONDITION DETECTED!
Order XXX was paid TWICE:
  - 2024-XX-XX 10:00:01: status = paid
  - 2024-XX-XX 10:00:01: status = paid
✅ test PASSED (демонстрирует проблему)
```

**test_concurrent_payment_safe.py:**
```
✅ RACE CONDITION PREVENTED!
Order XXX was paid only ONCE:
  - 2024-XX-XX 10:00:01: status = paid
Second attempt was rejected: OrderAlreadyPaidError(...)
✅ test PASSED (проблема решена)
```

## Структура проекта

```
lab_02/
├── backend/
│   ├── app/
│   │   ├── application/
│   │   │   └── payment_service.py       # TODO: Реализовать
│   │   └── tests/
│   │       ├── test_concurrent_payment_unsafe.py   # TODO: Реализовать
│   │       └── test_concurrent_payment_safe.py     # TODO: Реализовать
│   └── migrations/
│       └── 001_init.sql                 # ✅ Из lab_01
├── REPORT.md                            # TODO: Заполнить
└── README.md                            # Этот файл
```

## Подсказки

### Использование asyncio для конкурентных запросов

```python
import asyncio

# Запуск двух параллельных операций
results = await asyncio.gather(
    pay_order_unsafe(order_id),  # Попытка 1
    pay_order_unsafe(order_id),  # Попытка 2
    return_exceptions=True
)

# Проверка результатов
for i, result in enumerate(results):
    if isinstance(result, Exception):
        print(f"Попытка {i+1} завершилась ошибкой: {result}")
    else:
        print(f"Попытка {i+1} успешна: {result}")
```

### Установка уровня изоляции в SQLAlchemy

```python
from sqlalchemy import text

# В начале транзакции
await session.execute(
    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
)
```

### Использование FOR UPDATE

```python
# Блокировка строки для обновления
result = await session.execute(
    text("SELECT status FROM orders WHERE id = :order_id FOR UPDATE"),
    {"order_id": order_id}
)
status = result.scalar()
```

### Создание независимых сессий для тестов

```python
# Каждая "попытка оплаты" должна иметь свою сессию
async def payment_attempt_1():
    async with AsyncSession(engine) as session1:
        service1 = PaymentService(session1)
        return await service1.pay_order_unsafe(order_id)

async def payment_attempt_2():
    async with AsyncSession(engine) as session2:
        service2 = PaymentService(session2)
        return await service2.pay_order_unsafe(order_id)

# Запустить параллельно
results = await asyncio.gather(
    payment_attempt_1(),
    payment_attempt_2(),
    return_exceptions=True
)
```

## Критерии оценки

- **Корректность реализации PaymentService** — 40%
  - pay_order_unsafe() действительно ломается
  - pay_order_safe() действительно работает
- **Качество тестов** — 30%
  - Тесты корректно демонстрируют проблему и решение
  - Правильное использование asyncio.gather()
- **Отчёт и обоснования** — 20%
  - Понимание уровней изоляции
  - Обоснование выбора для продакшена
- **Понимание механизмов** — 10%
  - Объяснение работы FOR UPDATE
  - Знание аномалий транзакций

## Важно!

**Главный принцип:** Конкурентный доступ должен контролироваться на уровне СУБД (через уровни изоляции и блокировки), а не только в коде приложения.

## FAQ

**Q: Почему нужны два разных метода?**  
A: Чтобы явно показать разницу между небезопасной и безопасной реализацией. В реальном проекте используется только безопасная версия.

**Q: Почему тесты должны ПРОХОДИТЬ, если есть проблема?**  
A: Тест `test_concurrent_payment_unsafe` проверяет, что проблема ЕСТЬ (assert len(history) == 2). Это демонстрационный тест.

**Q: Как убедиться, что FOR UPDATE действительно работает?**  
A: Добавьте `asyncio.sleep(1)` в первую транзакцию после FOR UPDATE и проверьте временные метки - вторая транзакция должна завершиться позже.

**Q: Нужно ли реализовывать API endpoints?**  
A: Нет, достаточно реализовать сервис и тесты. API endpoints из lab_01 можно оставить как есть.
