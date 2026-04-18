# Solução para o Erro 413 - Request Entity Too Large

## O Problema

O erro "413 Request Entity Too Large" ocorre quando:
1. O tamanho do arquivo é maior que o limite configurado no servidor
2. O nginx tem um limite padrão de `client_max_body_size` muito pequeno (geralmente 1MB)
3. A aplicação Flask tem um limite diferente do nginx

## Soluções Implementadas

### 1. Limite do Flask (app.py)
✅ Configurado para 30MB:
```python
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024
```

### 2. Limite do Nginx (nginx.conf)
Se você está rodando em produção com nginx, aplique esta configuração:

#### Opção A: Editar arquivo de site individual
```bash
sudo nano /etc/nginx/sites-available/spotted-social
```

Adicione ou atualize a linha:
```nginx
client_max_body_size 30M;
```

#### Opção B: Usar arquivo de configuração fornecido
```bash
# Copie o arquivo nginx.conf para a configuração do site
sudo cp nginx.conf /etc/nginx/sites-available/spotted-social
sudo ln -s /etc/nginx/sites-available/spotted-social /etc/nginx/sites-enabled/
```

**Lembre de editar os caminhos no arquivo!**

#### Opção C: Editar configuração global do nginx
```bash
sudo nano /etc/nginx/nginx.conf
```

Na seção `http { }`, adicione:
```nginx
client_max_body_size 30M;
```

### 3. Após configurar o nginx
```bash
# Teste a configuração
sudo nginx -t

# Reinicie o nginx
sudo systemctl restart nginx
```

## Tamanhos de Upload Suportados

| Tipo | Tamanho Máximo | Compressão |
|------|---|---|
| Imagens | 30MB | ✅ Convertidas para WebP |
| Foto de Perfil | 30MB | ✅ Convertidas para WebP |
| Evento com Imagem | 30MB | ✅ Convertidas para WebP |

## Como a Compressão Funciona

1. **Recepção**: Arquivo de até 30MB é recebido
2. **Processamento**:
   - Convertido para WebP (mais eficiente)
   - Redimensionado para máximo 1280x1280px
   - Qualidade comprimida para 75%
3. **Armazenamento**: Arquivo otimizado é salvo em `static/uploads/`

Isso resulta em arquivos 60-80% menores!

## Testando Localmente

Se tiver erro 413 localmente:
1. Verifique se nginx está rodando
2. Aplique a configuração acima
3. Reinicie nginx
4. Ou, para desenvolvimento, rode diretamente com Flask (sem nginx):
   ```bash
   python app.py
   ```

## Variáveis de Ambiente (Opcional)

Você pode controlar o limite via ambiente:
```bash
# No app.py, pode-se adicionar no futuro:
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_UPLOAD_SIZE', 30)) * 1024 * 1024
```

Então usar:
```bash
export MAX_UPLOAD_SIZE=50  # 50MB
python app.py
```

## Suporte

Se ainda receber o erro:
1. Verifique os logs do nginx: `sudo tail -f /var/log/nginx/error.log`
2. Verifique os logs do Flask: `tail -f instance/error.log`
3. Confirme se o nginx foi reiniciado corretamente

