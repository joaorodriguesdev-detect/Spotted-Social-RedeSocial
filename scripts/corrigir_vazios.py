import sqlite3

# Caminho que confirmamos antes
DB_PATH = '/home/SpottedSocial/spottedsocial/instance/spotted.db'

def fix_nulls():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Corrigindo usuários com nome vazio...")
    
    # Este comando copia o 'username' para o 'name' caso o 'name' esteja vazio ou nulo
    cursor.execute('''
        UPDATE user 
        SET name = username 
        WHERE name IS NULL OR name = ''
    ''')
    
    # Este comando coloca uma universidade padrão caso esteja vazia
    cursor.execute('''
        UPDATE user 
        SET university = 'Não informada' 
        WHERE university IS NULL OR university = ''
    ''')
    
    conn.commit()
    print(f"Total de linhas alteradas: {conn.total_changes}")
    conn.close()
    print("Correção finalizada! Pode checar o site.")

if __name__ == "__main__":
    fix_nulls()