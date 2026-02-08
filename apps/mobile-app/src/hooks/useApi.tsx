/**
 * Generic API hooks with loading, error, and data states.
 * Provides a consistent pattern for data fetching across the app.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../lib/api";

interface UseApiState<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
}

interface UseApiResult<T> extends UseApiState<T> {
  refetch: () => Promise<void>;
  reset: () => void;
}

/**
 * Hook for fetching data from the API. Automatically fetches on mount
 * and provides refetch capability.
 *
 * @param fetcher - Async function that returns the data
 * @param deps - Dependency array; refetches when deps change
 * @param options - Configuration options
 */
export function useApiQuery<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options: {
    enabled?: boolean;
    onSuccess?: (data: T) => void;
    onError?: (error: string) => void;
  } = {}
): UseApiResult<T> {
  const { enabled = true, onSuccess, onError } = options;
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    isLoading: enabled,
    error: null,
  });

  const mountedRef = useRef(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const fetchData = useCallback(async () => {
    if (!mountedRef.current) return;
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const data = await fetcherRef.current();
      if (!mountedRef.current) return;
      setState({ data, isLoading: false, error: null });
      onSuccess?.(data);
    } catch (err) {
      if (!mountedRef.current) return;
      const message =
        (err as ApiError)?.detail || "An unexpected error occurred.";
      setState((prev) => ({ ...prev, isLoading: false, error: message }));
      onError?.(message);
    }
  }, [onSuccess, onError]);

  useEffect(() => {
    mountedRef.current = true;
    if (enabled) {
      fetchData();
    }
    return () => {
      mountedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled]);

  const reset = useCallback(() => {
    setState({ data: null, isLoading: false, error: null });
  }, []);

  return {
    ...state,
    refetch: fetchData,
    reset,
  };
}

/**
 * Hook for API mutations (POST, PUT, DELETE).
 * Does NOT auto-fetch; call `mutate()` to trigger.
 *
 * @param mutator - Async function that performs the mutation
 * @param options - Callbacks for success and error
 */
export function useApiMutation<TData, TVariables = void>(
  mutator: (variables: TVariables) => Promise<TData>,
  options: {
    onSuccess?: (data: TData) => void;
    onError?: (error: string) => void;
  } = {}
): {
  mutate: (variables: TVariables) => Promise<TData | undefined>;
  data: TData | null;
  isLoading: boolean;
  error: string | null;
  reset: () => void;
} {
  const { onSuccess, onError } = options;
  const [state, setState] = useState<UseApiState<TData>>({
    data: null,
    isLoading: false,
    error: null,
  });

  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const mutate = useCallback(
    async (variables: TVariables): Promise<TData | undefined> => {
      setState({ data: null, isLoading: true, error: null });

      try {
        const data = await mutator(variables);
        if (!mountedRef.current) return data;
        setState({ data, isLoading: false, error: null });
        onSuccess?.(data);
        return data;
      } catch (err) {
        const message =
          (err as ApiError)?.detail || "An unexpected error occurred.";
        if (mountedRef.current) {
          setState((prev) => ({ ...prev, isLoading: false, error: message }));
        }
        onError?.(message);
        return undefined;
      }
    },
    [mutator, onSuccess, onError]
  );

  const reset = useCallback(() => {
    setState({ data: null, isLoading: false, error: null });
  }, []);

  return {
    ...state,
    mutate,
    reset,
  };
}
