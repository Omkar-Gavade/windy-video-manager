import { useCallback, useEffect, useState } from "react";
import { getStates, getPlants } from "../services/videoApi";

// Discovers State and Plant options dynamically from S3 (no hardcoded arrays).
// Fetches states on mount; fetches plants whenever the selected state changes.
// Returns the current selection + setters so a form/filter can bind to it.
export function useVideoOptions() {
  const [states, setStates] = useState([]);
  const [plants, setPlants] = useState([]);
  const [state, setState] = useState("");
  const [plant, setPlant] = useState("");
  const [loadingStates, setLoadingStates] = useState(true);
  const [loadingPlants, setLoadingPlants] = useState(false);

  // Load states once.
  useEffect(() => {
    const controller = new AbortController();
    setLoadingStates(true);
    getStates(controller.signal)
      .then((data) => {
        const list = data || [];
        setStates(list);
        setState((prev) => prev || list[0] || "");
      })
      .catch((err) => {
        if (err?.code === "ERR_CANCELED" || err?.name === "CanceledError") return;
        setStates([]);
      })
      .finally(() => setLoadingStates(false));
    return () => controller.abort();
  }, []);

  // Load plants whenever the selected state changes.
  useEffect(() => {
    if (!state) {
      setPlants([]);
      setPlant("");
      return undefined;
    }
    const controller = new AbortController();
    setLoadingPlants(true);
    getPlants(state, controller.signal)
      .then((data) => {
        const list = data || [];
        setPlants(list);
        setPlant(list[0] || "");
      })
      .catch((err) => {
        if (err?.code === "ERR_CANCELED" || err?.name === "CanceledError") return;
        setPlants([]);
        setPlant("");
      })
      .finally(() => setLoadingPlants(false));
    return () => controller.abort();
  }, [state]);

  const changeState = useCallback((value) => {
    setState(value);
    setPlant(""); // reset until the new state's plants load
  }, []);

  return {
    states,
    plants,
    state,
    plant,
    setState: changeState,
    setPlant,
    loadingStates,
    loadingPlants,
  };
}
