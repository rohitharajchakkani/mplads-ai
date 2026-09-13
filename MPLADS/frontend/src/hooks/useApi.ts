import { useCallback, useEffect, useState } from "react";

export interface ApiState<T> {
  data?: T;
  error?: Error;
  loading: boolean;
  reload: () => void;
}

/** Cancels stale requests whenever its stable request factory changes. */
export function useApi<T>(request: (signal: AbortSignal) => Promise<T>, dependencies: readonly unknown[]): ApiState<T> {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<Omit<ApiState<T>, "reload">>({ loading: true });
  const reload = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    // Keep existing data visible while the fresh request is in-flight
    // (stale-while-revalidate). Callers already guard with
    // `result.loading && !result.data` to show skeletons only on the first load.
    setState((prev) => ({ ...prev, loading: true, error: undefined }));
    request(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ data, loading: false });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ error: error instanceof Error ? error : new Error("Unable to load data."), loading: false });
      });
    return () => controller.abort();
    // The caller owns the dependency list so it is explicit at each API integration.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencies, revision]);

  return { ...state, reload };
}
