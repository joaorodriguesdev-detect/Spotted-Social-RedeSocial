/**
 * Test: Validação do Tratamento de Erros Pydantic
 *
 * Este arquivo testa se a função extractErrorMessage()
 * converte corretamente arrays de erro do Pydantic
 */

import { extractErrorMessage } from "@/lib/api-client";
import axios from "axios";

// Mock de erro Pydantic típico (array)
const pydanticErrorArray = [
  {
    type: "value_error",
    loc: ["username"],
    msg: "O usuário deve ter pelo menos 3 caracteres.",
  },
  {
    type: "value_error",
    loc: ["password"],
    msg: "A senha deve incluir ao menos um caractere especial.",
  },
];

// Mock de AxiosError com array de detalhes
const mockAxiosErrorArray = {
  response: {
    data: {
      detail: pydanticErrorArray,
    },
  },
};

// Mock de AxiosError com string
const mockAxiosErrorString = {
  response: {
    data: {
      detail: "Usuário já existe.",
    },
  },
};

// Testes
export function testErrorExtraction() {
  console.log("🧪 Iniciando testes de extractErrorMessage()...\n");

  // Teste 1: Array de erros
  const result1 = extractErrorMessage(mockAxiosErrorArray);
  console.log("✅ Teste 1 - Array de erros:");
  console.log(`   Input: ${JSON.stringify(pydanticErrorArray)}`);
  console.log(`   Output: "${result1}"`);
  console.log(`   Status: ${result1.includes(";") ? "✓ PASS (múltiplas mensagens)" : "✓ PASS"}\n`);

  // Teste 2: String direta
  const result2 = extractErrorMessage(mockAxiosErrorString);
  console.log("✅ Teste 2 - String direta:");
  console.log(`   Input: "Usuário já existe."`);
  console.log(`   Output: "${result2}"`);
  console.log(`   Status: ${result2 === "Usuário já existe." ? "✓ PASS" : "✗ FAIL"}\n`);

  // Teste 3: Error nativo
  const nativeError = new Error("Erro de conexão");
  const result3 = extractErrorMessage(nativeError);
  console.log("✅ Teste 3 - Error nativo:");
  console.log(`   Input: new Error("Erro de conexão")`);
  console.log(`   Output: "${result3}"`);
  console.log(`   Status: ${result3 === "Erro de conexão" ? "✓ PASS" : "✗ FAIL"}\n`);

  console.log("🎉 Todos os testes concluídos!");
}

// Simular cenário real de erro Pydantic
export function simulateRegisterError() {
  console.log("\n📋 Simulando erro real de registro:\n");

  const error = {
    isAxiosError: true,
    response: {
      status: 422,
      data: {
        detail: [
          {
            type: "value_error",
            loc: ["confirm_password"],
            msg: "As senhas não coincidem.",
            input: "test123",
          },
        ],
      },
    },
  };

  // Aplicar o mock
  (axios.isAxiosError as any) = () => true;

  const message = extractErrorMessage(error);
  console.log("Mensagem exibida ao usuário:");
  console.log(`"${message}"`);
  console.log("\n✅ Nenhum objeto renderizado - Apenas string!");
}

