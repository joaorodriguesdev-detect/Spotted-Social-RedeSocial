# 🧪 INSTRUÇÕES DE TESTE - Sistema de Comentários

## Pré-requisitos
- ✅ Python 3.8+
- ✅ Flask rodando com `python app.py`
- ✅ Usuário autenticado
- ✅ Browser com DevTools (F12)

## Teste 1: Comentário Normal ✅

### Passos:
1. Abra `/feed` no navegador
2. Escreva um comentário em qualquer post
3. Clique em "Enviar"

### Resultado Esperado:
- ✅ Comentário aparece **imediatamente** abaixo do post
- ✅ O texto que digitou desaparece do input
- ✅ Contador de comentários aumenta em 1

### Console esperado:
```
(nenhum erro)
```

---

## Teste 2: Comentário Vazio ❌

### Passos:
1. Clique no input de comentário
2. Clique em "Enviar" **sem digitar nada**

### Resultado Esperado:
- ✅ Mensagem de erro aparece: "Digite um comentário..."
- ✅ Input recebe foco (cursor pisca)
- ✅ Comentário **NÃO é enviado**

### Console esperado:
```
(nenhum erro, apenas lógica local)
```

---

## Teste 3: Erro HTTP (Simular) ⚠️

### Passos:
1. Abra DevTools (F12)
2. Vá em Network → Throttling → "Offline"
3. Escreva um comentário
4. Clique em "Enviar"

### Resultado Esperado:
- ✅ Mensagem de erro aparece: "Erro de conexão. Tente novamente."
- ✅ Botão permanece habilitado
- ✅ Input mantém o texto

### Console esperado:
```
Erro ao enviar comentário: TypeError: Failed to fetch
```

### Restaurar conexão:
1. DevTools → Network → Throttling → "No throttling"

---

## Teste 4: Botão Desabilitado durante Envio 🔒

### Passos:
1. Abra DevTools (F12)
2. Vá em Network → Throttling → "Slow 3G"
3. Escreva um comentário
4. **Rapidamente clique 3 vezes** em "Enviar"

### Resultado Esperado:
- ✅ Botão fica cinzento/desabilitado
- ✅ Apenas **1 comentário é criado** (não 3)
- ✅ Botão volta ao normal após sucesso

### Console esperado:
```
(nenhum erro de duplicação)
```

---

## Teste 5: Múltiplos Posts 📝

### Passos:
1. Vá para `/feed`
2. Comente em **diferentes posts** sequencialmente
3. Exemplo: Comentário em post 1, depois post 2, depois post 3

### Resultado Esperado:
- ✅ Cada comentário aparece no post correto
- ✅ Contadores de cada post aumentam independentemente
- ✅ Nenhuma interferência entre posts

---

## Teste 6: Edição de Comentário 📝

### Passos:
1. Adicione um comentário
2. Localize o comentário que você acabou de criar
3. Clique nas 3 reticências (menu)
4. Selecione "Editar"
5. Mude o texto
6. Clique "Salvar"

### Resultado Esperado:
- ✅ Comentário é atualizado
- ✅ Marca "(editado)" aparece
- ✅ Menu fecha automaticamente

---

## Teste 7: Deleção de Comentário 🗑️

### Passos:
1. Adicione um comentário
2. Clique nas 3 reticências do comentário
3. Selecione "Deletar"
4. Confirme no diálogo

### Resultado Esperado:
- ✅ Comentário desaparece da página
- ✅ Contador diminui em 1
- ✅ Mensagem de sucesso aparece

---

## Teste 8: Admin pode deletar qualquer comentário 👨‍💼

### Pré-requisitos:
- ✅ Estar autenticado como admin
- ✅ Haver comentários de outros usuários visíveis

### Passos:
1. Localize um comentário de **outro usuário**
2. Verifique se as 3 reticências aparecem
3. Clique nas 3 reticências
4. Selecione "Deletar"

### Resultado Esperado:
- ✅ Menu de opções aparece (mesmo comentário de outro)
- ✅ Botão "Deletar" está disponível
- ✅ Comentário é deletado após confirmação

---

## Verificações de Console (F12)

### Após cada teste, abra Console (F12) e procure por:

**✅ Sucesso:**
```javascript
(sem erros)
```

**❌ Erros a observar:**
```javascript
// Não deve ter isso:
Comment submission failed with status: ...
Comments container not found for ...
Erro ao enviar comentário: ...
```

---

## Teste de Compatibilidade: Formulário Tradicional

### Passos (sem JavaScript):
1. Desabilite JavaScript no navegador:
   - Chrome: DevTools → Cmd+Shift+P → "Disable JavaScript"
2. Recarregue a página
3. Tente comentar

### Resultado Esperado:
- ✅ Comentário é enviado (com reload da página)
- ✅ Página redireciona para `#post-{id}`
- ✅ Funciona normalmente (sem AJAX)

---

## Checklist Final

- [ ] Comentário normal funciona
- [ ] Comentário vazio é rejeitado
- [ ] Erro de conexão é tratado
- [ ] Botão previne duplicatas
- [ ] Múltiplos posts funcionam independentemente
- [ ] Edição de comentário funciona
- [ ] Admin pode deletar qualquer comentário
- [ ] Usuário pode deletar próprio comentário
- [ ] Compatibilidade com formulário tradicional
- [ ] Console limpo de erros

---

## Depuração Avançada

### Se algo não funcionar, cheque:

1. **DevTools → Network:**
   - Requisição POST em `/comentar/{post_id}` foi feita?
   - Response status é 201 (sucesso) ou 400/500 (erro)?
   - Headers contém `X-Requested-With: XMLHttpRequest`?

2. **DevTools → Console:**
   - Há erros JavaScript?
   - Há logs de comentário enviado?

3. **DevTools → Application:**
   - Session está ativa?
   - Cookie de autenticação presente?

4. **Backend logs:**
   - Há erros na terminal do Flask?
   - Banco de dados respondendo?

---

## Próximos Passos

Se todos os testes passarem ✅, o sistema está funcionando corretamente!

Considere também testar:
- [ ] Upload de imagem com comentário
- [ ] Menções (@username) em comentários
- [ ] Caracteres especiais e emojis
- [ ] Muito texto (limite de 500 caracteres)

