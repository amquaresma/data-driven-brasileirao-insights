import { useEffect, useState } from "react";

// Busca uma URL e devolve { data, loading, error }. O estado de "carregando" é derivado
// da URL pedida, então não há setState síncrono dentro do efeito.
export function useApi(url, errorMessage = "Não foi possível carregar os dados.") {
  const [result, setResult] = useState({ url: null, data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(errorMessage);
        return r.json();
      })
      .then((data) => !cancelled && setResult({ url, data, error: null }))
      .catch((err) => !cancelled && setResult({ url, data: null, error: err.message }));
    return () => {
      cancelled = true;
    };
  }, [url, errorMessage]);

  const ready = result.url === url;
  return { data: ready ? result.data : null, error: ready ? result.error : null, loading: !ready };
}
