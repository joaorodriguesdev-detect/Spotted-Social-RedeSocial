import sqlite3
import os

# Caminho exato do seu banco de dados
DB_PATH = '/home/SpottedSocial/spottedsocial/instance/spotted.db'

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
            try:
                cursor.execute(cmd)
                conn.commit()
                print(f"SUCESSO: {cmd}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"PULADO: Coluna já existe.")
                else:
                    print(f"AVISO: {e}")

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

        conn.close()
        print("\n--- TUDO PRONTO! MIGRACAO FINALIZADA ---")

    except Exception as e:
        print(f"ERRO: {e}")

if __name__ == "__main__":
    migrate()