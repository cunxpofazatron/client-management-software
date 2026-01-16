import psycopg2
from psycopg2 import sql
from typing import List, Optional, Tuple

def create_db(conn):
    """Создает структуру базы данных (таблицы)"""
    with conn.cursor() as cur:
        # Удаляем существующие таблицы (для чистоты демонстрации)
        cur.execute("DROP TABLE IF EXISTS phone CASCADE;")
        cur.execute("DROP TABLE IF EXISTS client CASCADE;")

        # Создаем таблицу клиентов
        cur.execute("""
            CREATE TABLE client (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL
            );
        """)

        # Создаем таблицу телефонов
        cur.execute("""
            CREATE TABLE phone (
                id SERIAL PRIMARY KEY,
                client_id INTEGER NOT NULL REFERENCES client(id) ON DELETE CASCADE,
                phone VARCHAR(20) NOT NULL,
                UNIQUE(client_id, phone)
            );
        """)
    conn.commit()
    print("База данных успешно создана")

def add_client(conn, first_name: str, last_name: str, email: str, phones: Optional[List[str]] = None) -> int:
    """Добавляет нового клиента"""
    with conn.cursor() as cur:
        try:
            # Вставляем данные клиента
            cur.execute("""
                INSERT INTO client (first_name, last_name, email)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (first_name, last_name, email))
            client_id = cur.fetchone()[0]

            # Если есть телефоны, добавляем их
            if phones:
                for phone in phones:
                    if phone:  # Проверяем, что номер не пустой
                        cur.execute("""
                            INSERT INTO phone (client_id, phone)
                            VALUES (%s, %s);
                        """, (client_id, phone))

            conn.commit()
            print(f"Клиент {first_name} {last_name} добавлен с ID: {client_id}")
            return client_id

        except psycopg2.IntegrityError as e:
            conn.rollback()
            if "email" in str(e):
                print(f"Ошибка: Клиент с email {email} уже существует")
            else:
                print(f"Ошибка при добавлении клиента: {e}")
            raise

def add_phone(conn, client_id: int, phone: str):
    """Добавляет телефон для существующего клиента"""
    with conn.cursor() as cur:
        try:
            # Проверяем существование клиента
            cur.execute("SELECT id FROM client WHERE id = %s;", (client_id,))
            if not cur.fetchone():
                print(f"Ошибка: Клиент с ID {client_id} не найден")
                return

            # Добавляем телефон
            cur.execute("""
                INSERT INTO phone (client_id, phone)
                VALUES (%s, %s);
            """, (client_id, phone))

            conn.commit()
            print(f"Телефон {phone} добавлен для клиента с ID: {client_id}")

        except psycopg2.IntegrityError:
            conn.rollback()
            print(f"Ошибка: Телефон {phone} уже существует у клиента с ID {client_id}")

def change_client(conn, client_id: int, first_name: Optional[str] = None,
                  last_name: Optional[str] = None, email: Optional[str] = None,
                  phones: Optional[List[str]] = None):
    """Изменяет данные о клиенте"""
    with conn.cursor() as cur:
        try:
            # Проверяем существование клиента
            cur.execute("SELECT id FROM client WHERE id = %s;", (client_id,))
            if not cur.fetchone():
                print(f"Ошибка: Клиент с ID {client_id} не найден")
                return

            # Обновляем данные клиента
            updates = []
            params = []

            if first_name is not None:
                updates.append("first_name = %s")
                params.append(first_name)
            if last_name is not None:
                updates.append("last_name = %s")
                params.append(last_name)
            if email is not None:
                updates.append("email = %s")
                params.append(email)

            if updates:
                params.append(client_id)
                cur.execute(f"""
                    UPDATE client
                    SET {', '.join(updates)}
                    WHERE id = %s;
                """, tuple(params))

            # Обновляем телефоны, если они предоставлены
            if phones is not None:
                # Удаляем старые телефоны
                cur.execute("DELETE FROM phone WHERE client_id = %s;", (client_id,))

                # Добавляем новые телефоны
                for phone in phones:
                    if phone:  # Проверяем, что номер не пустой
                        cur.execute("""
                            INSERT INTO phone (client_id, phone)
                            VALUES (%s, %s);
                        """, (client_id, phone))

            conn.commit()
            print(f"Данные клиента с ID {client_id} успешно обновлены")

        except psycopg2.IntegrityError as e:
            conn.rollback()
            if "email" in str(e):
                print(f"Ошибка: Email {email} уже используется другим клиентом")
            else:
                print(f"Ошибка при обновлении клиента: {e}")

def delete_phone(conn, client_id: int, phone: str):
    """Удаляет телефон для существующего клиента"""
    with conn.cursor() as cur:
        # Проверяем существование телефона
        cur.execute("""
            DELETE FROM phone
            WHERE client_id = %s AND phone = %s
            RETURNING id;
        """, (client_id, phone))

        if cur.rowcount > 0:
            conn.commit()
            print(f"Телефон {phone} удален у клиента с ID: {client_id}")
        else:
            print(f"Телефон {phone} не найден у клиента с ID: {client_id}")

def delete_client(conn, client_id: int):
    """Удаляет существующего клиента"""
    with conn.cursor() as cur:
        # Проверяем существование клиента
        cur.execute("SELECT id FROM client WHERE id = %s;", (client_id,))
        if not cur.fetchone():
            print(f"Ошибка: Клиент с ID {client_id} не найден")
            return

        # Удаляем клиента (телефоны удалятся автоматически благодаря CASCADE)
        cur.execute("DELETE FROM client WHERE id = %s;", (client_id,))

        conn.commit()
        print(f"Клиент с ID {client_id} успешно удален")

def find_client(conn, first_name: Optional[str] = None, last_name: Optional[str] = None,
                email: Optional[str] = None, phone: Optional[str] = None) -> List[Tuple]:
    """Находит клиента по его данным"""
    with conn.cursor() as cur:
        query = """
            SELECT DISTINCT c.id, c.first_name, c.last_name, c.email,
                   STRING_AGG(p.phone, ', ') as phones
            FROM client c
            LEFT JOIN phone p ON c.id = p.client_id
            WHERE 1=1
        """

        params = []
        conditions = []

        if first_name:
            conditions.append("c.first_name ILIKE %s")
            params.append(f"%{first_name}%")
        if last_name:
            conditions.append("c.last_name ILIKE %s")
            params.append(f"%{last_name}%")
        if email:
            conditions.append("c.email ILIKE %s")
            params.append(f"%{email}%")
        if phone:
            conditions.append("p.phone = %s")
            params.append(phone)

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += " GROUP BY c.id, c.first_name, c.last_name, c.email;"

        cur.execute(query, tuple(params))
        results = cur.fetchall()

        return results

def print_clients(clients: List[Tuple]):
    """Печатает информацию о клиентах в удобном формате"""
    if not clients:
        print("Клиенты не найдены")
        return

    print("\n" + "="*60)
    print(f"{'ID':<5} {'Имя':<15} {'Фамилия':<15} {'Email':<20} {'Телефоны':<30}")
    print("-"*60)

    for client in clients:
        client_id, first_name, last_name, email, phones = client
        print(f"{client_id:<5} {first_name:<15} {last_name:<15} {email:<20} {phones or 'Нет телефона':<30}")

    print("="*60 + "\n")

# =======================
# Демонстрация работы
# =======================
if __name__ == "__main__":
    try:
        # Подключение к базе данных
        # ВНИМАНИЕ: Замените параметры подключения на свои!
        conn = psycopg2.connect(
            dbname="postgres",
            user="",
            password="",
            host="localhost",
            port="5432"
        )

        print("Подключение к базе данных успешно установлено")

        # Создаем базу данных, если она не существует
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'clients_db';")
            if not cur.fetchone():
                cur.execute("CREATE DATABASE clients_db;")
                print("База данных 'clients_db' создана")
        conn.autocommit = False

        # Переподключаемся к созданной базе данных
        conn.close()
        conn = psycopg2.connect(
            dbname="clients_db",
            user="",
            password="",
            host="localhost",
            port="5432"
        )

        print("Подключение к базе данных 'clients_db' установлено")

        # 1. Создаем структуру БД
        print("\n1. Создание структуры базы данных...")
        create_db(conn)

        # 2. Добавляем клиентов
        print("\n2. Добавление клиентов...")
        client1_id = add_client(
            conn,
            "Иван",
            "Иванов",
            "ivan@mail.com",
            phones=["+79991234567", "+79997654321"]
        )

        client2_id = add_client(
            conn,
            "Мария",
            "Петрова",
            "maria@mail.com",
            phones=["+79998887766"]
        )

        client3_id = add_client(
            conn,
            "Алексей",
            "Сидоров",
            "alex@mail.com"
        )  # Без телефона

        # 3. Добавляем телефон для существующего клиента
        print("\n3. Добавление телефона для клиента...")
        add_phone(conn, client3_id, "+79995554433")

        # 4. Изменяем данные клиента
        print("\n4. Изменение данных клиента...")
        change_client(
            conn,
            client_id=client1_id,
            first_name="Иоанн",  # Меняем имя
            email="ivanov@mail.ru"  # Меняем email
        )

        # 5. Поиск клиентов
        print("\n5. Поиск клиентов...")
        print("Поиск по имени 'Иоанн':")
        clients = find_client(conn, first_name="Иоанн")
        print_clients(clients)

        print("Поиск по телефону '+79998887766':")
        clients = find_client(conn, phone="+79998887766")
        print_clients(clients)

        print("Поиск по email 'maria@mail.com':")
        clients = find_client(conn, email="maria@mail.com")
        print_clients(clients)

        # 6. Удаление телефона
        print("\n6. Удаление телефона...")
        delete_phone(conn, client1_id, "+79997654321")

        print("Клиент после удаления телефона:")
        clients = find_client(conn, first_name="Иоанн")
        print_clients(clients)

        # 7. Удаление клиента
        print("\n7. Удаление клиента...")
        delete_client(conn, client2_id)

        print("Все клиенты после удаления:")
        clients = find_client(conn)  # Без параметров - все клиенты
        print_clients(clients)

        print("Все операции успешно выполнены!")

    except psycopg2.OperationalError as e:
        print(f"Ошибка подключения к базе данных: {e}")
        print("Пожалуйста, убедитесь что:")
        print("1. PostgreSQL установлен и запущен")
        print("2. База данных существует")
        print("3. Параметры подключения верны")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("\nСоединение с базой данных закрыто")
