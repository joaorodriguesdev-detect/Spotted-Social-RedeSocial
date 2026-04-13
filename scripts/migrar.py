import sqlite3
import os

DB_PATH = '/home/SpottedSocial/spottedsocial/instance/spotted.db'


def run_ddl(cursor, command):
    try:
        cursor.execute(command)
        print(f"SUCESSO: {command.splitlines()[0]}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("PULADO: Coluna ja existe.")
        else:
            print(f"AVISO: {e}")


def create_direct_tables(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug VARCHAR(80) UNIQUE,
            title VARCHAR(80),
            is_group BOOLEAN NOT NULL DEFAULT 0,
            group_photo VARCHAR(200),
            created_at DATETIME
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            is_admin BOOLEAN NOT NULL DEFAULT 0,
            joined_at DATETIME,
            UNIQUE(conversation_id, user_id),
            FOREIGN KEY(conversation_id) REFERENCES conversation(id),
            FOREIGN KEY(user_id) REFERENCES user(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS direct_chat_message (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            content VARCHAR(500) NOT NULL,
            media_url VARCHAR(200),
            created_at DATETIME,
            FOREIGN KEY(conversation_id) REFERENCES conversation(id),
            FOREIGN KEY(sender_id) REFERENCES user(id)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_member_user ON conversation_member(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_direct_chat_message_conv ON direct_chat_message(conversation_id, id DESC)')
    try:
        cursor.execute('ALTER TABLE conversation_member ADD COLUMN last_read_message_id INTEGER')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE conversation ADD COLUMN pinned_message_id INTEGER')
    except sqlite3.OperationalError:
        pass

def migrate():
    print(f"--- Iniciando Migração no Banco: {DB_PATH} ---")
    
    if not os.path.exists(DB_PATH):
        print("ERRO: Banco de dados não encontrado!")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Adicionar novas colunas necessárias
        commands = [
            "ALTER TABLE user ADD COLUMN name VARCHAR(80)",
            "ALTER TABLE user ADD COLUMN university VARCHAR(50)",
            "ALTER TABLE post ADD COLUMN is_anonymous BOOLEAN DEFAULT 0",
            "ALTER TABLE notification ADD COLUMN post_id INTEGER"
        ]

        for cmd in commands:
            run_ddl(cursor, cmd)
        conn.commit()

        # 2. Corrigir usuários antigos (preencher Nome e Universidade vazios)
        print("Limpando 'bugs' de usuários antigos...")
        cursor.execute("UPDATE user SET name = username WHERE name IS NULL OR name = ''")
        cursor.execute("UPDATE user SET university = 'Não informada' WHERE university IS NULL OR university = ''")
        conn.commit()
        print("SUCESSO: Usuários antigos atualizados.")

        # 3. Criar a tabela de eventos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                event_date VARCHAR(50) NOT NULL,
                location VARCHAR(100) NOT NULL,
                media_url VARCHAR(200),
                created_at DATETIME,
                user_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES user(id)
            )
        ''')
        conn.commit()
        print("SUCESSO: Tabela de eventos pronta.")

        # 4. Criar tabelas do novo Direct/Grupo
        create_direct_tables(cursor)
        conn.commit()
        print("SUCESSO: Tabelas do Direct prontas.")

        conn.close()
        print("\n--- TUDO PRONTO! MIGRACAO FINALIZADA ---")

    except Exception as e:
        print(f"ERRO: {e}")

if __name__ == "__main__":
    migrate()