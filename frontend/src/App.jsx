import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import VideoDashboard from "./pages/VideoDashboard";
import Documents from "./pages/Documents";

// Application shell: shared Navbar + routed pages.
// "/" -> Video Dashboard (existing, unchanged). "/documents" -> Document Manager.
export default function App() {
  return (
    <div className="min-h-full">
      <Navbar />
      <main className="py-8 sm:py-10">
        <Routes>
          <Route path="/" element={<VideoDashboard />} />
          <Route path="/documents" element={<Documents />} />
        </Routes>
      </main>
    </div>
  );
}
