import { useState, useEffect } from 'react';
import { apiFetch } from '../services/api/client';

export type MetadataSuggestions = Record<string, string[]>;

// Module-level caches to share data across all components
let globalCache: MetadataSuggestions | null = null;
let fetchPromise: Promise<MetadataSuggestions> | null = null;
let lastFetchTime = 0;
const CACHE_TTL_MS = 60 * 1000; // 60 seconds

export async function fetchMetadataSuggestions(force = false): Promise<MetadataSuggestions> {
  const now = Date.now();

  if (!force && globalCache && now - lastFetchTime < CACHE_TTL_MS) {
    return globalCache;
  }

  if (fetchPromise && !force) {
    return fetchPromise;
  }

  fetchPromise = apiFetch('/api/v3/references/metadata/suggestions')
    .then((data: unknown) => {
      const typedData = data as MetadataSuggestions;
      globalCache = typedData;
      lastFetchTime = Date.now();
      return typedData;
    })
    .finally(() => {
      fetchPromise = null;
    });

  return fetchPromise;
}

export function useMetadataSuggestions() {
  const [suggestions, setSuggestions] = useState<MetadataSuggestions>(globalCache || {});
  const [loading, setLoading] = useState<boolean>(!globalCache);

  useEffect(() => {
    let mounted = true;

    // Background interval to keep it fresh every 60s
    const refreshData = async () => {
      try {
        const data = await fetchMetadataSuggestions();
        if (mounted) {
          setSuggestions(data);
          setLoading(false);
        }
      } catch (err) {
        console.error('Failed to fetch metadata suggestions:', err);
        if (mounted) setLoading(false);
      }
    };

    refreshData();
    const interval = setInterval(refreshData, CACHE_TTL_MS);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const getSuggestionsForField = (fieldName: string, query: string): string[] => {
    const list = suggestions[fieldName] || [];
    if (!query.trim()) return list;

    const q = query.toLowerCase().trim();
    return list.filter(item => item.toLowerCase().includes(q));
  };

  return {
    suggestions,
    loading,
    getSuggestionsForField
  };
}
