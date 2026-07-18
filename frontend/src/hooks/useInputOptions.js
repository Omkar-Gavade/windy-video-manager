import { useCallback, useEffect, useState } from "react";
import { getStates, getPlants } from "../services/inputApi";

// Discovers State and Plant options dynamically from S3 for the Inputs module
// (mirrors the Videos module's useVideoOptions). No hardcoded arrays.
export function useInputOptions() {
  const [states, setStates] = useState([]);
  const [plants, setPlants] = useState([]);
  const [state, setState] = useState("");
  const [plant, setPlant] = useState("");
  const [loadingStates, setLoadingStates] = useState(true);
  const [loadingPlants, setLoadingPlants] = useState(false);

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
    setPlant("");
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
