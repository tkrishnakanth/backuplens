/** Tiny observable store (no framework). */
export function createStore(initial) {
  let state = { ...initial };
  const listeners = new Set();

  return {
    get() {
      return state;
    },
    set(patch) {
      state = { ...state, ...patch };
      for (const listener of listeners) listener(state);
    },
    subscribe(listener) {
      listeners.add(listener);
      listener(state);
      return () => listeners.delete(listener);
    },
  };
}

export const store = createStore({
  view: "home",
  backups: [],
  session: null,
  typeFilter: "all",
  scope: null,
  selectionCount: 0,
  visibleCount: 0,
});
