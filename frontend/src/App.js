import { BrowserRouter, Routes, Route } from "react-router-dom";
import MatchList from "./Pages/MatchList";
import MatchDetail from "./Pages/MatchDetail";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MatchList />} />
        <Route path="/match/:matchId" element={<MatchDetail />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;