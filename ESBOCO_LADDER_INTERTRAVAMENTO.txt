# Esboço Ladder — intertravamento de portas e alarme de pressão

Este documento é um **esboço separado** da documentação funcional. Ele organiza os rungs para transcrever no GX Works2, mas não é um programa pronto para download: o modelo exato da CPU FX, o módulo analógico, o mapa de I/O e a fiação ainda precisam ser confirmados.

## 1. Comportamento previsto

- Portas 1 e 2 são intertravadas entre si; portas 3 e 4 também.
- Um botão libera sua porta somente se ela e a porta parceira estiverem fechadas e a parceira não estiver liberada.
- A liberação se mantém até a porta abrir e depois fechar novamente.
- Eletroímã e válvula de enchimento são saídas independentes. O eletroímã liga imediatamente quando a porta está fechada e não está liberada; a válvula liga após 2 segundos contínuos nessa condição. Ao solicitar liberação, ambas desligam imediatamente; o atraso só se aplica ao acionamento da válvula.
- Um transdutor analógico mede a pressão da linha comum.
- A sirene liga abaixo de 0,8 bar ou acima de 1,5 bar. A lâmpada de pressão indica vermelho/verde conforme a faixa e pisca nas condições de alarme.
- Cada porta possui um LED bicolor e um relé auxiliar próprio: porta aberta energiza seu relé e seleciona vermelho; porta fechada desenergiza o relé e seleciona verde.

## 2. Mapa de I/O e bits (endereços provisórios)

### Entradas e saídas das portas

| Porta | Botão | Sensor fechada | Eletroímã | Válvula da junta |
|---|---|---|---|---|
| 1 | X0 | X10 | Y0 | Y10 |
| 2 | X1 | X11 | Y1 | Y11 |
| 3 | X2 | X12 | Y2 | Y12 |
| 4 | X3 | X13 | Y3 | Y13 |

### Bits internos de estado

| Porta | Liberação memorizada | Já abriu neste ciclo |
|---|---|---|
| 1 | M100 | M110 |
| 2 | M101 | M111 |
| 3 | M102 | M112 |
| 4 | M103 | M113 |

### Temporizadores de acionamento das válvulas

| Porta | Temporizador TON não retentivo | Atraso |
|---|---|---|
| 1 | T0 (exemplo) | 2 segundos |
| 2 | T1 (exemplo) | 2 segundos |
| 3 | T2 (exemplo) | 2 segundos |
| 4 | T3 (exemplo) | 2 segundos |

### Pressão e sinalização

| Sinal | Endereço simbólico/exemplo | Observação |
|---|---|---|
| Valor analógico de pressão em centibar | D200 (após conversão) | 100 centibar = 1,00 bar; dado bruto depende do módulo |
| Pulso de pisca | M_PISCA | Usar clock especial ou temporizador compatível com a CPU |
| Sirene | Y20 | Ligada com baixa ou alta pressão |
| Lâmpada vermelha | Y21 | Pisca abaixo de 0,8 bar; fixa na faixa vermelha intermediária |
| Lâmpada verde de pressão | Y22 | Pisca acima de 1,5 bar; fixa na faixa verde intermediária |
| Relé do LED porta 1 | Y23 | Energizado com porta 1 aberta; desenergizado fechada |
| Relé do LED porta 2 | Y24 | Energizado com porta 2 aberta; desenergizado fechada |
| Relé do LED porta 3 | Y25 | Energizado com porta 3 aberta; desenergizado fechada |
| Relé do LED porta 4 | Y26 | Energizado com porta 4 aberta; desenergizado fechada |

`D200`, `M_PISCA` e os endereços de saída são referências ilustrativas. A pressão é representada em centibar para facilitar as comparações: 0,8 bar = 80, 1,15 bar = 115 e 1,5 bar = 150. O dado bruto da entrada analógica precisa ser escalado conforme o manual do módulo. Y23–Y26 são bobinas de relés auxiliares individuais com contato reversível: contato NA seleciona o vermelho; contato NF seleciona o verde do LED da respectiva porta, com circuito e alimentação adequados.

> Em CPUs FX, endereços de I/O podem usar numeração octal. Confira endereços disponíveis e a configuração de módulos no GX Works2. Os exemplos X10 a X13 não devem ser tratados como endereços garantidos para a instalação.

## 3. Convenções dos desenhos

- `[ X0 ]` = contato lógico normalmente aberto, verdadeiro quando X0 está ligado.
- `[/X0]` = contato lógico negado, verdadeiro quando X0 está desligado. Isso não define o tipo elétrico do sensor de campo.
- `LDP X0` = pulso na borda positiva do botão, se suportado pela CPU selecionada.
- `SET M` / `RST M` = memorizar / apagar bit.
- Condições na mesma linha são contatos em série (E). Ramos em paralelo representam OU.
- Comparações analógicas e `M_PISCA` são simbólicas; selecionar instrução e dispositivo de clock conforme o modelo de CPU.

## 4. Rungs de liberação das portas

### 4.1 Solicitações

A solicitação só é aceita quando a própria porta e sua parceira estão fechadas, e a parceira não está liberada:

```text
Rung 1 — liberar porta 1
LDP X0    [ X10 ]    [ X11 ]    [/M101]  ───────── ( SET M100 )

Rung 2 — liberar porta 2
LDP X1    [ X11 ]    [ X10 ]    [/M100]  ───────── ( SET M101 )

Rung 3 — liberar porta 3
LDP X2    [ X12 ]    [ X13 ]    [/M103]  ───────── ( SET M102 )

Rung 4 — liberar porta 4
LDP X3    [ X13 ]    [ X12 ]    [/M102]  ───────── ( SET M103 )
```

No editor Ladder, inserir o contato de pulso (`LDP`) do botão e os demais contatos em série. Não usar `LDP` como se fosse uma saída SET: a instrução de pulso é o contato de entrada do rung.

### 4.2 Registrar abertura e finalizar ao fechar

A liberação somente é apagada depois de o sensor indicar que a porta abriu e, em seguida, voltou a fechar.

```text
Porta 1
[ M100 ]    [/X10]  ───────────────────────────── ( SET M110 )
[ M110 ]    [ X10 ] ───────────────────────────── ( RST M100 )
[ M110 ]    [ X10 ] ───────────────────────────── ( RST M110 )

Porta 2
[ M101 ]    [/X11]  ───────────────────────────── ( SET M111 )
[ M111 ]    [ X11 ] ───────────────────────────── ( RST M101 )
[ M111 ]    [ X11 ] ───────────────────────────── ( RST M111 )

Porta 3
[ M102 ]    [/X12]  ───────────────────────────── ( SET M112 )
[ M112 ]    [ X12 ] ───────────────────────────── ( RST M102 )
[ M112 ]    [ X12 ] ───────────────────────────── ( RST M112 )

Porta 4
[ M103 ]    [/X13]  ───────────────────────────── ( SET M113 )
[ M113 ]    [ X13 ] ───────────────────────────── ( RST M103 )
[ M113 ]    [ X13 ] ───────────────────────────── ( RST M113 )
```

### 4.3 Saídas independentes e temporização das válvulas

Para cada porta, a saída do eletroímã liga imediatamente quando a porta está fechada e não está liberada. Um TON não retentivo conta 2 segundos sob a mesma condição; o contato de término desse timer comanda a válvula. Se a porta abrir ou a liberação for solicitada antes de completar o tempo, o TON reseta e a válvula fica desligada.

Exemplo da porta 1:

```text
[ X10 ]  [/M100] ──────────────────────────────── ( Y0 )
[ X10 ]  [/M100] ──────────────────────────────── ( TON T0, 2 s )
[ X10 ]  [/M100]  [ T0 concluído ] ────────────── ( Y10 )
```

Repetir para as demais portas com timers independentes:

```text
[ X11 ]  [/M101] ──────────────────────────────── ( Y1 )
[ X11 ]  [/M101] ──────────────────────────────── ( TON T1, 2 s )
[ X11 ]  [/M101]  [ T1 concluído ] ────────────── ( Y11 )

[ X12 ]  [/M102] ──────────────────────────────── ( Y2 )
[ X12 ]  [/M102] ──────────────────────────────── ( TON T2, 2 s )
[ X12 ]  [/M102]  [ T2 concluído ] ────────────── ( Y12 )

[ X13 ]  [/M103] ──────────────────────────────── ( Y3 )
[ X13 ]  [/M103] ──────────────────────────────── ( TON T3, 2 s )
[ X13 ]  [/M103]  [ T3 concluído ] ────────────── ( Y13 )
```

`TON T0, 2 s` é uma notação conceitual, não sintaxe literal garantida para a CPU FX. No GX Works2, configurar o timer não retentivo e escolher o valor de preset de acordo com a base de tempo e o modelo da CPU; não assumir `K20` sem verificar o manual. O atraso é somente na energização da válvula. Na solicitação de liberação, a condição `/Mxxx` deixa de ser verdadeira e a válvula desenergiza imediatamente, junto com o eletroímã. Confirmar no circuito que a válvula energizada enche a junta.

### 4.4 Relés para LEDs individuais das portas

Assumindo que `X10` a `X13` ficam ligados quando cada porta está fechada, cada saída de relé é comandada pelo sensor da sua própria porta:

```text
[/X10] ───────────────────────── ( Y23 — relé/LED porta 1 )
[/X11] ───────────────────────── ( Y24 — relé/LED porta 2 )
[/X12] ───────────────────────── ( Y25 — relé/LED porta 3 )
[/X13] ───────────────────────── ( Y26 — relé/LED porta 4 )
```

Fiação indicativa para cada relé auxiliar com contato reversível:

```text
Saída Y energizada    → contato NA fecha → LED da porta em vermelho (porta aberta)
Saída Y desenergizada → contato NF fecha → LED da porta em verde (porta fechada)
```

Y23 controla somente a indicação da porta 1, Y24 a porta 2, Y25 a porta 3 e Y26 a porta 4. Dimensionar as saídas, relés, contatos e alimentação dos LEDs conforme as cargas reais. Não ligar os LEDs diretamente às saídas do PLC sem verificar tipo de saída e corrente.

A lógica indica posição física pelos sensores. Uma porta liberada pelo botão mas ainda fechada continuará verde; para indicar vermelho desde a liberação, adicionar o bit M correspondente (`M100` a `M103`) à condição do LED daquela porta.

## 5. Escala analógica da pressão

Configurar a entrada do transdutor conforme sua saída elétrica (por exemplo, 4–20 mA ou 0–10 V) e o módulo analógico utilizado. Converter o valor bruto para uma variável escalada em centibar:

```text
D200 = pressão da linha comum em centibar
80  = 0,80 bar
115 = 1,15 bar
150 = 1,50 bar
```

O método de conversão e o registro bruto de entrada são específicos do módulo; não copiar valores de outro modelo sem conferir o manual. Validar a escala com instrumento de referência antes de usar os alarmes.

## 6. Rungs conceituais da sirene e da lâmpada

A faixa intermediária é dividida no ponto médio de 1,15 bar. Para manter o desenho legível, `D200 < K80`, `D200 > K150` e comparações semelhantes representam contatos/comparadores de palavra. A instrução de comparação no GX Works2 varia com a CPU.

### Estados de pressão

```text
BAIXA:       D200 <  K80          (menos de 0,8 bar)
VERMELHO_FIXO: D200 >= K80 E D200 < K115
VERDE_FIXO:    D200 >= K115 E D200 <= K150
ALTA:        D200 >  K150         (mais de 1,5 bar)
```

### Sirene

```text
BAIXA  ─┐
        ├──────────────────────────────────────── ( Y20 )
ALTA   ─┘
```

A sirene permanece ligada enquanto a pressão estiver abaixo de 0,8 bar ou acima de 1,5 bar. Neste esboço, não há retenção nem botão de silêncio: a saída acompanha a condição. Se for necessário silenciar mantendo o alarme visual, criar uma função de reconhecimento separada.

### Lâmpadas

```text
(BAIXA E M_PISCA) OU VERMELHO_FIXO ────────────── ( Y21 )
(ALTA  E M_PISCA) OU VERDE_FIXO   ────────────── ( Y22 )
```

- Menos de 0,8 bar: Y21 pisca; Y20 ligado.
- De 0,8 bar até menos de 1,15 bar: Y21 aceso fixo; Y20 desligado.
- De 1,15 bar até 1,5 bar: Y22 aceso fixo; Y20 desligado.
- Mais de 1,5 bar: Y22 pisca; Y20 ligado.

`M_PISCA` deve alternar ligado/desligado com a frequência desejada. Usar o relé especial de clock indicado no manual da CPU ou configurar um temporizador oscilador. Não assumir um endereço de clock antes de saber o modelo exato do FX.

### Permissivo opcional para o processo

Se o processo só puder operar dentro da faixa de 0,8 a 1,5 bar, criar uma condição `M_PRESSAO_OK` verdadeira entre esses limites e usá-la no permissivo do processo. O endereço da saída/processo não foi informado, portanto não foi inventado neste esboço. A reação da máquina a pressão baixa/alta deve ser definida por análise de risco.

## 7. Testes antes de operar

1. Com as saídas de potência isoladas, monitorar os sensores de porta no GX Works2 e confirmar o estado lógico fechado/aberto.
2. Solicitar cada porta e confirmar que as saídas do eletroímã e da válvula da porta selecionada desligam imediatamente.
3. Com uma porta do par aberta, tentar solicitar a parceira e confirmar que a solicitação é recusada.
4. Confirmar que o ciclo só termina após a sequência abrir e fechar; depois do fechamento, verificar eletroímã imediato e válvula após 2 segundos contínuos.
5. Abrir novamente a porta antes de completar os 2 segundos e confirmar cancelamento do timer e válvula desligada.
6. Abrir cada porta individualmente e confirmar que só o relé correspondente (Y23–Y26) energiza e seu LED fica vermelho; ao fechar, confirmar que o mesmo relé desenergiza e o LED fica verde.
7. Injetar valores analógicos de teste (ou usar fonte/calibrador apropriado) e verificar as transições em 0,8, 1,15 e 1,5 bar, a sirene e as duas cores de pressão.
8. Verificar a frequência de pisca e se a lâmpada de pressão nunca acende vermelho e verde ao mesmo tempo.
9. Testar falha/desconexão do transdutor, reinicialização do PLC e perda/retorno de energia.
10. Confirmar o comportamento das válvulas, pressão real e dispositivos de alívio com profissional habilitado.

## 8. Alertas importantes

- O transdutor único monitora somente a pressão geral do coletor; não diagnostica qual junta individual falhou.
- Os níveis de 0,8 e 1,5 bar precisam ser confirmados com os fabricantes da junta, válvula e demais componentes.
- A sirene e as lâmpadas são sinalização, não substituem medidas de segurança.
- Não usar o programa/PLC como única proteção contra sobrepressão; avaliar proteção mecânica independente, como válvula de alívio, conforme projeto pneumático.
- Um PLC comum e sensores únicos não constituem automaticamente uma função de segurança. Validar riscos, emergência e acesso às portas com profissional habilitado.
- Antes de converter para rungs definitivos, obter o modelo completo da CPU FX, modelo do módulo analógico, tipo/faixa do transdutor e endereços físicos reais.
