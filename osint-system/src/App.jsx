import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import CaseView from "./pages/CaseView";
import NewCase from "./pages/NewCase";
import "./styles/globals.css";

export default function App() {
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [activeCase, setActiveCase] = useState(null);

  const navigate = (page, caseData = null) => {
    setCurrentPage(page);
    if (caseData) setActiveCase(caseData);
  };

  return (
    <div className="app">
      {currentPage === "dashboard" && (
        <Dashboard navigate={navigate} />
      )}
      {currentPage === "case" && (
        <CaseView navigate={navigate} caseData={activeCase} />
      )}
      {currentPage === "new-case" && (
        <NewCase navigate={navigate} />
      )}
    </div>
  );
}
