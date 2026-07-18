import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import VideoDashboard from "./pages/VideoDashboard";
import Inputs from "./pages/Inputs";

// Application shell: shared Navbar + routed pages.
// "/" and "/videos" -> Video Dashboard. "/inputs" -> Input Manager.
// Unknown paths fall back to the Video Dashboard so hard-refresh deep links
// never render blank.
export default function App() {
  return (
    <div className="min-h-full">
      <Navbar />
      <main className="py-8 sm:py-10">
        <Routes>
          <Route path="/" element={<VideoDashboard />} />
          <Route path="/videos" element={<VideoDashboard />} />
          <Route path="/inputs" element={<Inputs />} />
          <Route path="*" element={<VideoDashboard />} />
        </Routes>
      </main>
    </div>
  );
}
