export function WithAside({ aside, show = true, children }) {
  if (!show) return children;
  return (
    <div className="with-aside">
      <div className="with-aside-main">{children}</div>
      <aside className="info-card">{aside}</aside>
    </div>
  );
}

function Swatch({ color }) {
  return <span className="legend-swatch" style={{ background: color }} />;
}

function LegendItem({ visual, children }) {
  return (
    <div className="legend-item">
      <span className="legend-visual">{visual}</span>
      <span>{children}</span>
    </div>
  );
}

export function PredictionsInfo() {
  return (
    <>
      <h3>Legenda</h3>
      <div className="legend-list">
        <LegendItem visual={<Swatch color="var(--accent)" />}>
          <b>Verde, "Casa":</b> chance de vitória do mandante (o time da esquerda).
        </LegendItem>
        <LegendItem visual={<Swatch color="var(--draw)" />}>
          <b>Cinza, "Empate":</b> chance de o jogo terminar empatado.
        </LegendItem>
        <LegendItem visual={<Swatch color="#3b82f6" />}>
          <b>Azul, "Fora":</b> chance de vitória do visitante (o time da direita).
        </LegendItem>
        <LegendItem visual={<span className="legend-text">%</span>}>
          O tamanho de cada trecho da barra é proporcional à probabilidade. Os três somam 100%, e o
          arredondamento pode mostrar 99% ou 101%.
        </LegendItem>
        <LegendItem visual={<span className="legend-text">dia</span>}>
          Só aparecem jogos ainda não disputados, agrupados por data.
        </LegendItem>
        <LegendItem visual={<span className="legend-text">nota</span>}>
          O texto no fim da página informa o modelo usado, quantos jogos o treinaram e quando as
          probabilidades foram atualizadas.
        </LegendItem>
      </div>

      <h3 className="info-title-spaced">Como funcionam as previsões</h3>

      <h4>1. Força dos times (Elo)</h4>
      <p>
        Todo time começa com 1500 pontos. Depois de cada jogo, o rating sobe para quem ganhou e desce
        para quem perdeu, e o ajuste é maior quando o resultado era menos esperado: vencer um favorito
        vale mais do que vencer um time fraco. O cálculo segue a ordem dos jogos desde 2020.
      </p>

      <h4>2. Do Elo à probabilidade</h4>
      <p>
        Uma regressão logística converte a diferença de Elo entre mandante e visitante em três
        probabilidades. Ela aprendeu com os jogos finalizados das Séries A e B desde 2020 (cerca de
        5 mil). O efeito de jogar em casa já está nesses dados: mandantes venceram uns 47% dos jogos.
      </p>

      <h4>Quão confiável é</h4>
      <p>
        Testamos o modelo sempre prevendo jogos que ele ainda não tinha visto: treina com o passado,
        prevê o bloco seguinte e repete seis vezes (cerca de 3 mil jogos previstos). Na última
        avaliação, o erro das probabilidades (log loss) ficou uns 2,6% menor do que o de chutar sempre
        a frequência histórica (47% casa, 27% empate, 26% fora). É um ganho real, mas modesto: futebol
        tem muito acaso.
      </p>
      <p>
        Leia como frequência, não como promessa: em 10 jogos com 70% para o mandante, esperamos uns 7
        vitórias dele.
      </p>

      <h4>O que ficou de fora</h4>
      <p>
        Forma recente, médias de gols e dias de descanso foram testados e não melhoraram o modelo, então
        não entram. Lesões, escalações, odds e confronto direto também não são considerados.
      </p>

      <h4>Limitações</h4>
      <ul>
        <li>O rating não volta para perto da média entre temporadas.</li>
        <li>As Séries A e B têm Elo separado: quem muda de divisão não leva o rating junto.</li>
        <li>
          Este Elo parte de 2020, por isso difere do Elo da aba Clubes, que usa só a temporada atual.
        </li>
        <li>Não há previsão de gols: o modelo testado quase não melhorou sobre a frequência histórica.</li>
      </ul>
    </>
  );
}

export function TeamMetricsInfo() {
  return (
    <>
      <h3>Legenda</h3>
      <div className="legend-list">
        <LegendItem visual={<span className="legend-text">#</span>}>
          Posição pelo <b>Elo</b>, não pela classificação do campeonato. Ela é fixa: não muda quando
          você reordena a tabela.
        </LegendItem>
        <LegendItem visual={<span className="trend-up">+1.10</span>}>
          <b>Verde:</b> momentum positivo, o time está melhor agora do que na média recente.
        </LegendItem>
        <LegendItem visual={<span className="trend-down">-0.80</span>}>
          <b>Vermelho:</b> momentum negativo, o time está pior agora do que na média recente.
        </LegendItem>
        <LegendItem visual={<span className="trend-flat">0.00</span>}>
          <b>Cinza:</b> sem mudança entre as duas janelas.
        </LegendItem>
        <LegendItem visual={<span className="legend-text">-</span>}>
          Sem jogos suficientes para calcular.
        </LegendItem>
        <LegendItem visual={<span className="legend-text">0</span>}>
          Nas sequências, zero quer dizer que ela terminou no último jogo.
        </LegendItem>
        <LegendItem visual={<span className="legend-text">?</span>}>
          Passe o mouse sobre o cabeçalho para ver um resumo. <b>Clique</b> nele para ordenar (▲ crescente,
          ▼ decrescente) e clique de novo para inverter.
        </LegendItem>
      </div>

      <h3 className="info-title-spaced">Como os números são calculados</h3>
      <p>
        Tudo vem dos jogos finalizados da temporada atual e é recalculado quando o Analytics roda, não
        em tempo real. Elo, momentum e volatilidade são índices próprios do projeto.
      </p>

      <dl className="info-glossary">
        <dt>Elo</dt>
        <dd>
          Rating de força: todos começam em 1500 e sobem ou descem a cada resultado, mais quando ele é
          surpresa. Aqui usa só os jogos desta temporada e serve para comparar times da mesma série.
        </dd>

        <dt>Momentum</dt>
        <dd>
          Mostra se o time está melhorando ou piorando, comparando os últimos 5 jogos com os últimos 10.
          <div className="info-formula">2 × Δ pontos + Δ gols marcados + Δ gols sofridos</div>
          Δ é a média dos últimos 5 menos a média dos últimos 10. Em gols sofridos o sinal é invertido,
          porque sofrer menos é melhor.
        </dd>

        <dt>Forma</dt>
        <dd>
          Média de pontos (vitória 3, empate 1, derrota 0) dos últimos 10 jogos, com peso maior nos mais
          recentes: o último jogo pesa 10, o anterior 9, e assim até 1. Vai de 0 (só derrotas) a 3 (só
          vitórias), e 1 equivale a uma sequência de empates.
        </dd>

        <dt>Seq. V</dt>
        <dd>Vitórias seguidas até o último jogo.</dd>

        <dt>Invicto</dt>
        <dd>Jogos seguidos sem perder (vitórias e empates).</dd>

        <dt>Sem sofrer</dt>
        <dd>Jogos seguidos sem sofrer gol.</dd>

        <dt>Volat.</dt>
        <dd>
          Quão irregular é o time: média do desvio padrão dos pontos e do saldo de gols nos últimos 10
          jogos. Quanto maior, mais imprevisível. É uma regra nossa, sem valor certo ou errado, e não
          tem cor porque alto não é bom nem ruim.
        </dd>

        <dt>GP/GC (5)</dt>
        <dd>Média de gols marcados e sofridos por jogo nos últimos 5 jogos.</dd>
      </dl>
    </>
  );
}
