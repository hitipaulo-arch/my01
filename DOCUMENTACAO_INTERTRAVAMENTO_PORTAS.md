# Documentação funcional — intertravamento de quatro portas

> **Status:** proposta preliminar de lógica. Não é um projeto elétrico validado nem uma função de segurança certificada. Os endereços abaixo são exemplos e devem ser ajustados ao modelo do PLC, à expansão de I/O e à fiação real.

## 1. Objetivo

Controlar quatro portas com eletroímã e junta pneumática inflável. As portas formam dois pares intertravados:

- **Par A:** porta 1 e porta 2 — somente uma pode ser liberada por vez.
- **Par B:** porta 3 e porta 4 — somente uma pode ser liberada por vez.

Em operação normal, o eletroímã é comandado quando a porta está confirmada como fechada e não está liberada. A válvula da junta é uma saída independente: desenergiza imediatamente ao solicitar a liberação e, após a porta fechar novamente, só energiza depois de um atraso de 2 segundos com o sensor de fechada ativo e o eletroímã comandado. Assim, a junta infla depois do travamento magnético.

## 2. Premissas a confirmar antes da implementação

1. Cada porta tem um botão de solicitação e um sensor de porta fechada.
2. O sensor fica ligado (`1`) quando a porta está fechada e corretamente posicionada.
3. A válvula é do tipo em que a bobina energizada enche a junta e desenergizada interrompe/esvazia a junta. Se a válvula tiver funcionamento diferente, a lógica deve ser adaptada.
4. A liberação é mantida até a porta abrir e depois fechar. Se o botão for pressionado, mas a porta não abrir, a lógica abaixo mantém a liberação. Pode-se acrescentar um temporizador de cancelamento, após análise do processo.
5. As saídas do PLC comandam interfaces adequadas (relés, drivers ou válvulas), não necessariamente alimentam as bobinas diretamente.

## 3. Exemplo de endereçamento

| Porta | Botão de solicitação | Sensor fechada | Eletroímã | Válvula da junta | Bit de liberação | Bit “abriu” |
|---|---|---|---|---|---|---|
| 1 | X0 | X10 | Y0 | Y10 | M100 | M110 |
| 2 | X1 | X11 | Y1 | Y11 | M101 | M111 |
| 3 | X2 | X12 | Y2 | Y12 | M102 | M112 |
| 4 | X3 | X13 | Y3 | Y13 | M103 | M113 |

Saída adicional de exemplo: `Y23` comanda a bobina do relé indicador geral de portas. Relé energizado seleciona vermelho; relé desenergizado seleciona verde.

`X`, `Y` e `M` são notações ilustrativas para PLC Mitsubishi FX. Em famílias FX, a numeração de I/O pode ser octal; verificar a configuração e o mapa de módulos no projeto GX Works2. O símbolo `/X10` abaixo significa contato lógico negado de X10 no ladder, não afirma que o sensor de campo seja eletricamente NF.

## 4. Sequência de operação

1. Com a porta fechada e sem solicitação de liberação, o eletroímã é comandado ligado. A válvula só liga após 2 segundos de confirmação contínua de porta fechada e eletroímã comandado.
2. Um pulso no botão é aceito somente se a própria porta e a porta parceira estiverem fechadas e a parceira não estiver liberada.
3. A lógica grava a liberação e desenergiza imediatamente o eletroímã e a válvula da porta solicitada.
4. Quando o sensor dessa porta deixa de indicar fechada, a lógica grava que a porta abriu.
5. Quando o sensor volta a indicar fechada, a liberação é removida. O eletroímã é comandado imediatamente; a válvula só energiza depois do atraso de 2 segundos, se a porta continuar fechada.
6. Enquanto uma porta estiver aberta, o sensor aberto impede que sua parceira seja liberada.
7. O indicador geral usa os quatro sensores de fechada: se qualquer um indicar porta aberta, Y23 energiza o relé e seleciona o LED vermelho. Somente quando todos os sensores confirmarem portas fechadas, Y23 desenergiza e o contato normalmente fechado do relé seleciona o LED verde.

## 5. Lógica ladder de referência

### 5.1 Solicitação de liberação

Use contato de borda positiva (`LDP`) para que manter o botão pressionado não gere novas solicitações. O rung da porta 1, por exemplo, é:

```text
LDP X0   X10   X11   /M101  ───── SET M100
```

Condições: pulso do botão 1, porta 1 fechada, porta 2 fechada e porta 2 fora do estado de liberação.

Repita para cada porta:

```text
LDP X1   X11   X10   /M100  ───── SET M101
LDP X2   X12   X13   /M103  ───── SET M102
LDP X3   X13   X12   /M102  ───── SET M103
```

No editor Ladder do GX Works2, monte cada condição com os contatos em série e a bobina `SET` no final. `LDP` representa o contato de pulso na borda positiva; confira a forma disponível para a CPU selecionada.

### 5.2 Detectar abertura e encerrar a liberação ao fechar

Para a porta 1:

```text
M100   /X10  ──────────────────── SET M110
M110    X10  ──────────────────── RST M100
M110    X10  ──────────────────── RST M110
```

A primeira linha memoriza que a porta abriu durante o ciclo. As duas linhas seguintes encerram o ciclo quando a porta retorna ao estado fechado. Repita o padrão:

```text
M101   /X11  ──────────────────── SET M111
M111    X11  ──────────────────── RST M101
M111    X11  ──────────────────── RST M111

M102   /X12  ──────────────────── SET M112
M112    X12  ──────────────────── RST M102
M112    X12  ──────────────────── RST M112

M103   /X13  ──────────────────── SET M113
M113    X13  ──────────────────── RST M103
M113    X13  ──────────────────── RST M113
```

### 5.3 Comando independente dos eletroímãs e atraso das válvulas

Os eletroímãs energizam assim que a respectiva porta está fechada e não está liberada. Cada válvula tem temporizador próprio: ela só energiza depois de 2 segundos contínuos nessas mesmas condições. Se a porta abrir ou receber solicitação de liberação antes do fim do tempo, o temporizador zera e a válvula permanece desligada.

Exemplo para a porta 1 (temporizador simbólico `T0`; selecionar base/valor conforme CPU FX):

```text
X10   /M100  ──────────────────── Y0       (eletroímã, imediato)
X10   /M100  ──────────────────── T0 2 s   (temporização não retentiva)
X10   /M100   T0  ─────────────── Y10      (válvula após 2 s)
```

Repetir com temporizador independente por porta:

```text
X11   /M101  ──────────────────── Y1
X11   /M101  ──────────────────── T1 2 s
X11   /M101   T1  ─────────────── Y11

X12   /M102  ──────────────────── Y2
X12   /M102  ──────────────────── T2 2 s
X12   /M102   T2  ─────────────── Y12

X13   /M103  ──────────────────── Y3
X13   /M103  ──────────────────── T3 2 s
X13   /M103   T3  ─────────────── Y13
```

As linhas `T0 2 s` etc. são indicação conceitual de temporizador TON de 2 segundos; no FX o valor constante depende da base de tempo do timer e da CPU (por exemplo, não assumir `K20` sem confirmar). Use temporizadores não retentivos para que a contagem reinicie se a porta abrir ou a liberação for solicitada. A válvula desenergiza imediatamente quando sua condição de saída deixa de ser verdadeira; o atraso é somente no acionamento/energização.

### 5.4 Indicador LED geral de portas abertas/fechadas

Use `Y23` para comandar a bobina de um relé auxiliar com contato reversível (SPDT), dimensionado para a tensão e a corrente do LED. A lógica assume que `X10` a `X13` ficam ligados quando as respectivas portas estão fechadas:

```text
/X10 ─┐
/X11 ─┤
/X12 ─┤────────────────────────── Y23 (bobina do relé indicador)
/X13 ─┘
```

Os quatro contatos `/X10` a `/X13` são ramos em paralelo (OU). Assim, qualquer porta aberta energiza Y23. Ligue o contato normalmente aberto do relé para selecionar o vermelho e o contato normalmente fechado para selecionar o verde: Y23 ligado = vermelho; Y23 desligado, com todas as portas fechadas = verde. Use alimentação e proteção adequadas para o LED/relé; não passe corrente da lâmpada por um contato sem verificar sua especificação.

Esse indicador usa os sensores físicos de fechada. Se uma porta estiver liberada pelo botão, mas ainda fisicamente fechada, o LED continuará verde até o sensor indicar que ela abriu. Se a intenção for mostrar vermelho já durante a liberação, acrescentar `/M100` a `/M103` como condições paralelas.

## 6. Verificações e testes de comissionamento

Realizar os testes primeiro em modo seguro, sem pessoas expostas ao risco e, quando possível, sem carga ou pressão no atuador. Registrar os resultados.

- [ ] Confirmar CPU, versão de GX Works2, mapa de I/O e endereços físicos.
- [ ] Confirmar, no monitor do PLC, que cada sensor indica `1` somente quando a porta está efetivamente fechada.
- [ ] Solicitar abertura da porta 1: as saídas Y0 e Y10 devem desligar; porta 2 não deve poder ser liberada.
- [ ] Repetir o teste em ordem inversa para o par 1–2.
- [ ] Repetir os dois testes para o par 3–4.
- [ ] Confirmar que, após abrir e fechar, o eletroímã energiza imediatamente e a válvula só energiza após 2 segundos contínuos com a porta fechada.
- [ ] Confirmar que a válvula desenergiza imediatamente ao solicitar liberação e que a contagem é cancelada se a porta abrir novamente.
- [ ] Abrir uma porta por vez e verificar que o relé Y23 energiza e seleciona vermelho; fechar todas e confirmar relé desenergizado e LED verde.
- [ ] Confirmar o comportamento se um botão ficar pressionado, se a porta não abrir e se a porta demorar a fechar.
- [ ] Validar partida/reinicialização do PLC, falta e retorno de energia, falha/desconexão de sensor, falha de saída e perda de ar comprimido.
- [ ] Testar o transdutor único da linha comum: verificar leitura analógica, indicações da lâmpada e sirene abaixo de 0,8 bar, entre 0,8 e 1,5 bar e acima de 1,5 bar.
- [ ] Validar os tempos, a pressão, a exaustão e o comportamento real da válvula e da junta pneumática; lembrar que o sensor comum não detecta necessariamente vazamento localizado em uma junta.

## 7. Monitoramento de pressão e alarme da linha de ar comum

A configuração desejada usa **um único transdutor analógico de pressão** na linha de ar comum. Um pressostato simples, com apenas saída liga/desliga, não consegue distinguir os níveis de 0,8 e 1,5 bar nem selecionar a cor conforme a pressão medida. Instale o transdutor no coletor principal, depois do filtro/regulador e antes das derivações para as quatro válvulas. O modelo escolhido deve ser compatível com a pressão, o tipo de saída e a entrada analógica da CPU/módulo; definir escala e unidades no GX Works2.

> **Limitação:** o transdutor comum detecta a pressão geral da alimentação, mas não identifica qual junta está com vazamento, desconectada ou sem inflar. Uma falha localizada depois da derivação pode ocorrer mesmo com pressão normal no coletor.

### Sinais sugeridos

| Sinal | Endereço de exemplo | Função |
|---|---|---|
| Medição analógica da pressão comum | `AI_PRESSAO` (simbólico) | Valor escalado em bar; endereço real depende do módulo analógico |
| Sirene | Y20 | Ligada quando a pressão estiver fora da faixa de 0,8 a 1,5 bar |
| Lâmpada vermelha | Y21 | Indica pressão baixa; piscando abaixo de 0,8 bar |
| Lâmpada verde | Y22 | Indica pressão alta/normal; piscando acima de 1,5 bar |

Y20–Y22 são apenas exemplos. Confirmar a configuração de I/O, o tipo de lâmpada (vermelho e verde separados ou torre bicolor) e a interface elétrica das cargas. O pisca deve ser gerado por um bit de clock apropriado à CPU ou por temporizador; o dispositivo especial exato depende do modelo FX.

### Comportamento solicitado

- **Pressão abaixo de 0,8 bar:** lâmpada vermelha piscando e sirene ligada.
- **De 0,8 bar até abaixo de 1,15 bar:** lâmpada vermelha acesa continuamente e sirene desligada.
- **A partir de 1,15 bar até 1,5 bar:** lâmpada verde acesa continuamente e sirene desligada.
- **Pressão acima de 1,5 bar:** lâmpada verde piscando e sirene ligada.

O ponto de 1,15 bar é o meio entre 0,8 e 1,5 bar, usado para escolher a cor fixa na faixa intermediária: abaixo dele fica vermelha; a partir dele fica verde. Os limites de alarme seguem a solicitação estrita “menor que 0,8” e “maior que 1,5”; portanto, exatamente 0,8 e 1,5 bar não acionam a sirene. Para evitar oscilação da indicação perto dos limites, pode-se implementar histerese (limites distintos para ligar e desligar cada alarme), mas os valores devem ser acordados e validados no equipamento.

### Lógica conceitual

```text
Se AI_PRESSAO < 0,8 bar:
    Y21 = pisca; Y22 = desligada; Y20 = ligada
Senão, se AI_PRESSAO > 1,5 bar:
    Y22 = pisca; Y21 = desligada; Y20 = ligada
Senão, se AI_PRESSAO < 1,15 bar:
    Y21 = ligada fixa; Y22 = desligada; Y20 = desligada
Senão:
    Y22 = ligada fixa; Y21 = desligada; Y20 = desligada
```

Este é um algoritmo funcional, não a sintaxe final de instrução para uma CPU específica. Confirmar com o fabricante o limite máximo permitido pela junta e pelos componentes pneumáticos. **Não usar o alarme do PLC como proteção única contra sobrepressão:** qualquer proteção necessária deve ser dimensionada para o risco, incluindo válvula mecânica de alívio quando aplicável. A reação do processo a baixa ou alta pressão deve ser definida por análise de risco; não liberar portas automaticamente sem validar que isso é seguro.

## 8. Segurança e limitações

Esta lógica é apenas um exemplo de controle funcional. Um PLC comum, um único sensor por porta e contatos ladder padrão não garantem uma função de segurança contra falhas. Para máquinas ou locais com risco de aprisionamento/esmagamento, a avaliação de risco e o projeto devem ser feitos por profissional habilitado, com dispositivos e arquitetura de segurança apropriados (por exemplo, intertravamentos e relé/PLC de segurança, conforme aplicável). Avaliar também escape/liberação em emergência, perda de energia, falha de sensor, retenção de pressão e o comportamento de portas com pessoas no interior.

**Não colocar o sistema em operação com pessoas expostas ao risco com base somente neste documento.** Antes da implementação, confirmar o modelo completo do PLC, os endereços reais, a lógica elétrica dos sensores, o tipo de válvula, os pressostatos e os requisitos de segurança da máquina.
